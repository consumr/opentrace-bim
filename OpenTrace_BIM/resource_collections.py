# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental portable hierarchical resource collections.

A collection is an index, not an eager copy of the host's material library.
Only explicitly selected assets are copied into a portable project snapshot.
The complete library remains accessible for searching and individual import.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import zipfile

SCHEMA = 'opentrace-resource-collection'
VERSION = 1
KINDS = ('wall', 'slab', 'beam', 'column', 'door', 'window', 'profile', 'material')
BUNDLED = (
    {'id': 'ot:arq:basica', 'name': 'Architecture · Basic', 'folder': 'Architecture / Basic',
     'defaults': {'wall': 3, 'slab': 2, 'beam': 2, 'column': 2, 'door': 0,
                  'window': 0, 'profile': 0, 'material': 0}},
    {'id': 'ot:arq:padrao', 'name': 'Architecture · Standard', 'folder': 'Architecture / Standard',
     'defaults': {'wall': 8, 'slab': 6, 'beam': 4, 'column': 4, 'door': 0,
                  'window': 0, 'profile': 12, 'material': 0}},
    {'id': 'ot:estrutural', 'name': 'Structure · Essential', 'folder': 'Structure / Essential',
     'defaults': {'wall': 0, 'slab': 3, 'beam': 8, 'column': 8, 'door': 0,
                  'window': 0, 'profile': 12, 'material': 0}},
)


def _safe_text(v, limit=240):
    s = str(v or '').strip()
    if len(s) > limit:
        raise ValueError('Name/path is too long.')
    return s


def validate_collection(raw):
    if not isinstance(raw, dict) or raw.get('format') != SCHEMA or raw.get('version') != VERSION:
        raise ValueError('Invalid OpenTrace library format.')
    ident = _safe_text(raw.get('id'))
    name = _safe_text(raw.get('name'))
    if not ident or not name:
        raise ValueError('Library requires an ID and name.')
    resources = raw.get('resources', [])
    if not isinstance(resources, list) or len(resources) > 50000:
        raise ValueError('Invalid or oversized library.')
    unique = set()
    clean = []
    for rec in resources:
        if not isinstance(rec, dict) or rec.get('kind') not in KINDS:
            raise ValueError('Invalid resource type.')
        rid = _safe_text(rec.get('id'))
        folder = _safe_text(rec.get('folder', ''), 500)
        if not rid or folder.startswith('/') or '..' in folder.split('/'):
            raise ValueError('Invalid resource ID or folder.')
        key = (rec['kind'], rid)
        if key in unique:
            raise ValueError('Duplicate resource in library.')
        unique.add(key)
        data = rec.get('data', {})
        if data is not None and not isinstance(data, dict):
            raise ValueError('Invalid resource data.')
        clean.append({'kind':rec['kind'], 'id':rid, 'name':_safe_text(rec.get('name') or rid),
                      'folder':folder, 'data':copy.deepcopy(data or {}),
                      'source':_safe_text(rec.get('source', ''))})
    return {'format':SCHEMA, 'version':VERSION, 'id':ident, 'name':name,
            'folder':_safe_text(raw.get('folder',''),500), 'resources':clean}


def make_collection(name, resources, *, ident='user:collection', folder=''):
    return validate_collection({'format':SCHEMA,'version':VERSION,'id':ident,
                                'name':name,'folder':folder,'resources':list(resources)})


def serialize_collection(data):
    return json.dumps(validate_collection(data), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def write_collection(data, target):
    """Exclusive write; no overwrite and no out-of-archive path traversal."""
    path = Path(target)
    encoded = serialize_collection(data).encode('utf-8')
    if len(encoded) > 25*1024*1024:
        raise ValueError('Library metadata exceeds the 25 MB limit.')
    with path.open('xb') as fp:
        fp.write(encoded)
    return path


def read_collection(path):
    path = Path(path)
    if path.stat().st_size > 25*1024*1024:
        raise ValueError('Library metadata exceeds the 25 MB limit.')
    return validate_collection(json.loads(path.read_text(encoding='utf-8')))


def resource_index(collections):
    """folder -> records. A folder may contain nested subfolders."""
    folders = {}
    for collection in collections:
        pack = validate_collection(collection)
        for rec in pack['resources']:
            route = '/'.join(x.strip() for x in
                             (pack['folder']+'/'+rec['folder']).split('/') if x.strip())
            folders.setdefault(route or 'Geral', []).append(rec)
    return folders


def search_resources(collections, query='', kind=None):
    needle = str(query).casefold().strip()
    results = []
    for folder, recs in resource_index(collections).items():
        for rec in recs:
            if kind and rec['kind'] != kind:
                continue
            if needle and needle not in (folder+' '+rec['name']+' '+rec['id']).casefold():
                continue
            results.append((folder, rec))
    return results


def sample_collections(presets=None, profiles=None):
    """Three *real* small starter indexes; never invent geometry/recipes."""
    presets = presets or {}
    profiles = profiles or []
    out = []
    for spec in BUNDLED:
        entries = []
        for kind, count in spec['defaults'].items():
            pool = profiles if kind == 'profile' else presets.get(kind, ())
            choices=list(pool)[:count]
            # Do not let insertion order hide drywall or structural masonry
            # from starter wall packs when the master catalog grows.
            if kind=='wall' and spec['id'] in ('ot:arq:basica','ot:arq:padrao'):
                wanted=('builtin:wall:dry95',) if spec['id']=='ot:arq:basica' else (
                    'builtin:wall:dry95','builtin:wall:dry120',
                    'builtin:wall:struct_con_19','builtin:wall:brick_render',
                    'builtin:wall:wet_con14')
                present={str(x.get('id')) for x in choices if isinstance(x,dict)}
                for identifier in wanted:
                    for candidate in pool:
                        if candidate.get('id')==identifier and identifier not in present:
                            choices.append(candidate);present.add(identifier);break
            for src in choices:
                if not isinstance(src, dict):
                    continue
                ident = str(src.get('id') or '')
                if not ident:
                    continue
                entries.append({'kind':kind, 'id':ident, 'name':src.get('name',ident),
                                'folder':({'wall':'Walls','slab':'Slabs','beam':'Beams',
                                           'column':'Columns','profile':'Complex profiles'}
                                          .get(kind,kind)), 'data':copy.deepcopy(src),
                                'source':'opentrace:bundled'})
        out.append(make_collection(spec['name'], entries, ident=spec['id'], folder=spec['folder']))
    return out


def capture_personal_resources():
    """Capture per-user presets/profiles at template-save time, not at startup."""
    from .preset_catalog import load_personal
    from .profile_library import load_personal_profiles
    from .resource_presets import load_wall_presets
    from .composition_library import _load_personal_compositions
    entries = []
    folders = {'wall':'Walls','slab':'Slabs','beam':'Beams',
               'column':'Columns','door':'Doors','window':'Windows'}
    for kind, items in load_personal().items():
        if kind not in KINDS:
            continue
        for item in items:
            entries.append({'kind':kind,'id':str(item.get('id') or item.get('name')),
                            'name':str(item.get('name') or 'Preset'),
                            'folder':folders.get(kind,'Objects'), 'data':item,
                            'source':'user:presets'})
    for item in load_wall_presets():
        entries.append({'kind':'wall','id':'wall-personal:'+str(item['id']),
                        'name':item['name'],'folder':'Walls / Favorites',
                        'data':item,'source':'user:wall_presets'})
    for item in load_personal_profiles():
        entries.append({'kind':'profile','id':str(item['id']),'name':item['name'],
                        'folder':'Complex profiles / '+str(item.get('folder') or 'Personal'),
                        'data':item,'source':'user:profiles'})
    # Compositions are reusable wall definitions: retain their physical layers.
    for name, layers in _load_personal_compositions().items():
        entries.append({'kind':'wall','id':'composition:'+name,'name':name,
                        'folder':'Walls / Compositions',
                        'data':{'name':name,'layers':layers},'source':'user:compositions'})
    return make_collection('My favorites and resources', entries,
                           ident='user:favorites', folder='Personal')


def classify_material(name, recipe=None):
    """Conservative search-category inference, not a normative classification."""
    import unicodedata
    recipe = recipe if isinstance(recipe, dict) else {}
    texture = recipe.get('texture')
    path = str(texture.get('path','')) if isinstance(texture,dict) else ''
    src = (str(name) + ' ' + path).lower()
    src = ''.join(ch for ch in unicodedata.normalize('NFKD',src) if not unicodedata.combining(ch))
    def has(*tokens): return any(token in src for token in tokens)
    if str(name).upper().startswith('RAL '): return 'Pinturas / Cores RAL'
    if has('tijol','brick','block','bloco','masonry'): return 'Blocos ou Tijolos'
    if has('concret','cimento','cement','reboco','argamassa','plaster','stucco','mortar'): return 'Cimentos e Argamassas'
    if has('paint','tinta','pintura','limewash','pigment'): return 'Pinturas'
    if has('metal','steel','inox','alumin','ferro','iron','aco','cobre','brass','bronze','chrome'): return 'Metais'
    if has('stone','pedra','granito','marble','marmore','travert','limestone','quartz','ardosia','slate'): return 'Pedras'
    if has('ceramic','ceram','tile','porcelanato','azulejo','revest','mosaic','mosaico'): return 'Revestimentos'
    if has('wood','madeira','oak','carvalho','walnut','nogueira','mdf','laminado','veneer'): return 'Madeiras e Laminados'
    if has('glass','vidro','espelho','mirror'): return 'Vidros e Espelhos'
    if has('fabric','tecido','wallpaper','papel de parede','pattern','estampa','floral','carpet','tapete'): return 'Estampas e Tecidos'
    return 'Diversos'


def material_folders(names, *, catalog=None):
    """Folders are virtual: no bulk loading or material renaming occurs."""
    folders={}
    for name in sorted(set(str(n) for n in names),key=str.casefold):
        recipe=(catalog or {}).get(name,{})
        group=classify_material(name,recipe)
        folders.setdefault(group,[]).append(name)
    return folders
