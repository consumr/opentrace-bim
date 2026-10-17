# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPERIMENTAL: non-destructive catalogue migration, with preview and undo.

Only IFC *classification* fields and document catalogue metadata are changed;
model geometry, layers, parametric records, GUIDs and favourites are untouched.
Normative code translation requires a verified explicit mapping or a manual
choice; IFC4 class names are not ABNT or Uniclass classification codes.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from .bim import is_bim_group, normalize_document_data
from .classification_equivalences import (crosswalks_from_document,
                                          find_correspondences, validate_crosswalk)


def identity(value):
    if not isinstance(value, dict):
        return None
    system = str(value.get('system') or '').strip()
    code = str(value.get('code') or '').strip()
    return (system, code) if system and code else None


def key_of(system, code):
    return (str(system or '').strip(), str(code or '').strip())


def targets(catalogue):
    """Index exact target IDs and explicit source aliases, without guesses."""
    result = {}
    by_class = {}
    for entry in (catalogue.get('classifications') or {}).values():
        if not isinstance(entry, dict) or not identity(entry):
            continue
        dest = identity(entry)
        keys = [dest]
        for alias in entry.get('matches', []) or []:
            if isinstance(alias, dict):
                candidate = identity(alias)
            elif isinstance(alias, str) and ' · ' in alias:
                candidate = tuple(x.strip() for x in alias.split(' · ', 1))
            else:
                candidate = None
            if candidate and all(candidate):
                keys.append(candidate)
        for source_key in keys:
            items = result.setdefault(source_key, [])
            if entry not in items:
                items.append(entry)
        for cls in entry.get('ifc_classes', []) or []:
            if str(cls).startswith('Ifc'):
                by_class.setdefault(str(cls), []).append(entry)
    return result, by_class


def automatic_for_class(catalogue, ifc_class):
    """Only a single explicitly tagged code qualifies for new IFC elements."""
    _by_source, by_class = targets(catalogue)
    matches = by_class.get(str(ifc_class), ())
    return copy.deepcopy(matches[0]) if len(matches) == 1 else None


def automatic_for_class_multi(catalogue, ifc_class):
    """Fast, conservative assignment using a lazily prepared class index.

    Classifications can contain tens of thousands of entries. Never scan or
    deepcopy the entire catalogue every time the user creates an element.
    Cache is local to the transient catalogue loaded into this scene, not the
    saved .igz and not shared between projects.
    """
    if not isinstance(catalogue, dict) or not ifc_class:
        return []
    classes = catalogue.get('classifications') or {}
    cache = catalogue.get('_opentrace_creation_index')
    if not isinstance(cache, dict) or cache.get('classes_id') != id(classes):
        grouped = {}
        for item in classes.values():
            if not isinstance(item, dict):
                continue
            for cls in item.get('ifc_classes', ()) or ():
                if not str(cls).startswith('Ifc'):
                    continue
                by_system = grouped.setdefault(str(cls), {})
                by_system.setdefault(str(item.get('system') or ''), []).append(item)
        singles = {}
        for cls, systems in grouped.items():
            singles[cls] = [copy.deepcopy(entries[0])
                            for entries in systems.values() if len(entries) == 1]
        cache = {'classes_id':id(classes), 'singles':singles}
        catalogue['_opentrace_creation_index'] = cache
    return copy.deepcopy(cache['singles'].get(str(ifc_class), ()))


def current_assignment(meta):
    if not isinstance(meta, dict):
        return None
    key = key_of(meta.get('classification_system'), meta.get('classification_code'))
    if all(key):
        return key
    # Legacy element may only have one entry in IFC classifications list.
    entries = [identity(e) for e in meta.get('classifications', ()) if isinstance(e, dict)]
    entries = [e for e in entries if e]
    return entries[0] if len(set(entries)) == 1 else None


@dataclass
class MigrationPreview:
    rows: list
    count: int
    catalogue: dict
    original: dict
    signature: tuple = ()
    library_conflicts: tuple = ()
    crosswalks: tuple = ()

    @property
    def unresolved(self):
        return sum(1 for row in self.rows if row['status'] in ('pendente', 'conflito', 'revisão de equivalência'))


def preview_migration(groups, document, catalogue, equivalence_catalogues=None):
    """Snapshot live metadata; no writes during preview."""
    if not isinstance(catalogue, dict) or not isinstance(catalogue.get('classifications'), dict):
        raise ValueError('Escolha um catálogo de destino válido.')
    doc = normalize_document_data(document)
    by_key, by_class = targets(catalogue)
    crosswalks = (crosswalks_from_document(doc) if equivalence_catalogues is None
                  else [validate_crosswalk(c) for c in equivalence_catalogues])
    rows_by_key = {}
    elements = []
    for group in list(groups):
        if not is_bim_group(group):
            continue
        meta = copy.deepcopy(getattr(group, 'ifc', None))
        if not isinstance(meta, dict):
            continue  # Never create or replace unrelated data in this operation.
        source = current_assignment(meta)
        cls = str(meta.get('class') or '')
        suggestions = []
        if not source:
            status, proposal = 'pendente', None
        else:
            matched, suggestions = find_correspondences(source, catalogue, crosswalks)
            match = by_key.get(source, ())
            if len(match) == 1:
                status, proposal = 'automática', match[0]
            elif len(match) > 1:
                status, proposal = 'conflito', None
            elif matched is not None:
                status, proposal = 'equivalência verificada', matched
            elif suggestions:
                status, proposal = 'revisão de equivalência', None
            elif source[0] in ('OpenTrace BIM / IFC4', 'OpenTrace BIM / IFC4.3') and len(by_class.get(cls, ())) == 1:
                status, proposal = 'automática', by_class[cls][0]
            else:
                status, proposal = 'pendente', None
        # Group the review by source *and* IFC class for unclassified cases.
        rowkey = (source, cls)
        if rowkey not in rows_by_key:
            rows_by_key[rowkey] = {'source': source, 'ifc_class': cls,
                                  'status': status, 'proposal': copy.deepcopy(proposal),
                                  'suggestions': copy.deepcopy(suggestions),
                                  'count': 0, 'key': rowkey}
        rows_by_key[rowkey]['count'] += 1
        elements.append((group, meta, rowkey))
    rows = sorted(rows_by_key.values(), key=lambda r: (str(r['source'] or ''), r['ifc_class']))
    existing_lib = doc.get('libraries', {}).get('classifications', {})
    conflicts = tuple(key for key, entry in (catalogue.get('classifications') or {}).items()
                      if key in existing_lib and existing_lib[key] != entry)
    signature = tuple(sorted((id(group), repr(meta)) for group, meta, _rowkey in elements))
    return MigrationPreview(rows, len(elements), copy.deepcopy(catalogue), doc,
                            signature, conflicts, tuple(copy.deepcopy(crosswalks)))


def build_migration(preview, groups, choices=None, *, keep_pending=False):
    """Return (new doc, group mutation plan, pending rows) without writes.

    choices maps (source tuple or None, IFC class) -> catalogue key, or None
    to retain the source as a recorded pending classification.  A missing
    choice leaves the automatic proposal intact; ambiguous/unmapped rows are
    blocked until explicitly retained or resolved.
    """
    choices = choices or {}
    catalog = preview.catalogue
    entries = catalog['classifications']
    decisions = {}
    pending = []
    for row in preview.rows:
        rk = row['key']
        if rk in choices:
            choice = choices[rk]
            dest = entries.get(choice) if choice is not None else None
            if choice is not None and dest is None:
                raise ValueError('A classificação escolhida não existe no catálogo de destino.')
        else:
            dest = row['proposal']
        if dest is None and not keep_pending:
            raise ValueError('Existem conflitos ou pendências. Revise-os antes de aplicar.')
        if dest is None:
            pending.append({'source': list(row['source']) if row['source'] else None,
                            'ifc_class': row['ifc_class'], 'count': row['count'],
                            'reason': row['status']})
        decisions[rk] = dest
    mutations = []
    for group in list(groups):
        if not is_bim_group(group):
            continue
        old = getattr(group, 'ifc', None)
        if not isinstance(old, dict):
            continue
        rowkey = (current_assignment(old), str(old.get('class') or ''))
        if rowkey not in decisions or decisions[rowkey] is None:
            continue
        target = decisions[rowkey]
        new = copy.deepcopy(old)
        new['classification_system'] = str(target['system'])
        new['classification_code'] = str(target['code'])
        new['classification_opt_out'] = False
        # Preserve any additional multi-classification tags. Replace only
        # the primary assignment when it appears in the IFC list.
        old_primary = rowkey[0]
        for item in new.get('classifications', []) or []:
            if isinstance(item, dict) and identity(item) == old_primary:
                item.update({'system': target['system'], 'code': target['code'],
                             'name': target.get('name', ''),
                             'location': target.get('location', '')})
        if new != old:
            mutations.append((group, copy.deepcopy(old), new))
    document = copy.deepcopy(preview.original)
    catalog_keys = []
    for key, value in entries.items():
        saved_key = key
        existing = document['libraries']['classifications']
        if saved_key in existing and existing[saved_key] != value:
            # Preserve BOTH catalogue definitions. Never damage personal
            # favourites or silently replace a published classification.
            prefix = str(catalog.get('id') or 'catalogo:destino')
            saved_key = prefix + ' / ' + key
            if saved_key in existing and existing[saved_key] != value:
                raise ValueError('Definição conflitante já existe no destino: ' + saved_key)
        existing[saved_key] = copy.deepcopy(value)
        catalog_keys.append(saved_key)
    setup = document.setdefault('project_setup', {})
    # A classification-system migration cannot silently deactivate the other
    # taxonomies already used by the same project or its objects.
    all_keys = list(setup.get('catalogue_keys') or [])
    all_keys.extend(key for key in catalog_keys if key not in all_keys)
    if preview.crosswalks:
        # Track editions of mapping catalogs used for this reviewed decision.
        existing = {c['id']: c for c in crosswalks_from_document(document)}
        existing.update({c['id']: copy.deepcopy(c) for c in preview.crosswalks})
        setup['equivalence_catalogues'] = list(existing.values())
    setup.update({'version': 1, 'catalogue_id': str(catalog.get('id') or ''),
                  'catalogue_name': str(catalog.get('name') or ''),
                  'catalogue_count': len(all_keys), 'catalogue_keys': all_keys,
                  'migration_pending': pending})
    return normalize_document_data(document), mutations, pending


class MigrateCatalogueCommand:
    """One native undo step for both IFC metadata and project setup."""
    def __init__(self, app, before, after, mutations):
        self.app = app
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        self.mutations = list(mutations)

    def _run(self, scene, forward):
        data = self.after if forward else self.before
        self.app.set_document_data(copy.deepcopy(data))
        for group, old, new in self.mutations:
            group.ifc = copy.deepcopy(new if forward else old)
        from .project_setup import catalogue_from_document
        scene._opentrace_catalogue_for_creation = catalogue_from_document(data)
        scene.version += 1

    def do(self, scene):
        self._run(scene, True)

    def undo(self, scene):
        self._run(scene, False)


def apply_migration(app, preview, choices=None, *, keep_pending=False):
    before = copy.deepcopy(app.document_data(default=None))
    groups = list(getattr(app.scene, 'groups', ()) or ())
    after, mutations, pending = build_migration(preview, groups, choices, keep_pending=keep_pending)
    # Do not silently migrate against a stale scene or catalogue selection.
    if normalize_document_data(before).get('project_setup') != preview.original.get('project_setup'):
        raise ValueError('O projeto mudou desde a prévia. Reabra a migração.')
    current = preview_migration(groups, before, preview.catalogue, list(preview.crosswalks))
    if current.signature != preview.signature:
        raise ValueError('Objetos ou classificações mudaram desde a prévia. Reabra a migração.')
    app.viewport.history.execute(MigrateCatalogueCommand(app, before, after, mutations))
    error = getattr(app.viewport.history, 'last_error', None)
    if error:
        raise RuntimeError(str(error))
    app.viewport.notify_scene_changed()
    return len(mutations), pending
