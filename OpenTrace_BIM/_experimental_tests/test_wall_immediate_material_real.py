"""Regression: wall material pick must paint actual faces without Apply preset.

These are headless face/host-cache tests, not a Windows UI acceptance test.
"""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from OpenTrace_BIM.wall_edge_finishes import invalidate_wall_face_appearance, stamp_wall_edge_finishes
from OpenTrace_BIM.materials import stamp_structured_materials

ROOT = Path(__file__).resolve().parents[1]
KEY = 'arquitetura_parametrica'


def make_wall():
    faces = [SimpleNamespace(attrs={'ap_wall_side': s, 'mat': 'Old', 'color': (0.5, 0.5, 0.5)})
             for s in ('left', 'right', 'start', 'end', 'top', 'bottom')]
    mesh = SimpleNamespace(faces=faces, _attrs_dirty=False, _chunk_dirty=False,
                           _mut_serial=11)
    group = SimpleNamespace(children=[SimpleNamespace(mesh=mesh)],
                            ext={KEY: {'kind': 'wall', 'material_name': 'Old',
                                       'edge_materials': {'top': 'Cap'},
                                       'structure': 'simple'}})
    scene = SimpleNamespace(groups=[group], edit_group=None, version=15)
    scene.entity_selectable = lambda g: g is group
    return group, scene, mesh


def real_recipe(scene, name):
    recipes = {
        'Old': {'mat': 'Old', 'color': (0.5, 0.5, 0.5)},
        'New': {'mat': 'New', 'color': (0.95, 0.2, 0.2)},
        'Cap': {'mat': 'Cap', 'color': (0.1, 0.1, 0.9)},
    }
    return copy.deepcopy(recipes.get(name))


def command_type():
    tree = ast.parse((ROOT / 'commands.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                and n.name == 'PaintWallBodyMaterial')
    env = {'__name__': 'OpenTrace_BIM.commands_live_test',
           '__package__': 'OpenTrace_BIM', 'Command': type('Command', (), {}),
           'root_edit_allowed': lambda scene: None,
           'WallError': ValueError, 'KEY': KEY,
           'copy': copy, 'stamp_structured_materials': stamp_structured_materials,
           'stamp_wall_edge_finishes': stamp_wall_edge_finishes,
           'read_wall': lambda g: g.ext[KEY]}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'commands.py'), 'exec'), env)
    return env['PaintWallBodyMaterial']


class WallDirectMaterialTests(unittest.TestCase):
    def test_paint_immediate_without_rebuilding_faces_and_keeps_cap(self):
        wall, scene, mesh = make_wall()
        initial_face_ids = [id(face) for face in mesh.faces]
        command = command_type()(scene, wall, 'New')
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=real_recipe):
            command.do(scene)
        self.assertEqual([id(face) for face in mesh.faces], initial_face_ids)
        self.assertEqual([f.attrs['mat'] for f in mesh.faces],
                         ['New', 'New', 'New', 'New', 'Cap', 'New'])
        self.assertEqual(wall.ext[KEY]['material_name'], 'New')
        self.assertTrue(mesh._attrs_dirty and mesh._chunk_dirty)
        self.assertEqual(mesh._mut_serial, 11)
        mesh._attrs_dirty = mesh._chunk_dirty = False
        command.undo(scene)
        self.assertEqual(wall.ext[KEY]['material_name'], 'Old')
        self.assertEqual([f.attrs['mat'] for f in mesh.faces], ['Old'] * 6)
        self.assertTrue(mesh._attrs_dirty and mesh._chunk_dirty)
        mesh._attrs_dirty = mesh._chunk_dirty = False
        command.do(scene)
        self.assertEqual(mesh.faces[0].attrs['mat'], 'New')
        self.assertEqual(mesh.faces[4].attrs['mat'], 'Cap')
        self.assertTrue(mesh._attrs_dirty and mesh._chunk_dirty)

    def test_missing_material_is_error_with_no_visual_or_metadata_change(self):
        wall, scene, mesh = make_wall()
        before = copy.deepcopy([f.attrs for f in mesh.faces])
        command = command_type()(scene, wall, 'Not installed')
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=real_recipe):
            with self.assertRaisesRegex(ValueError, 'not found'):
                command.do(scene)
        self.assertEqual(wall.ext[KEY]['material_name'], 'Old')
        self.assertEqual([f.attrs for f in mesh.faces], before)
        self.assertEqual(scene.version, 15)

    def test_none_material_clears_old_paint_and_keeps_edge_override(self):
        wall, scene, mesh = make_wall()
        command = command_type()(scene, wall, None)
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=real_recipe):
            command.do(scene)
        self.assertIsNone(wall.ext[KEY]['material_name'])
        self.assertNotIn('mat', mesh.faces[0].attrs)
        self.assertEqual(mesh.faces[4].attrs['mat'], 'Cap')

    def test_ui_material_signal_has_distinct_action_and_no_preset_apply(self):
        ui = (ROOT / 'ui.py').read_text(encoding='utf-8')
        body = ui[ui.index('def wall_material_changed'): ui.index('def edge_finishes_changed')]
        self.assertIn('self.material.currentIndexChanged.connect(self.wall_material_changed)', ui)
        self.assertIn('PaintWallBodyMaterial(self.app.scene, target, chosen)', body)
        self.assertIn('self.app.viewport.history.execute(cmd)', body)
        self.assertIn('self.app.viewport.notify_scene_changed()', body)
        self.assertNotIn('EditWall(', body)
        preset = (ROOT / 'preset_catalog.py').read_text(encoding='utf-8')
        self.assertIn('self.apply_btn.clicked.connect(self.apply)', preset)
        self.assertIn('apply_preset(self.kind,self.controller,p)', preset)

    def test_material_edits_precede_creation_defaults_when_wall_selected(self):
        ui = (ROOT / 'ui.py').read_text(encoding='utf-8')
        body = ui[ui.index('def defaults_changed'):ui.index('def preview_length')]
        self.assertLess(body.index('if self.target is not None'),
                        body.index('if self.app.viewport.active_tool is self.draw_tool:'))

if __name__ == '__main__':
    unittest.main()
