# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPERIMENTAL / ISOLATED: interoperable, evidence-tracked crosswalk catalogues.

Classification codes are independent of IFC schema versions.  A shared IFC
entity (IfcWall) never establishes semantic equivalence between a Uniclass,
OmniClass, ABNT or other classification code.  Only an explicit, reviewed,
uniquely resolved exact relation may be proposed automatically.

The format is versioned to allow further locally imported catalogs; source
catalogues remain separate and retain their own licences and revisions.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

FORMAT = 'opentrace-classification-equivalences'
VERSION = 1
MAX_BYTES = 4 * 1024 * 1024
MAX_RELATIONS = 30000
SYSTEMS = {
    'Uniclass 2015': {'organization': 'NBS', 'url': 'https://uniclass.thenbs.com/download', 'edition': 'trimestral'},
    'OmniClass': {'organization': 'CSI / CSC', 'url': 'https://www.csiresources.org/standards/omniclass', 'edition': 'segundo tabela'},
    'ABNT NBR 15965': {'organization': 'ABNT', 'url': 'https://siclic.fau.usp.br/busca', 'edition': 'segundo parte/tabela'},
    'MasterFormat': {'organization': 'CSI / CSC', 'url': 'https://www.csiresources.org/standards/masterformat', 'edition': 'segundo tabela'},
    'CoClass': {'organization': 'Svensk Byggtjanst', 'url': 'https://coclass.byggtjanst.se/', 'edition': 'segundo catalogo'},
}
RELATIONS = {'exact', 'similar', 'broader', 'narrower', 'related'}


def empty_crosswalk():
    return {'format': FORMAT, 'version': VERSION, 'id': 'opentrace:unreviewed',
            'name': 'Sem equivalências normativas homologadas', 'revision': '0',
            'relations': []}


def _identity(value, prefix):
    if not isinstance(value, dict):
        raise ValueError(prefix + ': sistema e código são obrigatórios.')
    system = str(value.get('system') or '').strip()
    code = str(value.get('code') or '').strip()
    if not system or not code or len(system) > 160 or len(code) > 160:
        raise ValueError(prefix + ': sistema/código inválido.')
    return {'system': system, 'code': code}


def _validate_relation(entry, index):
    if not isinstance(entry, dict):
        raise ValueError('Relação %d inválida.' % index)
    origin = _identity(entry.get('source'), 'Origem %d' % index)
    target = _identity(entry.get('target'), 'Destino %d' % index)
    kind = str(entry.get('relation') or '').strip().lower()
    if kind not in RELATIONS:
        raise ValueError('Relação %d: tipo desconhecido.' % index)
    if origin == target:
        raise ValueError('Relação %d: origem e destino iguais.' % index)
    evidence = entry.get('evidence') or {}
    if not isinstance(evidence, dict):
        raise ValueError('Relação %d: fonte inválida.' % index)
    status = str(evidence.get('status') or 'unreviewed').lower()
    if status not in ('verified', 'unreviewed'):
        raise ValueError('Relação %d: revisão deve ser verified ou unreviewed.' % index)
    uri = str(evidence.get('uri') or '').strip()
    if uri and (not uri.startswith(('https://', 'http://')) or len(uri) > 1200):
        raise ValueError('Relação %d: URL inválida.' % index)
    # Exact auto-mapping is only possible for curated, source-traceable rows.
    # 'Verified' is the crosswalk publisher's claim, not an OpenTrace endorsement.
    return {'source': origin, 'target': target, 'relation': kind,
            'evidence': {'status': status, 'uri': uri,
                         'edition': str(evidence.get('edition') or '')[:120],
                         'publisher': str(evidence.get('publisher') or '')[:160],
                         'note': str(evidence.get('note') or '')[:350]}}


def validate_crosswalk(raw):
    if not isinstance(raw, dict) or raw.get('format') != FORMAT or raw.get('version') != VERSION:
        raise ValueError('Formato de equivalências desconhecido (versão 1 necessária).')
    rows = raw.get('relations')
    if not isinstance(rows, list) or len(rows) > MAX_RELATIONS:
        raise ValueError('Relações inválidas ou catálogo grande demais.')
    ident = str(raw.get('id') or '').strip()
    if not ident or len(ident) > 180:
        raise ValueError('Catálogo de equivalências precisa de identificador.')
    name = str(raw.get('name') or ident).strip()[:180]
    revision = str(raw.get('revision') or '1')[:80]
    seen = set()
    result = []
    for n, row in enumerate(rows, 1):
        item = _validate_relation(row, n)
        sig = (item['source']['system'], item['source']['code'],
               item['target']['system'], item['target']['code'], item['relation'])
        if sig in seen:
            raise ValueError('Relação repetida na linha %d.' % n)
        seen.add(sig)
        result.append(item)
    return {'format': FORMAT, 'version': VERSION, 'id': ident,
            'name': name, 'revision': revision, 'relations': result}


def read_crosswalk(path):
    file = Path(path)
    if not file.is_file() or file.stat().st_size > MAX_BYTES:
        raise ValueError('Arquivo de equivalências inexistente ou maior que 4 MB.')
    data = file.read_bytes()
    if file.suffix.lower() == '.json':
        try:
            raw = json.loads(data.decode('utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            raise ValueError('JSON de equivalências inválido.') from exc
    elif file.suffix.lower() == '.csv':
        try:
            text = data.decode('utf-8-sig')
            try:
                dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
        except (ValueError, UnicodeError, csv.Error) as exc:
            raise ValueError('CSV de equivalências inválido.') from exc
        raw = {'format': FORMAT, 'version': VERSION,
               'id': 'sha256:' + hashlib.sha256(data).hexdigest(),
               'name': file.stem, 'revision': 'arquivo importado', 'relations': [
                   {'source': {'system': row.get('source_system'), 'code': row.get('source_code')},
                    'target': {'system': row.get('target_system'), 'code': row.get('target_code')},
                    'relation': row.get('relation'),
                    'evidence': {'status': row.get('evidence_status'),
                                 'uri': row.get('evidence_uri'),
                                 'edition': row.get('evidence_edition'),
                                 'publisher': row.get('evidence_publisher')}} for row in rows]}
    else:
        raise ValueError('Equivalências exigem arquivo JSON ou CSV.')
    return validate_crosswalk(raw)


def _id(item):
    return str(item.get('system') or ''), str(item.get('code') or '')


def _eligible(row):
    ev = row.get('evidence') or {}
    return (row.get('relation') == 'exact' and ev.get('status') == 'verified'
            and bool(ev.get('uri')) and bool(ev.get('edition')))


def find_correspondences(source, target_catalogue, crosswalks):
    """Return (verified exact matches, review-only candidates).

    Directional matches must exist in the chosen destination taxonomy.  It is
    unsafe to guess from IFC entity, string overlap or translated description.
    """
    key = (str(source[0]), str(source[1])) if source else ('', '')
    definitions = {(_id(v)): copy.deepcopy(v) for v in
                   (target_catalogue.get('classifications') or {}).values()
                   if isinstance(v, dict)}
    result = {}
    for catalog in crosswalks or ():
        parsed = validate_crosswalk(catalog)
        for rel in parsed['relations']:
            a, b = _id(rel['source']), _id(rel['target'])
            dest = b if key == a else a if key == b else None
            if dest is None or dest not in definitions:
                continue
            line = {'definition': copy.deepcopy(definitions[dest]),
                    'relation': rel['relation'], 'evidence': copy.deepcopy(rel['evidence']),
                    'crosswalk': parsed['id'], 'reviewed': _eligible(rel)}
            prev = result.get(dest)
            if prev is None or (line['reviewed'] and not prev['reviewed']):
                result[dest] = line
    automatic = [v['definition'] for v in result.values() if v['reviewed']]
    manual = list(result.values())
    # Multiple exact matches are ambiguous.  A competing approximate mapping
    # never becomes automatic, but is shown for human review.
    return (automatic[0] if len(automatic) == 1 and len(manual) == 1 else None), manual


def crosswalks_from_document(document):
    setup = document.get('project_setup') if isinstance(document, dict) else None
    rows = (setup or {}).get('equivalence_catalogues') or []
    if not isinstance(rows, list):
        return []
    parsed = []
    for row in rows:
        try:
            parsed.append(validate_crosswalk(row))
        except ValueError:
            continue
    return parsed


def attach_crosswalk(document, crosswalk):
    from .bim import normalize_document_data
    out = normalize_document_data(document)
    cw = validate_crosswalk(crosswalk)
    setup = out.setdefault('project_setup', {})
    existing = crosswalks_from_document(out)
    # Catalog id and revision uniquely identify a user-reviewed mapping edition.
    existing = [x for x in existing if x['id'] != cw['id']]
    existing.append(copy.deepcopy(cw))
    setup['equivalence_catalogues'] = existing
    return out
