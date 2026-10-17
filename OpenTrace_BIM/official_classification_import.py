# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental import of independently obtained classification tables.

Accept publisher's CSV/XLSX/ZIP without modifying classifications or
pretending that similarly named codes in different systems are equivalent.
No network activity. The source edition and checksum travel with project data.
XLSX parsing uses stdlib only, so IngeTrazo need not ship openpyxl.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import xml.etree.ElementTree as ET

MAX_FILE = 80 * 1024 * 1024
MAX_EXPANDED = 140 * 1024 * 1024
MAX_ROWS = 140000
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
TABLE_IDS = ('Ac', 'Co', 'En', 'SL', 'EF', 'Ss', 'Pr', 'TE', 'PM', 'Ro', 'RK', 'Ma', 'PC', 'FI', 'Zz')


def _clean(txt):
    return ' '.join(str(txt if txt is not None else '').split())


def _split_csv(data):
    for encoding in ('utf-8-sig', 'cp1252'):
        try:
            text = data.decode(encoding)
            break
        except UnicodeError:
            continue
    else:
        raise ValueError('CSV não utiliza UTF-8 ou Windows-1252.')
    try:
        dialect = csv.Sniffer().sniff(text[:10000], delimiters=',;\t')
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(io.StringIO(text), dialect=dialect))


def _xlsx_rows(data):
    """Reads shared strings, inline strings and raw cells; avoids dependencies."""
    try:
        src = ZipFile(io.BytesIO(data))
    except BadZipFile as exc:
        raise ValueError('Planilha XLSX corrompida.') from exc
    with src as z:
        names = z.namelist()
        if any(n.startswith('/') or '..' in Path(n).parts for n in names):
            raise ValueError('Caminho inseguro na planilha.')
        if sum(i.file_size for i in z.infolist()) > MAX_EXPANDED:
            raise ValueError('Planilha maior que o limite de segurança.')
        shared = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('m:si', NS):
                shared.append(''.join(t.text or '' for t in si.findall('.//m:t', NS)))
        # Consume worksheets, not drawings, macros or external links.
        worksheets = [n for n in names if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n)]
        for filename in sorted(worksheets):
            root = ET.fromstring(z.read(filename))
            rows = []
            for row in root.findall('.//m:sheetData/m:row', NS):
                vals = {}
                for c in row.findall('m:c', NS):
                    ref = c.attrib.get('r', '')
                    letters = re.match('[A-Z]+', ref)
                    if not letters:
                        continue
                    idx = 0
                    for letter in letters.group():
                        idx = idx * 26 + ord(letter) - 64
                    if idx > 100:
                        continue
                    kind = c.attrib.get('t', '')
                    if kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in c.findall('.//m:t', NS))
                    else:
                        v = c.find('m:v', NS)
                        value = v.text if v is not None else ''
                        if kind == 's' and value:
                            index = int(value)
                            value = shared[index] if index < len(shared) else ''
                    vals[idx - 1] = _clean(value)
                if vals:
                    rows.append([vals.get(i, '') for i in range(max(vals) + 1)])
                if len(rows) > MAX_ROWS:
                    raise ValueError('Planilha excede o limite de linhas.')
            yield filename, rows


def _extract_tables(blob, filename):
    lower = filename.lower()
    if lower.endswith('.csv'):
        yield filename, _split_csv(blob)
    elif lower.endswith('.xlsx'):
        for sheet, rows in _xlsx_rows(blob):
            yield filename + '/' + sheet, rows
    elif lower.endswith('.zip'):
        try:
            src = ZipFile(io.BytesIO(blob))
        except BadZipFile as exc:
            raise ValueError('ZIP de catálogos corrompido.') from exc
        with src as z:
            members = z.infolist()
            if len(members) > 250 or sum(i.file_size for i in members) > MAX_EXPANDED:
                raise ValueError('Pacote de catálogos excede o limite de segurança.')
            for member in members:
                name = member.filename
                if name.startswith('/') or '..' in Path(name).parts:
                    raise ValueError('Caminho inseguro no ZIP.')
                if member.is_dir() or Path(name).name.startswith('~$'):
                    continue
                if name.lower().endswith(('.xlsx', '.csv')):
                    for label, rows in _extract_tables(z.read(member), name):
                        yield label, rows
    else:
        raise ValueError('Use arquivos .csv, .xlsx ou .zip oficiais.')


def _normalize_col(s):
    normalized = unicodedata.normalize('NFKD', _clean(s).lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in normalized if not unicodedata.combining(c)))


def _guess_columns(row):
    cells = [_normalize_col(v) for v in row]
    code_names = {'code', 'codigo', 'classificationcode', 'number', 'classificationnumber',
                  'uniclass2015code', 'uniclasscode', 'omniclasscode', 'codigoabnt',
                  'codigodeclassificacao', 'codigodaclasse', 'cod'}
    title_names = {'title', 'description', 'descricao', 'name', 'nome', 'classificationtitle',
                   'classificationdescription', 'definition', 'termo', 'termos',
                   'termopadronizado', 'denominacao', 'designacao'}
    code = next((i for i, c in enumerate(cells) if c in code_names or c.endswith('code')), None)
    title = next((i for i, c in enumerate(cells) if c in title_names), None)
    return (code, title) if code is not None and title is not None and code != title else (None, None)


def _rows_to_records(rows, system, *, filename):
    header = None
    records = []
    for i, row in enumerate(rows):
        if header is None:
            code_col, title_col = _guess_columns(row)
            if code_col is not None:
                header = (code_col, title_col)
            elif i > 100:
                break
            continue
        code_idx, title_idx = header
        if len(row) <= max(code_idx, title_idx):
            continue
        code, title = _clean(row[code_idx]), _clean(row[title_idx])
        if not code or not title or _normalize_col(code) in {'code', 'codigo'}:
            continue
        if len(code) > 120 or len(title) > 500:
            continue
        if system == 'Uniclass 2015' and not re.match(r'^(?:' + '|'.join(TABLE_IDS) + r')_[0-9]', code):
            # Original publisher's table prefix is the stable identifier.
            continue
        records.append((code, title))
        if len(records) > MAX_ROWS:
            raise ValueError('Arquivo excede o máximo de códigos.')
    return records


def import_publisher_catalogue(path, system, *, edition='Fonte do usuário'):
    """Returns a source-tracked catalogue, no generated correspondences."""
    if not isinstance(system, str) or not system.strip() or len(system) > 160:
        raise ValueError('Identifique o sistema de classificação.')
    system = system.strip()
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError('Arquivo inexistente ou maior que 80 MB.')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    entries = {}
    table_counts = {}
    for name, rows in _extract_tables(raw, path.name):
        found = _rows_to_records(rows, system, filename=name)
        if not found:
            continue
        for code, title in found:
            key = system + ' · ' + code
            if key in entries:
                if entries[key]['name'] != title:
                    raise ValueError('Mesmo código com descrições diferentes: ' + code)
                continue
            table = code.split('_')[0] if system == 'Uniclass 2015' else ''
            if system == 'ABNT NBR 15965':
                from .siclic_bsdd_access import _abnt_table
                table = _abnt_table(code)
            entries[key] = {'system': system, 'code': code, 'name': title,
                            'table': table, 'ifc_classes': [], 'matches': []}
            table_counts[table or 'Sem tabela'] = table_counts.get(table or 'Sem tabela', 0) + 1
            if len(entries) > MAX_ROWS:
                raise ValueError('Catálogo excede 140 mil códigos.')
    if not entries:
        raise ValueError('Nenhuma tabela com cabeçalhos Código/Termo, Código/Descrição ou Code/Title encontrada. '
                         'O arquivo original deve ter códigos e descrições tabulares.')
    return {'id': 'source:sha256:' + digest, 'name': system + ' — ' + path.stem,
            'source_file': path.name, 'source_sha256': digest,
            'system': system, 'edition': _clean(edition),
            'table_counts': table_counts, 'classifications': entries,
            'publisher_original': True}
