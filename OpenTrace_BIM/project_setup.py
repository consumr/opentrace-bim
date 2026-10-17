# SPDX-License-Identifier: GPL-3.0-or-later
"""EXP-only, host-neutral setup of new projects (template and catalogue).

No existing source file is modified by this module. A JSON template supplies
project settings; a copied .igz template preserves full scene geometry.
Classification snapshots are embedded
in OpenTrace's document_data and survive file reopen without the source CSV.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

TEMPLATE_FORMAT = 'opentrace-project-settings-template'
TEMPLATE_VERSION = 1
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_CLASSIFICATIONS = 20000
_TEMPLATE_KEYS = ('project', 'georeference', 'export', 'libraries')


def _json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _read_text(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('Arquivo não existe ou excede 8 MB.')
    raw = path.read_bytes()
    return raw.decode('utf-8-sig'), hashlib.sha256(raw).hexdigest()


def file_sha256(path):
    """Stream file identity without loading a potentially large .igz in RAM."""
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def empty_template():
    return {'id': 'opentrace:current', 'name': 'Padrão OpenTrace', 'settings': {}}


def read_template(path):
    text, digest = _read_text(path)
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError('Template inválido: esperado JSON de configurações OpenTrace.') from exc
    if not isinstance(data, dict) or data.get('format') != TEMPLATE_FORMAT or data.get('version') != TEMPLATE_VERSION:
        raise ValueError('Template incompatível. Use um modelo exportado pelo OpenTrace.')
    settings = data.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Template sem configurações de projeto.')
    if any(k not in _TEMPLATE_KEYS for k in settings):
        raise ValueError('O template contém seções desconhecidas.')
    for key in settings:
        if not isinstance(settings[key], dict):
            raise ValueError('Configurações inválidas: ' + key)
    # A template never replaces identities, geometry, or external link paths.
    settings = _json_copy(settings)
    return {'id': 'sha256:' + digest, 'name': str(data.get('name') or Path(path).stem)[:160],
            'settings': settings}


def export_template(data, path, name):
    """Export the non-geometric BIM settings as a reusable project template."""
    if not name or not str(name).strip():
        raise ValueError('Informe o nome do template.')
    settings = {k: copy.deepcopy(data[k]) for k in _TEMPLATE_KEYS if isinstance(data.get(k), dict)}
    # Personal links and the project's existing classifications are intentional:
    # templates can include library definitions, but cannot copy persistent IDs.
    bundle = {'format': TEMPLATE_FORMAT, 'version': TEMPLATE_VERSION,
              'name': str(name).strip()[:160], 'settings': _json_copy(settings)}
    out = Path(path)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def empty_catalogue():
    return {'id': 'ifc4:bundled', 'name': 'IFC4 incorporado', 'classifications': {}}


def _entries(raw):
    if isinstance(raw, dict):
        if isinstance(raw.get('classifications'), dict):
            return [dict(v, name=k) for k, v in raw['classifications'].items() if isinstance(v, dict)]
        if isinstance(raw.get('classifications'), list):
            return raw['classifications']
        if isinstance(raw.get('entries'), list):
            return raw['entries']
    if isinstance(raw, list):
        return raw
    raise ValueError('Catálogo JSON sem lista de classificações válida.')


def read_catalogue(path):
    """Import a *real* CSV/JSON external taxonomy; never invent code mappings."""
    text, digest = _read_text(path)
    suffix = Path(path).suffix.lower()
    try:
        if suffix == '.csv':
            # Handles Excel CSV with semicolon or comma, no platform encoding.
            sample = text[:8192]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t') if sample else csv.excel
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
        elif suffix == '.json':
            rows = _entries(json.loads(text))
        else:
            raise ValueError('Catálogo externo precisa ser CSV ou JSON.')
    except (csv.Error, json.JSONDecodeError, TypeError) as exc:
        raise ValueError('Falha ao interpretar o catálogo.') from exc
    if len(rows) > MAX_CLASSIFICATIONS:
        raise ValueError('Catálogo excede 20.000 classificações.')
    classifications = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f'Linha {index} do catálogo não é um registro.')
        system = str(row.get('system') or row.get('sistema') or '').strip()
        code = str(row.get('code') or row.get('codigo') or row.get('código') or '').strip()
        title = str(row.get('name') or row.get('nome') or row.get('description') or row.get('descricao') or code).strip()
        if not system or not code:
            raise ValueError(f'Linha {index}: sistema e código são obrigatórios.')
        if len(system) > 160 or len(code) > 160 or len(title) > 240:
            raise ValueError(f'Linha {index}: campo longo demais.')
        key = f'{system} · {code}'
        if key in classifications:
            raise ValueError(f'Código repetido: {key}')
        # Mappings must come from the source taxonomy, never from guessed
        # similarities between IFC entities and normative classification codes.
        def cell_values(raw):
            if isinstance(raw, (list, tuple)):
                return [str(x).strip() for x in raw if str(x).strip()]
            if isinstance(raw, str):
                return [x.strip() for x in raw.replace('|', ';').split(';') if x.strip()]
            return []
        ifc_classes = cell_values(row.get('ifc_classes') or row.get('ifc_class') or row.get('classes_ifc'))
        for cls in ifc_classes:
            if not cls.startswith('Ifc') or len(cls) > 100:
                raise ValueError(f'Linha {index}: classe IFC inválida: {cls}')
        matches = cell_values(row.get('matches') or row.get('aliases') or row.get('correspondencias'))
        if len(matches) > 50 or any(' · ' not in value or len(value) > 350 for value in matches):
            raise ValueError(f'Linha {index}: cada correspondência deve ser Sistema · Código.')
        classifications[key] = {'system': system, 'code': code,
                                'ifc_classes': ifc_classes, 'matches': matches,
                                'description': str(row.get('description') or row.get('descricao') or '')[:500],
                                'location': str(row.get('location') or row.get('uri') or '')[:500],
                                'name': title}
    if not classifications:
        raise ValueError('O arquivo não contém classificações utilizáveis.')
    return {'id': 'sha256:' + digest, 'name': Path(path).stem,
            'classifications': classifications}


def catalogue_from_document(document):
    """Active catalogue snapshot on reopen; never depend on the source file."""
    if not isinstance(document, dict):
        return empty_catalogue()
    setup = document.get('project_setup') or {}
    libraries = (document.get('libraries') or {}).get('classifications') or {}
    keys = setup.get('catalogue_keys') or []
    entries = {key: copy.deepcopy(libraries[key]) for key in keys if key in libraries}
    result = {'id': setup.get('catalogue_id') or 'ifc4:bundled',
              'name': setup.get('catalogue_name') or 'IFC4 incorporado',
              'classifications': entries}
    if setup.get('primary_classification_system'):
        result['primary_system'] = setup['primary_classification_system']
    if setup.get('catalogue_sources'):
        result['sources'] = copy.deepcopy(setup['catalogue_sources'])
    return result


def _deep_overlay(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_overlay(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def merge_classification_catalogues(catalogues):
    """Combine several independent source taxonomies, preserving original IDs."""
    items = list(catalogues or [])
    if not items:
        return empty_catalogue()
    merged = {'id': 'multi:' + '+'.join(str(c.get('id') or '')[:32] for c in items),
              'name': ' + '.join(str(c.get('name') or 'Catálogo') for c in items),
              'sources': [], 'classifications': {}}
    for cat in items:
        if not isinstance(cat, dict) or not isinstance(cat.get('classifications'), dict):
            raise ValueError('Catálogo de classificação inválido.')
        merged['sources'].append({'id': str(cat.get('id') or ''),
                                  'name': str(cat.get('name') or ''),
                                  'system': str(cat.get('system') or ''),
                                  'edition': str(cat.get('edition') or ''),
                                  'source_file': str(cat.get('source_file') or ''),
                                  'sha256': str(cat.get('source_sha256') or ''),
                                  'source_url': str(cat.get('source_url') or ''),
                                  'publisher': str(cat.get('publisher') or ''),
                                  'license_url': str(cat.get('license_url') or '')})
        for key, val in cat['classifications'].items():
            if key in merged['classifications'] and merged['classifications'][key] != val:
                raise ValueError('Dois catálogos definem códigos conflitantes: ' + key)
            merged['classifications'][key] = copy.deepcopy(val)
    return merged


def configure_new_project(existing, template, catalogue, *, ifc_schema='IFC4',
                          equivalence_catalogues=None, primary_system='', layer_combination_set=None,
                          resource_libraries=None, project_information=None):
    """Produce a complete document record without changing source records.

    The caller must ensure this is a new/empty document. Once persisted, the
    setup stays with that .igz and is never prompted or re-applied on reopen.
    """
    from .bim import normalize_document_data
    if not isinstance(template, dict) or not isinstance(catalogue, dict):
        raise ValueError('Template e catálogo precisam ser escolhidos separadamente.')
    original = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if isinstance(original.get('project_setup'), dict):
        raise ValueError('Projeto já foi configurado. Trocar catálogo exige fluxo de migração separado.')
    out = normalize_document_data(original)
    settings = template.get('settings') or {}
    if not isinstance(settings, dict) or any(k not in _TEMPLATE_KEYS for k in settings):
        raise ValueError('Seções inválidas no template.')
    for key, values in settings.items():
        if not isinstance(values, dict):
            raise ValueError('Configuração inválida: ' + key)
        _deep_overlay(out[key], values)
    from .ifc_export import normalize_export_schema
    from .classification_equivalences import validate_crosswalk
    out['export']['schema'] = normalize_export_schema(ifc_schema)
    crosswalks = [validate_crosswalk(c) for c in (equivalence_catalogues or ())]
    classes = catalogue.get('classifications') or {}
    if not isinstance(classes, dict):
        raise ValueError('Catálogo inválido.')
    for key, value in classes.items():
        if not isinstance(value, dict) or not (value.get('system') and value.get('code')):
            raise ValueError('Classificação inválida: ' + str(key))
        # Never silently override a classification from a user's template.
        if key in out['libraries']['classifications'] and out['libraries']['classifications'][key] != value:
            raise ValueError('Conflito de classificação: ' + key)
        out['libraries']['classifications'][key] = copy.deepcopy(value)
    if project_information is not None:
        if not isinstance(project_information, dict):
            raise ValueError('Informações de projeto inválidas.')
        allowed = ('name', 'client', 'location', 'description', 'author',
                   'organization', 'site', 'building')
        if any(key not in allowed or not isinstance(value, str) or len(value) > 500
               for key, value in project_information.items()):
            raise ValueError('Campo de informação do projeto inválido.')
        for key, value in project_information.items():
            # A copied .igz template may already carry project information;
            # only fields the user explicitly supplied are overlaid.
            out['project'][key] = value.strip()
    out['project_setup'] = {
        'version': 1,
        'template_id': str(template.get('id') or 'opentrace:current'),
        'template_name': str(template.get('name') or 'Padrão OpenTrace'),
        'catalogue_id': str(catalogue.get('id') or 'ifc4:bundled'),
        'catalogue_name': str(catalogue.get('name') or 'IFC4 incorporado'),
        'catalogue_count': len(classes),
        'catalogue_keys': list(classes),
        'migration_pending': [],
        'catalogue_sources': copy.deepcopy(catalogue.get('sources') or []),
        'primary_classification_system': str(primary_system or ''),
        'equivalence_catalogues': crosswalks,
        'layer_combination_set': copy.deepcopy(layer_combination_set or {}),
        'resource_libraries': copy.deepcopy(resource_libraries or []),
        'library_selection_mode': 'curated' if resource_libraries is not None else 'legacy',
    }
    return normalize_document_data(out)


def copy_igz_template(source, target):
    """Never overwrite a user's project or their .igz template.

    Host-native ``window.open_path`` subsequently loads this independent copy.
    An exclusive destination protects against existing projects even if a file
    dialog's overwrite prompt was dismissed accidentally.
    """
    src, dst = Path(source), Path(target)
    if src.suffix.lower() != '.igz' or dst.suffix.lower() != '.igz':
        raise ValueError('Template e novo projeto precisam ser arquivos .igz.')
    if not src.is_file() or not src.stat().st_size:
        raise ValueError('Template .igz inexistente ou vazio.')
    if src.resolve() == dst.resolve():
        raise ValueError('O novo projeto deve ter outro nome e caminho.')
    created = False
    try:
        with src.open('rb') as origin, dst.open('xb') as destination:
            created = True
            shutil.copyfileobj(origin, destination, length=1024*1024)
    except FileExistsError as exc:
        raise ValueError('Destino já existe. Escolha um arquivo novo; nada será sobrescrito.') from exc
    except OSError:
        # Delete only a partial file actually created by *this* operation.
        # Never unlink an existing user project if opening the source fails.
        if created:
            try: dst.unlink()
            except OSError: pass
        raise
    return dst


def configure_cloned_igz(existing, source, catalogue, *, ifc_schema='IFC4',
                         equivalence_catalogues=None, primary_system='', layer_combination_set=None,
                         resource_libraries=None, project_information=None):
    """Adopt the existing scene and BIM settings of a copied user template.

    A new project never inherits the template's completed setup marker.  No
    existing geometry, IFC object identity or layer is changed by this function.
    """
    seed = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    seed.pop('project_setup', None)
    source = Path(source)
    return configure_new_project(seed, {
        'id': 'igz:' + file_sha256(source),
        'name': source.stem, 'settings': {},
    }, catalogue, ifc_schema=ifc_schema,
    equivalence_catalogues=equivalence_catalogues, primary_system=primary_system,
    layer_combination_set=layer_combination_set, resource_libraries=resource_libraries,
    project_information=project_information)


def can_configure_new_document(raw, group_count, *, has_saved_path=False,
                               clean_untitled=False):
    """Old saved .igz files are not 'new', even if empty and without BIM.

    IngeTrazo puts an optional Engineer/Person scale *group* in a fresh new
    scene. A clean, untitled host document is new despite that group.
    """
    return (not has_saved_path and (raw is None or raw == {})
            and (group_count == 0 or clean_untitled))



def should_offer_initial_setup(bim_document, group_count, *, has_saved_path=False,
                               clean_untitled=False, already_offered=False):
    """Popup policy, not a test for whether layer metadata exists.

    Importantly, an edit to the layer namespace is *not* a new project.
    Calling this from viewport-paint events or document-changed callbacks
    cannot resurrect a dismissed wizard.
    """
    return (not already_offered and can_configure_new_document(
        bim_document, group_count, has_saved_path=has_saved_path,
        clean_untitled=clean_untitled))
