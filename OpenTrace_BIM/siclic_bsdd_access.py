# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional SICLIC dictionary access via buildingSMART's public bSDD read API.

This is a *preview/demonstration dictionary*, not the official complete
ABNT NBR 15965 norm.  Only an explicit button click triggers network access.
No invented codes, correspondence or automatic assignment.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SICLIC_DEMO_URI = 'https://identifier.buildingsmart.org/uri/DEMO/SICLIC/0.1.2'
SICLIC_API = 'https://api.bsdd.buildingsmart.org/api/Dictionary/v1/Classes'
SICLIC_SOURCE = 'https://search.bsdd.buildingsmart.org/'
SICLIC_EDITION = 'bSDD DEMO/SICLIC 0.1.2 (prévia; não é a norma completa)'
PAGE_SIZE = 500
MAX_PAGES = 80
MAX_CODES = 30000
MAX_PAGE_BYTES = 4 * 1024 * 1024
ABNT_TABLES = {'0M', '0P', '1F', '1S', '1D', '2C', '2N', '2Q',
               '3E', '3R', '4U', '4A', '5I'}


def _read_page(url, opener=None):
    opening = opener or urlopen
    request = Request(url, headers={'User-Agent': 'OpenTraceBIM-Experimental/1.0',
                                    'Accept': 'application/json'})
    with opening(request, timeout=25) as response:
        raw = response.read(MAX_PAGE_BYTES + 1)
    if not raw or len(raw) > MAX_PAGE_BYTES:
        raise ValueError('Resposta do bSDD vazia ou acima do limite de segurança.')
    try:
        doc = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, ValueError) as exc:
        raise ValueError('O bSDD retornou uma resposta que não é JSON válido.') from exc
    if not isinstance(doc, dict):
        raise ValueError('Estrutura inesperada na resposta do bSDD.')
    return doc


def _abnt_table(code):
    code = str(code).strip().upper()
    prefix = re.match(r'^([0-5][A-Z])(?:[.\s_\-/]|\d|$)', code)
    return prefix.group(1) if prefix and prefix.group(1) in ABNT_TABLES else ''


def download_siclic_preview(*, opener=None, progress=None, uri=SICLIC_DEMO_URI):
    """Get real reference codes from SICLIC's bSDD DEMO dictionary.

    The published bSDD URL is referenced by SICLIC itself. We do not call it
    the complete edition of the ABNT norm. Pagination must finish completely;
    partial network results never become an installed catalogue.
    """
    if uri != SICLIC_DEMO_URI:
        raise ValueError('Versão SICLIC não autorizada por esta integração.')
    records = {}
    pages = 0
    expected = None
    while pages < MAX_PAGES:
        offset = pages * PAGE_SIZE
        params = urlencode({'Uri': uri, 'Offset': offset, 'Limit': PAGE_SIZE})
        doc = _read_page(SICLIC_API + '?' + params, opener)
        rows = doc.get('classes')
        if not isinstance(rows, list):
            raise ValueError('O bSDD não retornou a lista de classes esperada.')
        total = doc.get('classesTotalCount')
        if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            expected = total
            if expected > MAX_CODES:
                raise ValueError('O dicionário excede o limite de segurança.')
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get('referenceCode') or row.get('code') or '').strip()
            name = str(row.get('name') or row.get('description') or '').strip()
            table = _abnt_table(code)
            if not table or not name or len(code) > 160 or len(name) > 500:
                continue
            key = 'ABNT NBR 15965 · ' + code
            record = {'system': 'ABNT NBR 15965', 'code': code,
                      'name': name, 'table': table,
                      'ifc_classes': [], 'matches': [],
                      'location': str(row.get('uri') or '')[:500]}
            previous = records.get(key)
            if previous is not None and previous != record:
                raise ValueError('O bSDD devolveu definições conflitantes para ' + code)
            records[key] = record
        pages += 1
        if progress:
            progress(pages, expected, len(records))
        if len(records) > MAX_CODES:
            raise ValueError('O dicionário excede o limite de segurança.')
        if not rows:
            if expected is not None and offset < expected:
                raise ValueError('O bSDD encerrou antes de transferir todas as classes.')
            break
        if expected is not None and offset + len(rows) >= expected:
            break
        if expected is None and len(rows) < PAGE_SIZE:
            break
        if len(rows) != PAGE_SIZE:
            raise ValueError('O bSDD retornou página incompleta durante a transferência.')
    else:
        raise ValueError('Paginação SICLIC excedeu o limite permitido.')
    if not records:
        raise ValueError('Nenhum código ABNT NBR 15965 foi recebido do SICLIC/bSDD. '
                         'O dicionário de demonstração pode estar indisponível ou incompleto.')
    # Stable digest of the received snapshot; stored in the project's own data.
    identity = hashlib.sha256(json.dumps(records, sort_keys=True, ensure_ascii=False)
                              .encode('utf-8')).hexdigest()
    tables = {}
    for r in records.values():
        tables[r['table']] = tables.get(r['table'], 0) + 1
    return {'id': 'bsdd:siclic:0.1.2:' + identity,
            'name': 'SICLIC — bSDD demonstrativo 0.1.2',
            'system': 'ABNT NBR 15965', 'edition': SICLIC_EDITION,
            'source_file': 'bSDD read API', 'source_sha256': identity,
            'source_url': uri, 'publisher': 'SICLIC · FAU-USP / bSDD',
            'preview': True, 'table_counts': tables, 'classifications': records}
