"""Regression for actual collection loading and physically defined wall recipes.

Pure production functions are isolated from the Windows-only PySide6 host.
"""
import ast
import copy
import sys
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from OpenTrace_BIM.layers import normalize_layers,total_thickness
from OpenTrace_BIM.resource_collections import validate_collection, sample_collections
from OpenTrace_BIM.materials import default_wall_layer_material,_opentrace_default_catalog

ROOT=Path(__file__).resolve().parents[1]

def read_function(file,name,globals_dict):
    tree=ast.parse((ROOT/file).read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/file),'exec'),globals_dict)
    return globals_dict[name]

def recipes():
    space={'__package__':'OpenTrace_BIM','uuid':uuid,'copy':copy,
           'normalize_layers':normalize_layers,'total_thickness':total_thickness,
           '_BUILTIN_PRESETS':None}
    for name in ('_layer','_composite','_p','builtins'):
        read_function('preset_catalog.py',name,space)
    return space['builtins']()

class DummyNode:
    def __init__(self,record=None,checked=False,children=()):
        self.record=record;self.checked=checked;self.children=list(children)
    def childCount(self):return len(self.children)
    def child(self,i):return self.children[i]
    def checkState(self,column):return 2 if self.checked else 0
    def data(self,column,role):return self.record

class DummyTree:
    def __init__(self,roots):self.roots=roots
    def topLevelItem(self,i):return self.roots[i]

class SelectionRegression(unittest.TestCase):
    def test_complete_architecture_is_a_real_selectable_collection(self):
        all_presets=recipes()
        fake_preset=types.ModuleType('OpenTrace_BIM.preset_catalog')
        fake_preset.builtins=lambda:all_presets
        fake_profiles=types.ModuleType('OpenTrace_BIM.profile_library')
        fake_profiles.builtin_profiles=lambda:[]
        funcs={'__package__':'OpenTrace_BIM','sample_collections':sample_collections,'copy':copy}
        starter=read_function('resource_collections_ui.py','builtin_starter_collections',funcs)
        with patch.dict(sys.modules,{'OpenTrace_BIM.preset_catalog':fake_preset,
                                     'OpenTrace_BIM.profile_library':fake_profiles}):
            packs=starter()
        full=next(p for p in packs if p['id']=='ot:arq:completa')
        self.assertGreaterEqual(len(full['resources']),len(all_presets['wall']))
        self.assertIn('builtin:wall:dry95',{x['id'] for x in full['resources']})
        self.assertIn('builtin:wall:struct_con_19',{x['id'] for x in full['resources']})
        small=next(p for p in packs if p['id']=='ot:arq:padrao')
        self.assertIn('builtin:wall:dry95',{x['id'] for x in small['resources']})
        self.assertIn('builtin:wall:wet_con14',{x['id'] for x in small['resources']})

    def test_checking_full_or_partial_pack_actually_populates_quick_presets(self):
        all_presets=recipes()
        records=[{'kind':'wall','id':p['id'],'name':p['name'],'folder':'Walls',
                  'data':p,'source':'opentrace:bundled'} for p in all_presets['wall']]
        pack=validate_collection({'format':'opentrace-resource-collection',
            'version':1,'id':'test:full','name':'Architecture','resources':records})
        fakeQt=types.SimpleNamespace(Checked=2,UserRole=32)
        body={'copy':copy,'Qt':fakeQt}
        tree=ast.parse((ROOT/'resource_collections_ui.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LibraryManagerDialog')
        for name in ('_resource_key','_resource_of','_leaf_items','_checked_records','selected_collections'):
            node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
            exec(compile(ast.Module(body=[node],type_ignores=[]),'resource_collections_ui.py','exec'),body)
        manager=type('Manager',(),{k:body[k] for k in ('_resource_key','_resource_of','_leaf_items','_checked_records','selected_collections')})()
        manager.packs=[pack]
        leaves=[DummyNode(record=r,checked=True) for r in pack['resources']]
        manager.tree=DummyTree([DummyNode(children=leaves,checked=True)])
        selected=manager.selected_collections()
        self.assertEqual(len(selected[0]['resources']),len(records))
        # Actual production quick-list code: full library now adds drywall.
        context={'__package__':'OpenTrace_BIM','copy':copy,'_ACTIVE_COLLECTIONS':None,
                 'builtins':lambda:all_presets,'personal_for':lambda _:[]}
        read_function('preset_catalog.py','set_active_collections',context)
        read_function('preset_catalog.py','all_for',context)
        context['set_active_collections']({'project_setup':{'resource_libraries':selected,
                                            'library_selection_mode':'curated'}})
        self.assertIn('Drywall 95 mm',[r['name'] for r in context['all_for']('wall')])
        for leaf in leaves:leaf.checked=leaf.record['id']=='builtin:wall:dry95'
        chosen=manager.selected_collections()
        self.assertEqual(len(chosen[0]['resources']),1)
        context['set_active_collections']({'project_setup':{'resource_libraries':chosen,
                                            'library_selection_mode':'curated'}})
        self.assertEqual([r['name'] for r in context['all_for']('wall')],['Drywall 95 mm'])

    def test_all_specific_wall_layers_have_real_default_textures(self):
        walls=recipes()['wall']
        self.assertGreaterEqual(len(walls),21)
        missing=[]
        for preset in walls:
            cfg=preset['config']
            if cfg.get('structure')!='composite':continue
            for layer in cfg['layers']:
                mat=layer.get('material_name')
                if not mat or mat not in _opentrace_default_catalog():
                    missing.append((preset['name'],layer['name'],mat))
                self.assertEqual(default_wall_layer_material(layer),mat)
        self.assertEqual(missing,[])
        self.assertIn('OpenTrace · Clay Brick',_opentrace_default_catalog())

    def test_composer_preview_exact_proportional_stack(self):
        f=read_function('wall_visuals.py','stack_segments',{})
        layers=[{'name':'Tile','thickness':.01},{'name':'Block','thickness':.18},
                {'name':'Render','thickness':.01}]
        bands=f(layers)
        self.assertEqual(len(bands),3)
        self.assertAlmostEqual(bands[0][1],.05)
        self.assertAlmostEqual(bands[1][1],.95)
        self.assertAlmostEqual(bands[-1][1],1.)
        source=(ROOT/'resource_preview.py').read_text()
        self.assertIn('paint_isometric_wall',source)
        self.assertIn('LayerStackPreview', (ROOT/'layer_ui.py').read_text())

if __name__=='__main__':unittest.main()
