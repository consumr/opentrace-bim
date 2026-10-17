# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in update checks for OpenTrace BIM.

Update checks read published OpenTrace BIM releases on GitHub directly.
No extension package is downloaded until the user explicitly clicks
"Download and install".
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile

from PySide6.QtCore import QObject, QSettings, Signal, Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from . import __version__

RELEASES_URL = (
    "https://api.github.com/repos/lelopes05/opentrace-bim/releases?per_page=30"
)
DOWNLOAD_PREFIX = (
    "https://github.com/lelopes05/opentrace-bim/releases/download/"
)
SETTINGS_KEY = "opentrace_bim/check_updates_automatically"
MAX_CATALOG_BYTES = 2 * 1024 * 1024
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
MAX_UNPACKED_BYTES = 30 * 1024 * 1024
MAX_PACKAGE_FILES = 500


def auto_check_enabled() -> bool:
    return bool(QSettings().value(SETTINGS_KEY, False, type=bool))


def set_auto_check_enabled(enabled: bool) -> None:
    QSettings().setValue(SETTINGS_KEY, bool(enabled))


def _version_tuple(raw: str):
    nums = [int(x) for x in re.findall(r"\d+", str(raw))]
    if not nums:
        return ()
    return tuple((nums + [0, 0, 0, 0])[:4])


def _request_bytes(url: str, *, limit: int, timeout: int = 12) -> bytes:
    req = urllib.request.Request(
        str(url),
        headers={"User-Agent": f"OpenTrace-BIM/{__version__} updater"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError("The received response is larger than the allowed limit.")
    return data


def _release_entry() -> dict:
    """Find the newest published, hash-verified release on our GitHub.

    GitHub's Release asset digest is authoritative for download integrity.
    We intentionally do not depend on IngeTrazo's separately maintained
    extension catalogue, which may lag behind our own publication.
    """
    raw = _request_bytes(RELEASES_URL, limit=MAX_CATALOG_BYTES)
    releases = json.loads(raw.decode("utf-8"))
    if not isinstance(releases, list):
        raise RuntimeError("The OpenTrace BIM GitHub release feed is invalid.")

    candidates = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue

        tag = str(release.get("tag_name", ""))
        if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            continue
        version = tag[1:]
        filename = f"OpenTrace_BIM-{tag}.zip"
        expected_url = DOWNLOAD_PREFIX + f"{tag}/{filename}"

        for asset in release.get("assets", []):
            if not isinstance(asset, dict):
                continue
            if asset.get("name") != filename or asset.get("state") != "uploaded":
                continue
            digest = str(asset.get("digest") or "")
            if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
                continue
            if asset.get("browser_download_url") != expected_url:
                continue
            size = asset.get("size")
            if not isinstance(size, int) or not 0 < size <= MAX_PACKAGE_BYTES:
                continue
            candidates.append({
                "version": version,
                "download": expected_url,
                "sha256": digest.split(":", 1)[1].lower(),
            })
            break

    if not candidates:
        raise RuntimeError(
            "No published OpenTrace BIM release with a verified ZIP was found."
        )
    return max(candidates, key=lambda item: _version_tuple(item["version"]))


def _safe_zip_members(zf: zipfile.ZipFile):
    files = []
    unpacked = 0
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if not name or name.endswith("/"):
            continue
        path = Path(name)
        if name.startswith("/") or ".." in path.parts or ":" in name:
            raise RuntimeError(f"Invalid package: unsafe path {name!r}.")
        files.append(name)
        unpacked += int(info.file_size)
        if len(files) > MAX_PACKAGE_FILES or unpacked > MAX_UNPACKED_BYTES:
            raise RuntimeError("The update package exceeds the allowed unpacked size.")
    return files




def _extract_package(zf: zipfile.ZipFile, destination: Path):
    """Extract validated regular files without trusting ZipFile.extractall paths."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    names = _safe_zip_members(zf)
    infos = {info.filename.replace("\\", "/"): info for info in zf.infolist() if not info.is_dir()}
    for name in names:
        info = infos.get(name)
        if info is None:
            raise RuntimeError(f"Invalid package member {name!r}.")
        target = destination.joinpath(*Path(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Write a normal file even if an archive tried to encode a symlink or
        # other platform-specific type. No archive permissions are executed.
        with zf.open(info, "r") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return names

def _validate_package(data: bytes, expected_version: str):
    digest = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
        names = _safe_zip_members(zf)
        tops = {name.split("/")[0] for name in names}
        if len(tops) != 1:
            raise RuntimeError("The update package has an invalid structure.")
        root = next(iter(tops))
        if root != Path(__file__).resolve().parent.name:
            raise RuntimeError(
                f"The package installs {root!r}, but this installation uses "
                f"{Path(__file__).resolve().parent.name!r}."
            )
        init_name = f"{root}/__init__.py"
        if init_name not in names:
            raise RuntimeError("The package does not contain the extension main file.")
        init_text = zf.read(init_name).decode("utf-8")
        match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
        if not match or match.group(1) != str(expected_version):
            raise RuntimeError(
                "The package internal version does not match the GitHub release version."
            )
        for name in names:
            if not name.endswith(".py"):
                continue
            source = zf.read(name).decode("utf-8")
            compile(source, name, "exec")
    return digest


def _install_package(data: bytes, expected_version: str, expected_sha: str):
    got = _validate_package(data, expected_version)
    if got.lower() != str(expected_sha).lower():
        raise RuntimeError(
            "The update SHA-256 does not match the published GitHub asset."
        )

    current_dir = Path(__file__).resolve().parent
    if not os.access(current_dir, os.W_OK):
        raise RuntimeError(
            "The current OpenTrace BIM folder is not writable. "
            "Install the update using a writable plugin directory."
        )

    with tempfile.TemporaryDirectory(prefix="opentrace-update-") as td:
        tmp = Path(td)
        archive = tmp / "update.zip"
        archive.write_bytes(data)

        with zipfile.ZipFile(archive) as zf:
            names = _extract_package(zf, tmp / "unpacked")

        root = next((tmp / "unpacked").iterdir())
        if not root.is_dir():
            raise RuntimeError("The update content is invalid.")

        # Backup small and local: allows rollback if copying fails.
        backup = tmp / "backup"
        shutil.copytree(current_dir, backup)

        try:
            old_manifest_path = current_dir / "PACKAGE_MANIFEST.txt"
            old_owned = set()
            if old_manifest_path.is_file():
                old_owned = {
                    line.strip()
                    for line in old_manifest_path.read_text(
                        encoding="utf-8"
                    ).splitlines()
                    if line.strip()
                }

            backup_files = {
                p.relative_to(backup).as_posix()
                for p in backup.rglob("*")
                if p.is_file()
            }
            new_files = {
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file()
            }

            # Remove only files explicitly owned by the previous package.
            for rel in sorted(old_owned - new_files, reverse=True):
                target = current_dir / rel
                if target.is_file():
                    target.unlink()

            # Overwrite/add the new package without touching user-created files.
            for src in sorted(p for p in root.rglob("*") if p.is_file()):
                rel = src.relative_to(root)
                dst = current_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        except Exception:
            # Roll back both overwritten files and files that exist only in the
            # failed new package.  Older code restored the backup but left such
            # orphan files behind, producing mixed-version installations.
            for rel in sorted(new_files - backup_files, reverse=True):
                dst = current_dir / rel
                if dst.is_file():
                    try:
                        dst.unlink()
                    except OSError:
                        pass
            for src in sorted(p for p in backup.rglob("*") if p.is_file()):
                rel = src.relative_to(backup)
                dst = current_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            raise


class UpdateManager(QObject):
    """Background GitHub release checker and explicit installer."""

    check_result = Signal(object, object, bool)
    install_result = Signal(bool, str, str)

    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self._checking = False
        self._installing = False
        self._progress = None
        self.check_result.connect(self._finish_check)
        self.install_result.connect(self._finish_install)

    def check(self, *, manual: bool = False):
        if self._checking:
            if manual:
                QMessageBox.information(
                    self.parent_widget,
                    "Updates",
                    "An update check is already in progress.",
                )
            return

        self._checking = True

        def worker():
            try:
                entry = _release_entry()
                error = None
            except Exception as exc:
                entry = None
                error = f"{type(exc).__name__}: {exc}"
            self.check_result.emit(entry, error, bool(manual))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_check(self, entry, error, manual):
        self._checking = False

        if error:
            if manual:
                QMessageBox.warning(
                    self.parent_widget,
                    "Updates",
                    "Could not check for updates now.\n\n" + str(error),
                )
            return

        available = str(entry.get("version", ""))
        if _version_tuple(available) <= _version_tuple(__version__):
            if manual:
                QMessageBox.information(
                    self.parent_widget,
                    "Updates",
                    f"OpenTrace BIM {__version__} is already the latest version.",
                )
            return

        box = QMessageBox(self.parent_widget)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("OpenTrace BIM Update")
        box.setText(f"OpenTrace BIM {available} is available.")
        box.setInformativeText(
            "Automatic checking only queries OpenTrace BIM GitHub Releases; "
            "no update has been downloaded.\n\n"
            "You can download and install now. After installation, "
            "IngeTrazo must be restarted to use the new version."
        )
        install_button = box.addButton(
            "Download and install", QMessageBox.AcceptRole
        )
        box.addButton("Not now", QMessageBox.RejectRole)
        box.exec()

        if box.clickedButton() is install_button:
            self.install(entry)

    def install(self, entry: dict):
        if self._installing:
            return
        self._installing = True

        version = str(entry["version"])
        self._progress = QProgressDialog(
            f"Downloading and installing OpenTrace BIM {version}…",
            None,
            0,
            0,
            self.parent_widget,
        )
        self._progress.setWindowTitle("OpenTrace BIM Update")
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setCancelButton(None)
        self._progress.setMinimumDuration(0)
        self._progress.show()

        def worker():
            try:
                data = _request_bytes(
                    str(entry["download"]),
                    limit=MAX_PACKAGE_BYTES,
                    timeout=30,
                )
                _install_package(
                    data,
                    expected_version=version,
                    expected_sha=str(entry["sha256"]),
                )
                ok = True
                message = ""
            except Exception as exc:
                ok = False
                message = f"{type(exc).__name__}: {exc}"
            self.install_result.emit(ok, message, version)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_install(self, ok: bool, message: str, version: str):
        self._installing = False
        if self._progress is not None:
            self._progress.close()
            self._progress.deleteLater()
            self._progress = None

        if ok:
            QMessageBox.information(
                self.parent_widget,
                "Update installed",
                f"OpenTrace BIM {version} was installed.\n\n"
                "Restart IngeTrazo to complete the update.",
            )
        else:
            QMessageBox.critical(
                self.parent_widget,
                "Update failed",
                "The update was not installed.\n\n" + str(message),
            )
