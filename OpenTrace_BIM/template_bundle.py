# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone, non-destructive complete OpenTrace template (.ottemplate).

Contains a host-native .igz scene plus selected portable resource collections.
The source/current project is never rewritten or renamed during export.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

from .resource_collections import validate_collection

FORMAT = 'opentrace-full-template'
FILES = ('scene.igz', 'resources.json', 'manifest.json')


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get('format') != FORMAT or manifest.get('version') != 1:
        raise ValueError('Template OpenTrace inválido ou incompatível.')
    if not str(manifest.get('name') or '').strip():
        raise ValueError('Nome de template ausente.')
    return manifest


def inspect_template(source):
    with ZipFile(source) as z:
        names = set(z.namelist())
        if names != set(FILES):
            raise ValueError('O template contém arquivos ausentes ou inesperados.')
        if z.getinfo('scene.igz').file_size > 3*1024**3:
            raise ValueError('Cena muito grande para importar.')
        if z.getinfo('resources.json').file_size > 25*1024**2:
            raise ValueError('Metadados de recursos excessivamente grandes.')
        manifest = validate_manifest(json.loads(z.read('manifest.json').decode('utf-8')))
        resources = json.loads(z.read('resources.json').decode('utf-8'))
        if not isinstance(resources, list) or len(resources) > 100:
            raise ValueError('Bibliotecas de template inválidas.')
        resources = [validate_collection(x) for x in resources]
        return copy.deepcopy(manifest), resources


def extract_template(source, dest):
    """Extract scene to *new* .igz; never overwrite existing projects."""
    manifest, collections = inspect_template(source)
    target = Path(dest)
    if target.suffix.lower() != '.igz':
        raise ValueError('A cena de destino precisa ser .igz.')
    created = False
    try:
        with target.open('xb') as fp:
            created = True
            with ZipFile(source) as z, z.open('scene.igz') as scene:
                import shutil
                shutil.copyfileobj(scene, fp, length=1024*1024)
    except FileExistsError as exc:
        raise ValueError('O projeto de destino já existe; nenhum arquivo será sobrescrito.') from exc
    except Exception:
        if created:
            try: target.unlink()
            except OSError: pass
        raise
    return manifest, collections


def save_complete_template(app, target, name, selected_collections):
    """Export the active *real* scene without changing the currently open file.

    Requires host runtime. Native scene serialisation includes geometry,
    document layers and material data; the sidecar contains the portable
    presets, profiles and selected library packs.
    """
    from core import igz_format
    import os
    target = Path(target)
    if target.suffix.lower() != '.ottemplate':
        raise ValueError('Extensão esperada: .ottemplate')
    payload = [validate_collection(c) for c in selected_collections]
    resources = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(resources) > 25*1024**2:
        raise ValueError('Metadados de recursos excedem 25 MB.')
    manifest = {'format':FORMAT, 'version':1, 'name':str(name).strip(),
                'collections':[x['id'] for x in payload]}
    validate_manifest(manifest)
    if target.exists():
        raise ValueError('Destino já existe. Escolha outro nome para não substituir arquivos.')
    with TemporaryDirectory(prefix='ot_template_') as tmp:
        path = Path(tmp)/'scene.igz'
        igz_format.save_scene(app.scene, path)
        with target.open('xb') as fp:
            with ZipFile(fp, 'w', ZIP_DEFLATED, compresslevel=6) as z:
                z.write(path, 'scene.igz')
                z.writestr('resources.json', resources)
                z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False).encode('utf-8'))
    return target
