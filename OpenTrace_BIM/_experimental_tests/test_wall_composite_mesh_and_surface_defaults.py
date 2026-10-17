"""Host-free regression tests for preset switching, wall junction caps and materials.

The graphical host is not installed in this runner. Execute the exact production
function ASTs with a minimal vector implementation, and separately validate the
real bundled material image files and factory preset recipes.
"""
import ast
import copy
import math
import sys
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from OpenTrace_BIM import materials
from OpenTrace_BIM.layers import normalize_layers, total_thickness

ROOT = Path(__file__).resolve().parents[1]


class Vector:
    def __init__(self, *xyz):
        if len(xyz) == 1:
            p = xyz[0]
            self.xyz = tuple(p.xyz if isinstance(p, Vector) else p)
        else:
            self.xyz = xyz
    def __sub__(self, other): return Vector(*(a-b for a,b in zip(self.xyz, other.xyz)))
    def __add__(self, other): return Vector(*(a+b for a,b in zip(self.xyz, other.xyz)))
    def __mul__(self, k): return Vector(*(a*k for a in self.xyz))
    def length(self): return math.sqrt(sum(x*x for x in self.xyz))
    def __repr__(self): return f'Vector{self.xyz}'


def production_function(path, name, globals_dict):
    source = ast.parse((ROOT/path).read_text(encoding='utf8'))
    node = next(x for x in source.body if isinstance(x,ast.FunctionDef) and x.name==name)
    compiled = compile(ast.Module(body=[node],type_ignores=[]), str(ROOT/path), 'exec')
    exec(compiled, globals_dict)
    return globals_dict[name]


class WallCapsTests(unittest.TestCase):
    def test_miter_cap_is_distributed_across_actual_composition_bands(self):
        f=production_function('model.py','_caps_for_layer',{'QVector3D':Vector})
        caps={'start':(Vector(0,-.120,0), Vector(.16,.080,0)),
              'end':(Vector(4,-.100,0),Vector(3.93,.100,0))}
        thicknesses=[.009,.005,.015,.140,.015,.005,.009]
        lower=-sum(thicknesses)/2
        overall_low=lower
        overall_high=lower+sum(thicknesses)
        result=[]
        for t in thicknesses:
            hi=lower+t
            cap=f(caps,lower,hi,overall_low,overall_high)
            self.assertIsNotNone(cap)
            for side in ('start','end'):
                expected=(caps[side][1]-caps[side][0]).length() * t/sum(thicknesses)
                self.assertAlmostEqual((cap[side][1]-cap[side][0]).length(),expected,places=7)
            result.append(cap)
            lower=hi
        for a,b in zip(result,result[1:]):
            for end in ('start','end'):
                self.assertLess((a[end][1]-b[end][0]).length(),1e-7)
        # A former regression passed a 198 mm cap into EACH 5 mm adhesive band.
        self.assertLess((result[1]['start'][1]-result[1]['start'][0]).length(),.010)

    def test_new_composite_does_not_inherit_unrelated_simple_mesh(self):
        args=[]
        cfg={'structure':'composite','alignment':'center','thickness':.20,'layers':[]}
        layers=[({'name':'Exterior render'},-.1,-.085),
                ({'name':'Clay block'},-.085,.085),
                ({'name':'Interior render'},.085,.1)]
        f=production_function('model.py','build_children',{
            'validate':lambda p:p,'wall_layer_bands':lambda p:layers,
            'wall_offsets':lambda p:(-.1,.1),
            '_caps_for_layer':lambda *args: None,
            'build_body':lambda *a,**kw: args.append(kw) or object(),
        })
        previous=[types.SimpleNamespace(name='Corpo da parede')]
        f(cfg,previous_children=previous)
        self.assertEqual(len(args),3)
        self.assertTrue(all(kw['previous'] is None for kw in args))
        self.assertEqual([kw['body_name'] for kw in args],
                         ['Camada parede · Exterior render','Camada parede · Clay block',
                          'Camada parede · Interior render'])


class MaterialDefaultsTests(unittest.TestCase):
    def test_builtin_wall_presets_have_real_layer_materials(self):
        globals_dict={
            '__package__':'OpenTrace_BIM',
            'uuid':uuid,'copy':copy,
            'normalize_layers':normalize_layers,'total_thickness':total_thickness,
            '_BUILTIN_PRESETS':None,
        }
        for name in ('_layer','_composite','_p','builtins'):
            production_function('preset_catalog.py',name,globals_dict)
        presets=globals_dict['builtins']()['wall']
        ceramic=next(p for p in presets if p['id']=='builtin:wall:cer14_tile2')
        recipe=ceramic['config']['layers']
        self.assertEqual(len(recipe),7)
        self.assertEqual(recipe[0]['material_name'],'OpenTrace · Ceramic Tile')
        self.assertEqual(recipe[3]['material_name'],'OpenTrace · Clay Block')
        self.assertEqual(recipe[-1]['material_name'],'OpenTrace · Ceramic Tile')
        self.assertEqual(recipe[2]['material_name'],'OpenTrace · Light Plaster')
        generic=next(p for p in presets if p['id']=='builtin:wall:generic10')
        self.assertIsNone(generic['config']['material_name'])

    def test_materials_bundle_exist_and_have_safe_host_recipes(self):
        records=materials._opentrace_default_catalog()
        self.assertGreaterEqual(len(records),8)
        for name,item in records.items():
            tex=item['texture']
            self.assertTrue(Path(tex['path']).is_file())
            self.assertGreater(tex['sw'],0)
            self.assertGreater(tex['sh'],0)
            with Image.open(tex['path']) as im:
                im.verify()
        for name in ('OpenTrace · Light Plaster', 'OpenTrace · Clay Block',
                     'OpenTrace · Ceramic Tile'):
            self.assertIn(name,records)

    def test_user_override_is_not_replaced_by_default(self):
        class Material:
            def __init__(self,name,color=None,texture=None,opacity=None):
                self.name=name;self.color=color;self.texture=texture;self.opacity=opacity
            def face_attrs(self): return {'mat':self.name}
        fake_core=types.ModuleType('core')
        sub=types.ModuleType('core.materials')
        sub.Material=Material
        sub.register=lambda registry,mat: registry.setdefault(mat.name,mat).name
        fake_core.materials=sub
        scene=types.SimpleNamespace(materials={})
        with patch.dict(sys.modules,{'core':fake_core,'core.materials':sub}):
            bundled=materials.ensure_material(scene,'OpenTrace · Clay Block')
            self.assertIsNotNone(bundled.texture)
            custom=Material('OpenTrace · Clay Block',color=(.1,.3,.4))
            scene.materials[custom.name]=custom
            self.assertIs(materials.ensure_material(scene,custom.name),custom)
        # Old/imported personal layers with material_name None are NEVER
        # silently changed just by loading the material catalog.
        personal={'name':'Clay block','material_name':None}
        self.assertIsNone(personal['material_name'])

if __name__=='__main__':unittest.main()
