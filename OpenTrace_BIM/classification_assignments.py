# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive user-verified classification references on BIM objects."""
from __future__ import annotations
import copy


def normalized_entries(meta):
    result = []
    if not isinstance(meta, dict):
        return result
    for row in meta.get('classifications') or []:
        if isinstance(row, dict) and row.get('system') and row.get('code'):
            result.append(copy.deepcopy(row))
    current = (str(meta.get('classification_system') or '').strip(),
               str(meta.get('classification_code') or '').strip())
    if all(current) and not any((x['system'], x['code']) == current for x in result):
        result.append({'system': current[0], 'code': current[1]})
    return result


def add_reference(meta, definition, *, primary=False, provenance=None):
    """Returns a copy; geometry, identity, Psets and existing refs untouched."""
    if not isinstance(meta, dict) or not isinstance(definition, dict):
        raise ValueError('Metadados IFC e classificação necessários.')
    system = str(definition.get('system') or '').strip()
    code = str(definition.get('code') or '').strip()
    if not system or not code or len(system) > 160 or len(code) > 160:
        raise ValueError('Sistema/código de classificação inválido.')
    result = copy.deepcopy(meta)
    entries = normalized_entries(result)
    source = provenance or {}
    row = {'system': system, 'code': code,
           'name': str(definition.get('name') or '')[:300],
           'location': str(definition.get('location') or source.get('source_url') or '')[:500],
           'source': str(source.get('publisher') or source.get('system') or system)[:160],
           'edition': str(source.get('edition') or '')[:120],
           'verified': bool(definition.get('publisher_original') or source.get('publisher_original'))}
    match = next((i for i, value in enumerate(entries)
                  if (value.get('system'), value.get('code')) == (system, code)), None)
    if match is None:
        entries.append(row)
    else:
        # Existing checked description, if present, wins over blank manual entry.
        entries[match] = {**row, **{k: v for k, v in entries[match].items() if v}}
    result['classifications'] = entries
    if primary or not (result.get('classification_system') and result.get('classification_code')):
        result['classification_system'] = system
        result['classification_code'] = code
    result['classification_opt_out'] = False
    return result


def remove_reference(meta, system, code):
    out = copy.deepcopy(meta)
    out['classifications'] = [e for e in normalized_entries(meta)
                              if (e.get('system'), e.get('code')) != (system, code)]
    if (out.get('classification_system'), out.get('classification_code')) == (system, code):
        if out['classifications']:
            out['classification_system'] = out['classifications'][0]['system']
            out['classification_code'] = out['classifications'][0]['code']
        else:
            out['classification_system'] = ''
            out['classification_code'] = ''
    return out


def extend_project_catalogue(document, catalogue):
    """Install taxonomy after project creation without changing objects/favorites."""
    from .bim import normalize_document_data
    if not isinstance(catalogue, dict) or not isinstance(catalogue.get('classifications'), dict):
        raise ValueError('Catálogo inválido.')
    out = normalize_document_data(document)
    library = out['libraries']['classifications']
    additions = catalogue['classifications']
    for key, value in additions.items():
        if key in library and library[key] != value:
            raise ValueError('Conflito no mesmo código: ' + key)
    for key, value in additions.items():
        library[key] = copy.deepcopy(value)
    setup = out.setdefault('project_setup', {})
    keys = list(setup.get('catalogue_keys') or [])
    keys.extend(key for key in additions if key not in keys)
    setup['catalogue_keys'] = keys
    sources = list(setup.get('catalogue_sources') or [])
    descriptor = {k: catalogue.get(k) for k in
                  ('id', 'name', 'system', 'edition', 'source_file', 'source_sha256', 'source_url')}
    if not any(s.get('id') == descriptor['id'] for s in sources):
        sources.append(descriptor)
    setup['catalogue_sources'] = sources
    setup['catalogue_count'] = len(keys)
    setup['catalogue_name'] = ' + '.join(sorted({str(s.get('system') or '') for s in sources if s.get('system')})) or 'Catálogos carregados'
    return out
