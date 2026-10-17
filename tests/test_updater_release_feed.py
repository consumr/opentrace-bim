"""Isolated tests for GitHub-release updates (no IngeTrazo/PySide6 needed)."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "OpenTrace_BIM" / "updater.py"
DIGEST = "a" * 64
PREFIX = "https://github.com/lelopes05/opentrace-bim/releases/download/"


def asset(version, *, hash_string=None, state="uploaded", size=1500000):
    tag = f"v{version}"
    filename = f"OpenTrace_BIM-{tag}.zip"
    return {
        "name": filename,
        "state": state,
        "size": size,
        "digest": hash_string if hash_string is not None else "sha256:" + DIGEST,
        "browser_download_url": PREFIX + tag + "/" + filename,
    }


def release(version, *, draft=False, assets=None):
    return {
        "draft": draft,
        "tag_name": f"v{version}",
        "assets": [asset(version)] if assets is None else assets,
    }


def checker(payload):
    # Execute just the two pure functions; never import PySide6 or touch the network.
    tree = ast.parse(UPDATER.read_text(encoding="utf-8"), str(UPDATER))
    allowed = {"_version_tuple", "_release_entry"}
    found = [item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name in allowed]
    assert len(found) == 2
    env = {
        "json": json, "re": re,
        "RELEASES_URL": "https://api.github.com/repos/lelopes05/opentrace-bim/releases?per_page=30",
        "DOWNLOAD_PREFIX": PREFIX, "MAX_CATALOG_BYTES": 2097152,
        "MAX_PACKAGE_BYTES": 10485760,
        "_request_bytes": lambda url, *, limit: json.dumps(payload).encode("utf-8"),
    }
    exec(compile(ast.Module(body=found, type_ignores=[]), str(UPDATER), "exec"), env)
    return env["_release_entry"]


class GitHubUpdaterTests(unittest.TestCase):
    def test_latest_published_is_selected(self):
        result = checker([release("0.42.0"), release("0.42.1")])()
        self.assertEqual(result["version"], "0.42.1")
        self.assertEqual(result["sha256"], DIGEST)
        self.assertEqual(result["download"], PREFIX + "v0.42.1/OpenTrace_BIM-v0.42.1.zip")

    def test_drafts_not_selected(self):
        self.assertEqual(
            checker([release("0.99.9", draft=True), release("0.42.1")])()["version"],
            "0.42.1",
        )

    def test_missing_digest_rejected(self):
        bad = release("0.42.1", assets=[asset("0.42.1", hash_string="")])
        self.assertEqual(checker([bad, release("0.42.0")])()["version"], "0.42.0")

    def test_foreign_download_url_rejected(self):
        foreign = asset("0.42.1")
        foreign["browser_download_url"] = "https://example.org/unsafe.zip"
        self.assertEqual(
            checker([release("0.42.1", assets=[foreign]), release("0.42.0")])()["version"],
            "0.42.0",
        )

    def test_oversized_zip_rejected(self):
        oversized = release("0.42.1", assets=[asset("0.42.1", size=20 * 1024 * 1024)])
        self.assertEqual(checker([oversized, release("0.42.0")])()["version"], "0.42.0")

    def test_invalid_feed_fails_safely(self):
        with self.assertRaises(RuntimeError):
            checker({"not": "a list"})()


if __name__ == "__main__":
    unittest.main()
