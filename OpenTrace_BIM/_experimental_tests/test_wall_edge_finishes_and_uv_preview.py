"""Host-free tests for cosmetic wall edge finishes and preview texture projection."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from OpenTrace_BIM.wall_edge_finishes import (
    EDGE_FACES, normalize_edge_finishes, face_material_assignments,
    stamp_wall_edge_finishes,
)

ROOT=Path(__file__).resolve().parents[1]
KEY="arquitetura_parametrica"


class FakeFace:
    def __init__(self,key,layer):
        self.attrs={"ap_wall_side":key,"mat":layer,"color":(0.5,0.5,0.5)}


class FakeWall:
    def __init__(self,layers=("Base Plaster", "Clay Block")):
        self.children=[]
        for name in layers:
            faces=[FakeFace(key,name) for key in ("start","end","top","bottom","side","opening")]
            self.children.append(SimpleNamespace(mesh=SimpleNamespace(faces=faces)))
        self.ext={KEY:{"kind":"wall","edge_materials":{}}}


class FakeScene:
    def __init__(self, wall):
        self.groups=[wall]
        self.edit_group=None
        self.version=1
        self.materials={}
    def entity_selectable(self,wall):return wall in self.groups


def runtime_values(wall):
    return {"structure":"composite","layers":[{"material_name":name}
             for name in ("Base Plaster","Clay Block")],
            "edge_materials":copy.deepcopy(wall.ext[KEY].get("edge_materials", {}))}


class EdgeFinishTests(TestCase):
    def test_names_are_sanitized_without_reformatting_users_material(self):
        got=normalize_edge_finishes({"start":" My Stone ","top":"","side":"Do not touch",
                                    "end":42,"bottom":"Plain Steel"})
        self.assertEqual(got,{"start":"My Stone","bottom":"Plain Steel"})
        self.assertEqual(normalize_edge_finishes(None),{})
        self.assertEqual(normalize_edge_finishes([1,2]),{})

    def test_edge_matching_excludes_long_side_and_openings(self):
        wall=FakeWall()
        attrs=list(face_material_assignments(wall,{**runtime_values(wall),
                         "edge_materials":{"top":"New Tile"}}))
        self.assertEqual(len(attrs),8)
        self.assertEqual(sum(mat=="New Tile" for _,mat,_ in attrs),2)
        self.assertEqual({f.attrs["ap_wall_side"] for f,_,_ in attrs},set(EDGE_FACES))
        self.assertEqual([b for face,ov,b in attrs if face.attrs["ap_wall_side"]=="end"],
                         ["Base Plaster","Clay Block"])

    def test_stamps_top_and_start_without_touching_long_sides_or_opens(self):
        wall=FakeWall()
        data={**runtime_values(wall),"edge_materials":{"start":"Stone","top":"Tile"}}
        def recipe(scene,name):return {"mat":name,"color":(0.2,0.3,0.4)}
        with patch("OpenTrace_BIM.materials.material_face_attrs",side_effect=recipe):
            count=stamp_wall_edge_finishes(wall,object(),data)
        self.assertEqual(count,4)
        for layer in wall.children:
            faces={f.attrs["ap_wall_side"]:f for f in layer.mesh.faces}
            self.assertEqual(faces["start"].attrs["mat"],"Stone")
            self.assertEqual(faces["top"].attrs["mat"],"Tile")
            self.assertNotEqual(faces["side"].attrs["mat"],"Tile")
            self.assertNotEqual(faces["opening"].attrs["mat"],"Stone")

    def test_no_override_means_no_custom_stamping(self):
        wall=FakeWall()
        with patch("OpenTrace_BIM.materials.material_face_attrs",side_effect=AssertionError):
            self.assertEqual(stamp_wall_edge_finishes(wall,object(),runtime_values(wall)),0)

    def test_removing_override_restores_respective_layer_material(self):
        wall=FakeWall()
        def recipe(scene,name):return {"mat":name,"color":(0.1,0.2,0.3)}
        with patch("OpenTrace_BIM.materials.material_face_attrs",side_effect=recipe):
            stamp_wall_edge_finishes(wall,object(),{**runtime_values(wall),
                                     "edge_materials":{"start":"Granite"}})
            stamp_wall_edge_finishes(wall,object(),runtime_values(wall),restore_defaults=True)
        for index,child in enumerate(wall.children):
            self.assertEqual(child.mesh.faces[0].attrs["mat"],
                             ("Base Plaster","Clay Block")[index])

    def test_undo_redo_paints_only_faces_and_keeps_geometry_identity(self):
        source=ast.parse((ROOT/'commands.py').read_text(encoding='utf-8'))
        node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='PaintWallEdgeFinishes')
        env={'__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
             'root_edit_allowed':lambda scene:None,'WallError':ValueError,
             'KEY':KEY,'copy':copy,'wall_record':lambda wall:wall.ext[KEY],
             'normalize_edge_finishes':normalize_edge_finishes,
             'read_wall':runtime_values}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
        Command=env['PaintWallEdgeFinishes']
        wall=FakeWall()
        scene=FakeScene(wall)
        original_areas=[f for child in wall.children for f in child.mesh.faces]
        old_attributes=[copy.deepcopy(f.attrs) for f in original_areas]
        cmd=Command(scene,wall,{"start":"Stone","top":"Tile"})
        def recipe(scene,name):return {"mat":name,"color":(0.22,0.33,0.44)}
        with patch("OpenTrace_BIM.materials.material_face_attrs",side_effect=recipe):
            cmd.do(scene)
            self.assertEqual(wall.ext[KEY]["edge_materials"],{"start":"Stone","top":"Tile"})
            self.assertEqual(original_areas[0].attrs["mat"],"Stone")
            self.assertIs(original_areas[0],wall.children[0].mesh.faces[0])
            cmd.undo(scene)
            self.assertEqual(wall.ext[KEY]["edge_materials"],{})
            self.assertEqual([f.attrs for f in original_areas],old_attributes)
            cmd.do(scene)
            self.assertEqual(wall.ext[KEY]["edge_materials"]["top"],"Tile")
            self.assertEqual(original_areas[2].attrs["mat"],"Tile")
            # another undo to ensure all metadata/faces return completely
            cmd.undo(scene)
            self.assertEqual([f.attrs for f in original_areas],old_attributes)

    def test_junction_signature_excludes_cosmetic_finishes(self):
        source=(ROOT/'ui.py').read_text(encoding='utf-8')
        self.assertIn('k not in ("caps", "edge_materials", "material_name")',source)

    def test_composite_and_rectangular_wall_creation_stamps_finishes(self):
        source=(ROOT/'commands.py').read_text(encoding='utf-8')
        self.assertGreaterEqual(source.count('stamp_wall_edge_finishes('),3)
        self.assertIn('stamp_wall_edge_finishes(group, scene, rec)',source)
        self.assertIn('stamp_wall_edge_finishes(temp, scene, p)',source)

    def test_preview_texture_is_projected_along_isometric_face(self):
        source=(ROOT/'wall_visuals.py').read_text(encoding='utf-8')
        self.assertIn('p.setTransform(transform, combine=True)',source)
        self.assertNotIn('p.setClipRegion(QRegion(',source)
        # Mapping the source image's horizontal courses to the tilted facade.
        upper_left=(40,55);upper_right=(218,90);lower_left=(40,133)
        tw,th=256,128
        m11=(upper_right[0]-upper_left[0])/tw
        m12=(upper_right[1]-upper_left[1])/tw
        m21=(lower_left[0]-upper_left[0])/th
        m22=(lower_left[1]-upper_left[1])/th
        transform=lambda u,v:(m11*u+m21*v+upper_left[0],m12*u+m22*v+upper_left[1])
        self.assertEqual(transform(tw,0),upper_right)
        self.assertEqual(transform(0,th),lower_left)
        self.assertEqual(transform(tw,th),(218,168))
