# SPDX-License-Identifier: GPL-3.0-or-later
"""Single-resource and curated library exchange; never mutates a source file.

A portable resource is a parametric *recipe*, not an already-created mesh.
Geometry and object IDs of a scene remain separate from library identities.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import uuid
from .resource_collections import make_collection, validate_collection, read_collection

ITEM_FORMAT = 'opentrace-resource-item'
ITEM_VERSION = 1
MAX_ITEM_BYTES = 2 * 1024 * 1024
KIND_LABELS = {'wall':'wall','slab':'slab','beam':'beam','column':'column',
               'profile':'complex profile','door':'door','window':'window',
               'material':'material'}


def export_resource(record, target):
    # Same validator used by whole libraries, including path and kind limits.
    clean = make_collection('Resource', [record], ident='opentrace:single')['resources'][0]
    raw = {'format': ITEM_FORMAT, 'version': ITEM_VERSION, 'resource': clean}
    data = json.dumps(raw, ensure_ascii=False, indent=2).encode('utf-8')
    if len(data) > MAX_ITEM_BYTES:
        raise ValueError('Resource exceeds 2 MB.')
    with Path(target).open('xb') as handle:
        handle.write(data)
    return clean


def import_resource_file(path):
    path = Path(path)
    if path.stat().st_size > MAX_ITEM_BYTES:
        raise ValueError('Resource exceeds 2 MB.')
    raw = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(raw, dict):
        raise ValueError('Invalid resource.')
    if raw.get('format') == ITEM_FORMAT and raw.get('version') == ITEM_VERSION:
        return make_collection('Resource', [raw.get('resource')], ident='opentrace:single')['resources'][0]
    if raw.get('format') == 'parametric-architecture-preset':
        preset = raw.get('preset')
        if not isinstance(preset, dict):
            raise ValueError('Invalid preset.')
        kind = str(preset.get('kind') or '')
        return make_collection('Resource', [{'kind':kind, 'id':str(preset.get('id') or uuid.uuid4().hex),
               'name':str(preset.get('name') or 'Preset'),
               'folder':'Objects / '+KIND_LABELS.get(kind,kind),
               'data':preset,'source':'legacy:apreset'}], ident='opentrace:single')['resources'][0]
    raise ValueError('File is not a valid OpenTrace .otitem or .apreset resource.')


def collection_of_resources(name, resources, *, folder='My libraries'):
    # Equal source IDs may occur between folders: create independent record
    # identities for export while preserving the recipe in its payload.
    out=[]
    for rec in resources:
        item=copy.deepcopy(rec)
        if any(prev['kind']==item['kind'] and prev['id']==item['id'] for prev in out):
            item['id']='copy:'+uuid.uuid4().hex
        out.append(item)
    return make_collection(name,out,ident='user:'+uuid.uuid4().hex,folder=folder)


def add_to_personal_library(rec, *, existing=None):
    """Import selected recipe without changing modeled objects.

    Returns type and new personal ID. Door/window recipes are stored in the
    portable store; the geometry engine does not yet consume them as defaults.
    """
    kind=rec['kind']; data=copy.deepcopy(rec.get('data') or {})
    if kind in ('wall','slab','beam','column'):
        if not isinstance(data.get('config'),dict):
            if kind=='wall' and isinstance(data.get('layers'),list):
                layers=copy.deepcopy(data['layers'])
                data={'name':rec['name'],'kind':'wall','group':'Imported',
                      'config':{'structure':'composite','layers':layers,
                       'thickness':sum(float(layer.get('thickness',0)) for layer in layers)}}
            else:
                raise ValueError('This resource has no usable parametric preset.')
        from .preset_catalog import upsert_personal
        data['id']=uuid.uuid4().hex
        data['builtin']=False
        return kind, upsert_personal(kind,data)['id']
    if kind == 'profile':
        from .profile_library import upsert_profile
        if not isinstance(data.get('loops'),list):
            raise ValueError('Profile has no boundary points.')
        data['id']=uuid.uuid4().hex;data['builtin']=False;data['readonly']=False
        return kind, upsert_profile(data)['id']
    if kind in ('door','window'):
        # Portable favourite is available for library exchange; not auto-applied
        # until door/window controllers support preset injection.
        from .resource_favourites import save_favourite
        return kind, save_favourite(kind, (data.get('config') or data), name=rec['name'])['id']
    if kind == 'material':
        if existing is None:
            raise ValueError('No active project to apply the material.')
        from .materials import ensure_material
        mat=ensure_material(existing,rec['name'])
        if mat is None and data:
            # Portable color definitions and existing local texture paths can
            # be instantiated lazily, without importing the entire archive.
            from .materials import _material_from_recipe
            from pathlib import Path
            recipe=copy.deepcopy(data)
            tex=recipe.get('texture')
            if isinstance(tex,dict) and tex.get('path') and not Path(tex['path']).is_file():
                if recipe.get('color') is None:
                    raise ValueError('Source texture is missing. Import its image before using this material.')
                recipe['texture']=None
            registry=getattr(existing,'materials',None)
            if registry is None:raise ValueError('Document has no material registry.')
            registry[rec['name']]=_material_from_recipe(rec['name'],recipe)
            mat=registry[rec['name']]
        if mat is None:
            raise ValueError('Material is not available in this installation.')
        return kind, rec['name']
    raise ValueError('Resource type is not supported yet.')
