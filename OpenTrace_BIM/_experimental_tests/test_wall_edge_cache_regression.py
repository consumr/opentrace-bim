"""Regression for appearance-only edits bypassing the IngeTrazo VBO cache.

The host viewport can reuse cached chunks when _mut_serial is unchanged and
_attrs_dirty is false; incrementing scene.version alone does not repaint.
"""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from OpenTrace_BIM.wall_edge_finishes import (
    stamp_wall_edge_finishes, WallEdgeMaterialError,
    invalidate_wall_face_appearance, normalize_edge_finishes,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = 'arquitetura_parametrica'


def make_group():
    meshes=[]
    for layer in ('OpenTrace · Concrete', 'OpenTrace · Clay Block'):
        faces=[SimpleNamespace(attrs={'ap_wall_side':side, 'mat':layer,
                                       'color':(0.6,0.6,0.6)})
               for side in ('start', 'end', 'top', 'bottom', 'side', 'opening')]
        meshes.append(SimpleNamespace(faces=faces, _mut_serial=17,
                                      _attrs_dirty=False, _chunk_dirty=False))
    group=SimpleNamespace(
        children=[SimpleNamespace(mesh=m) for m in meshes],
        ext={KEY:{'kind':'wall', 'edge_materials':{}}},
    )
    return group, meshes


def record_values(group):
    return {'structure':'composite',
            'layers':[{'material_name':name}
                      for name in ('OpenTrace · Concrete','OpenTrace · Clay Block')],
            'edge_materials':copy.deepcopy(group.ext[KEY]['edge_materials'])}


def native_recipe(scene, name):
    if name == 'Not installed':
        return None
    return {'mat':name,'color':(0.9,0.3,0.2)}


class WallEdgeRenderCacheRegression(TestCase):
    def test_face_paint_sets_native_render_cache_dirty_with_no_mesh_changes(self):
        wall, meshes=make_group()
        data={**record_values(wall), 'edge_materials':{'top':'Brick','end':'Render'}}
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=native_recipe):
            self.assertEqual(stamp_wall_edge_finishes(wall,object(),data),4)
        for mesh in meshes:
            self.assertTrue(mesh._attrs_dirty)
            self.assertTrue(mesh._chunk_dirty)
            self.assertEqual(mesh._mut_serial,17)  # no geometry change
            self.assertEqual(mesh.faces[2].attrs['mat'],'Brick')
            self.assertEqual(mesh.faces[1].attrs['mat'],'Render')
            self.assertEqual(mesh.faces[4].attrs['mat'],'OpenTrace · Concrete'
                             if mesh is meshes[0] else 'OpenTrace · Clay Block')

    def test_missing_native_material_does_not_repaint_or_mark_dirty(self):
        wall, meshes=make_group()
        before=copy.deepcopy([[f.attrs for f in m.faces] for m in meshes])
        data={**record_values(wall),'edge_materials':{'start':'Brick','top':'Not installed'}}
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=native_recipe):
            with self.assertRaisesRegex(WallEdgeMaterialError,'Not installed'):
                stamp_wall_edge_finishes(wall,object(),data)
        self.assertEqual([[f.attrs for f in m.faces] for m in meshes],before)
        self.assertFalse(any(m._attrs_dirty for m in meshes))

    def test_undo_redo_dirty_flags_repaint_without_mesh_regeneration(self):
        source=ast.parse((ROOT/'commands.py').read_text(encoding='utf-8'))
        node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='PaintWallEdgeFinishes')
        wall,meshes=make_group()
        scene=SimpleNamespace(groups=[wall],edit_group=None,version=4)
        scene.entity_selectable=lambda group:group is wall
        env={'__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
             'root_edit_allowed':lambda s:None,'WallError':ValueError,
             'KEY':KEY,'copy':copy,'wall_record':lambda w:w.ext[KEY],
             'normalize_edge_finishes':normalize_edge_finishes,
             'read_wall':record_values}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
        command=env['PaintWallEdgeFinishes'](scene,wall,{'start':'Brick'})
        original_attrs=copy.deepcopy(meshes[0].faces[0].attrs)
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=native_recipe):
            command.do(scene)
            self.assertTrue(all(m._attrs_dirty for m in meshes))
            self.assertEqual(meshes[0].faces[0].attrs['mat'],'Brick')
            for m in meshes:m._attrs_dirty=False;m._chunk_dirty=False  # renderer consumed
            command.undo(scene)
            self.assertEqual(meshes[0].faces[0].attrs,original_attrs)
            self.assertTrue(all(m._attrs_dirty and m._chunk_dirty for m in meshes))
            for m in meshes:m._attrs_dirty=False;m._chunk_dirty=False
            command.do(scene)
            self.assertEqual(meshes[0].faces[0].attrs['mat'],'Brick')
            self.assertTrue(all(m._attrs_dirty for m in meshes))
            self.assertEqual([m._mut_serial for m in meshes],[17,17])
            self.assertEqual(wall.ext[KEY]['edge_materials'],{'start':'Brick'})

    def test_command_rejects_missing_recipe_before_altering_wall_record(self):
        source=ast.parse((ROOT/'commands.py').read_text(encoding='utf-8'))
        node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='PaintWallEdgeFinishes')
        wall,meshes=make_group()
        scene=SimpleNamespace(groups=[wall],edit_group=None,version=4)
        scene.entity_selectable=lambda group:group is wall
        env={'__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
             'root_edit_allowed':lambda s:None,'WallError':ValueError,
             'KEY':KEY,'copy':copy,'wall_record':lambda w:w.ext[KEY],
             'normalize_edge_finishes':normalize_edge_finishes,
             'read_wall':record_values}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
        command=env['PaintWallEdgeFinishes'](scene,wall,{'start':'Not installed'})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=native_recipe):
            with self.assertRaisesRegex(ValueError,'Not installed'):
                command.do(scene)
        self.assertEqual(wall.ext[KEY]['edge_materials'],{})
        self.assertFalse(any(m._attrs_dirty for m in meshes))

    def test_invalidation_handles_empty_groups(self):
        self.assertEqual(invalidate_wall_face_appearance(SimpleNamespace(children=[])),0)
