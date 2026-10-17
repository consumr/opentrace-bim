# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPERIMENTAL: optional one-click retrieval of an archived Uniclass dataset.

Nothing is fetched in the background. Public 2022 CSV snapshot is maintained
by Buildig from NBS-published classifications, NOT the current NBS 2026 issue.
Publisher's taxonomy is not modified. Users can replace it with NBS current
files via the original-file importer. Neither OmniClass nor ABNT tables are
embedded, scraped or downloaded. No cross-system code matches are inferred.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request
from zipfile import ZIP_DEFLATED, ZipFile

from .official_classification_import import import_publisher_catalogue

ARCHIVE_EDITION = 'Jan 2022 (arquivada; ver revisões por tabela)'
ARCHIVE_SOURCE = 'https://github.com/buildig/uniclass-2015'
NBS_CURRENT = 'https://uniclass.thenbs.com/download'
CC_BY_ND = 'https://creativecommons.org/licenses/by-nd/4.0/'
TABLES_2022 = ('Ac', 'Co', 'En', 'SL', 'EF', 'Ss', 'Pr', 'TE', 'PM', 'Ro', 'FI', 'Zz')
RAW_TEMPLATE = 'https://raw.githubusercontent.com/buildig/uniclass-2015/main/uniclass2015/Uniclass2015_{table}.csv'
MAX_SINGLE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 55 * 1024 * 1024


def cache_path(directory):
    return Path(directory) / 'Uniclass2015_arquivo_2022.zip'


def _get(url, *, opener=None):
    # Explicit network access only on the user clicking install. No telemetry.
    opener = opener or urllib.request.urlopen
    with opener(urllib.request.Request(url, headers={'User-Agent': 'OpenTraceBIM-Experimental/1.0'}), timeout=28) as response:
        out = response.read(MAX_SINGLE_BYTES + 1)
    if not out or len(out) > MAX_SINGLE_BYTES:
        raise ValueError('Tabela ausente ou maior que limite permitido.')
    return out


def download_uniclass_archive(directory, *, opener=None, progress=None):
    """Atomically cache all 12 historical tables; never leave a partial ZIP."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = cache_path(folder)
    contents = []
    size = 0
    for number, table in enumerate(TABLES_2022, 1):
        if progress:
            progress(number, len(TABLES_2022), table)
        raw = _get(RAW_TEMPLATE.format(table=table), opener=opener)
        # The original CSV has identifiable columns and real Uniclass codes.
        from .official_classification_import import _split_csv, _rows_to_records
        records = _rows_to_records(_split_csv(raw), 'Uniclass 2015', filename=table)
        if not records or not any(code.startswith(table + '_') for code, _ in records):
            raise ValueError('Tabela remota incompatível ou vazia: ' + table)
        contents.append((table, raw))
        size += len(raw)
        if size > MAX_TOTAL_BYTES:
            raise ValueError('Conjunto maior que o limite permitido.')
    manifest = {
        'system': 'Uniclass 2015', 'edition': ARCHIVE_EDITION,
        'source': ARCHIVE_SOURCE, 'original_publisher': 'NBS',
        'publisher_url': NBS_CURRENT, 'license': CC_BY_ND,
        'tables': {table: hashlib.sha256(data).hexdigest() for table, data in contents},
    }
    # Staging file in same directory allows atomic replace (also on Windows).
    fd, tmp = tempfile.mkstemp(prefix='.uniclass-', suffix='.zip', dir=str(folder))
    try:
        with os.fdopen(fd, 'wb') as stream:
            with ZipFile(stream, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
                for table, data in contents:
                    archive.writestr('Uniclass2015_' + table + '.csv', data)
                archive.writestr('OPENTRACE_SOURCE_MANIFEST.json', json.dumps(manifest, indent=2))
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return target


def load_uniclass_archive(directory):
    """Only accept a full 12-table installation with matching provenance hashes."""
    path = cache_path(directory)
    if not path.is_file():
        raise FileNotFoundError('Uniclass arquivado ainda não instalado.')
    with ZipFile(path) as archive:
        manifest = json.loads(archive.read('OPENTRACE_SOURCE_MANIFEST.json').decode('utf-8'))
        if manifest.get('edition') != ARCHIVE_EDITION or set(manifest.get('tables', {})) != set(TABLES_2022):
            raise ValueError('Manifesto de classificação incompleto.')
        for table, sha in manifest['tables'].items():
            if hashlib.sha256(archive.read('Uniclass2015_' + table + '.csv')).hexdigest() != sha:
                raise ValueError('Checksum incorreto em ' + table)
    cat = import_publisher_catalogue(path, 'Uniclass 2015', edition=ARCHIVE_EDITION)
    cat['publisher'] = 'NBS'
    cat['source_url'] = ARCHIVE_SOURCE
    cat['publisher_url'] = NBS_CURRENT
    cat['license_url'] = CC_BY_ND
    cat['archival'] = True
    return cat


def classification_cache_dir():
    """Separate per-user cache, never a workspace document or repository."""
    try:
        from PySide6.QtCore import QStandardPaths
        root = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if root:
            return Path(root) / 'opentrace-experimental' / 'classification-cache'
    except ImportError:
        pass
    return Path.home() / '.opentrace-experimental' / 'classification-cache'
