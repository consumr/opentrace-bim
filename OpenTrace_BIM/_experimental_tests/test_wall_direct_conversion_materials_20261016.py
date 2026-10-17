"""Isolated actual-command execution on face doubles (NOT Windows GUI tests)."""
import ast
import copy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import sys
from contextlib import contextmanager

from OpenTrace_BIM.materials import stamp_structured_materials
from OpenTrace_BIM.wall_edge_finishes import stamp_wall_edge_finishes

ROOT = Path(__file__).resolve().parents[1]
KEY = 'arquitetura_parametrica'


def recipe(scene, name):
    return ({'mat': name, 'color': {'brick': (0.5, 0.25, 0.2),
                                   'paint': (0.8, 0.4, 0.3),
                                   'steel': (0.6, 0.6, 0.7),
                                   'glass': (0.2, 0.6, 0.9)}[name]}
            if name in ('brick', 'paint', 'steel', 'glass') else None)


def wall(structure='simple'):
    layers = ([{'id':'outer','name':'outer','role':'finish','thickness':0.02,'material_name':'brick'},
               {'id':'core','name':'core','role':'core','thickness':0.1,'material_name':'steel'}]
              if structure == 'composite' else [])
    children = []
    for layer in (layers if layers else [{'material_name': 'brick'}]):
        faces = [NS(attrs={'ap_wall_side': key, 'mat': layer['material_name']})
                 for key in ('left', 'right', 'start', 'end', 'top', 'bottom')]
        mesh = NS(faces=faces, _attrs_dirty=False, _chunk_dirty=False, _mut_serial=47)
        children.append(NS(mesh=mesh))
    rec = {'kind':'wall','structure':structure,'layers':layers,
           'material_name':'brick' if structure == 'simple' else None,
           'edge_materials':{'top':'glass'}}
    group = NS(children=children,ext={KEY:rec},uid='wall-1')
    scene = NS(groups=[group],version=1,edit_group=None)
    scene.entity_selectable = lambda obj: obj is group
    scene.selection = [group]
    return group, scene


def real_command(name):
    tree = ast.parse((ROOT / 'commands.py').read_text('utf-8'))
    node = next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name == name)
    env = {'__name__':'OpenTrace_BIM.commands_integration_test',
           '__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
           'copy':copy,'KEY':KEY,'root_edit_allowed':lambda s:None,
           'WallError':ValueError,'wall_record':lambda g:g.ext.get(KEY),
           'normalize_edge_finishes': __import__('OpenTrace_BIM.wall_edge_finishes',fromlist=['normalize_edge_finishes']).normalize_edge_finishes,
           'read_wall':lambda g:g.ext[KEY],
           'stamp_structured_materials':stamp_structured_materials,
           'stamp_wall_edge_finishes':stamp_wall_edge_finishes}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
    return env[name]


class NativeCommandEffects(unittest.TestCase):
    def test_six_edge_faces_composite_apply_undo_redo(self):
        Paint = real_command('PaintWallEdgeFinishes')
        group, scene = wall('composite')
        faces = [f for c in group.children for f in c.mesh.faces]
        face_ids = tuple(map(id, faces))
        meshes = [c.mesh for c in group.children]
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=recipe):
            # First establish the correct previous edge attrs.
            stamp_wall_edge_finishes(group,scene,group.ext[KEY])
            before = [copy.deepcopy(f.attrs) for f in faces]
            command = Paint(scene,group,{'start':'paint','end':'steel',
                                         'top':'glass','bottom':'paint'})
            command.do(scene)
            for c in group.children:
                self.assertEqual([f.attrs['mat'] for f in c.mesh.faces],
                                 [c.mesh.faces[0].attrs['mat'],
                                  c.mesh.faces[1].attrs['mat'],
                                  'paint','steel','glass','paint'])
            self.assertEqual(tuple(map(id,faces)), face_ids)
            self.assertTrue(all(m._attrs_dirty for m in meshes))
            self.assertEqual([m._mut_serial for m in meshes],[47,47])
            command.undo(scene)
            self.assertEqual([f.attrs for f in faces],before)
            command.do(scene)
            self.assertEqual(group.ext[KEY]['edge_materials']['bottom'],'paint')

    def test_layer_material_real_faces_native_history_no_rebuild(self):
        Paint = real_command('PaintWallLayerMaterials')
        group, scene = wall('composite')
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=recipe):
            stamp_wall_edge_finishes(group,scene,group.ext[KEY])
            new = copy.deepcopy(group.ext[KEY]['layers'])
            new[0]['material_name']='paint'
            first = group.children[0].mesh.faces
            other = group.children[1].mesh.faces
            originals = [(f,copy.deepcopy(f.attrs)) for c in group.children for f in c.mesh.faces]
            cmd = Paint(scene,group,new)
            cmd.do(scene)
            self.assertEqual([f.attrs['mat'] for f in first],
                             ['paint','paint','paint','paint','glass','paint'])
            self.assertEqual([f.attrs['mat'] for f in other],
                             ['steel','steel','steel','steel','glass','steel'])
            self.assertEqual([id(f) for f,_ in originals],
                             [id(f) for c in group.children for f in c.mesh.faces])
            cmd.undo(scene)
            self.assertEqual([f.attrs for f,_ in originals],[attrs for _,attrs in originals])
            self.assertEqual(group.ext[KEY]['layers'][0]['material_name'],'brick')
            cmd.do(scene)
            self.assertEqual(group.ext[KEY]['layers'][0]['material_name'],'paint')
            self.assertTrue(all(c.mesh._attrs_dirty for c in group.children))
            self.assertTrue(all(c.mesh._mut_serial==47 for c in group.children))

    def test_no_partial_paint_for_unknown_layer_material(self):
        Paint = real_command('PaintWallLayerMaterials')
        group, scene = wall('composite')
        new = copy.deepcopy(group.ext[KEY]['layers'])
        new[1]['material_name'] = 'missing-material'
        before = copy.deepcopy(group.ext[KEY])
        cmd = Paint(scene,group,new)
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            with self.assertRaisesRegex(ValueError,'not found'):
                cmd.do(scene)
        self.assertEqual(group.ext[KEY],before)
        self.assertEqual(scene.version,1)

    def test_all_four_edge_faces_simple_apply_undo_redo(self):
        Paint = real_command('PaintWallEdgeFinishes')
        group, scene = wall('simple')
        with patch('OpenTrace_BIM.materials.material_face_attrs', side_effect=recipe):
            stamp_wall_edge_finishes(group,scene,group.ext[KEY])
            cmd = Paint(scene,group,{'start':'glass','end':'paint','top':'steel','bottom':'paint'})
            cmd.do(scene)
            self.assertEqual([f.attrs['mat'] for f in group.children[0].mesh.faces[2:]],
                             ['glass','paint','steel','paint'])
            cmd.undo(scene)
            self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
            cmd.do(scene)
            self.assertEqual(group.children[0].mesh.faces[2].attrs['mat'],'glass')

    def test_new_simple_and_composite_creation_stamps_independent_edges(self):
        tree=ast.parse((ROOT/'commands.py').read_text('utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='CreateWall')
        env={'__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
             'WallError':ValueError,'wall_record':lambda group:group.ext[KEY],
             'stamp_structured_materials':stamp_structured_materials,
             'stamp_wall_edge_finishes':stamp_wall_edge_finishes,
             'finalize_wall_surface_maps':lambda *a,**kw:None,
             'wall_path':lambda g:[], 'wall_path_kind':lambda g:'line'}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
        with patch.dict(sys.modules,{
                'OpenTrace_BIM.bim': NS(ensure_ifc_identity=lambda g,k:None),
                'OpenTrace_BIM.creation_properties':NS(apply_creation_properties=lambda *a,**k:None)}):
            for structure in ('simple','composite'):
                group,scene=wall(structure)
                scene.groups=[]
                scene.selection=NS(discard=lambda group:None)
                group.ext[KEY]['edge_materials']={'start':'paint','end':'steel','top':'glass','bottom':'paint'}
                cmd=env['CreateWall'](group)
                with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
                    cmd.do(scene)
                self.assertEqual(len(scene.groups),1)
                self.assertIs(scene.groups[0],group)
                for child in group.children:
                    self.assertEqual([f.attrs['mat'] for f in child.mesh.faces[2:]],
                                     ['paint','steel','glass','paint'])
                cmd.undo(scene)
                self.assertFalse(scene.groups)
                with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
                    cmd.do(scene)  # redo must preserve creation material stamping
                self.assertEqual(group.children[0].mesh.faces[2].attrs['mat'],'paint')

    def test_no_hidden_preset_dependency_in_direct_commands(self):
        source = (ROOT / 'ui.py').read_text('utf-8')
        segment = source[source.index('def structure_changed('):source.index('def layers_changed(')]
        self.assertIn('cmd = EditWall(',segment)
        self.assertIn('history.execute(cmd)',segment)
        self.assertNotIn('apply_preset(',segment)
        self.assertNotIn('self.start_drawing()',segment)
        bar = (ROOT / 'contextual_bar.py').read_text('utf-8')
        self.assertIn('lambda v: self._choose_wall_structure(v)',bar)





class GeometryCommandIntegrationTests(unittest.TestCase):
    """Execute genuine EditWall do/undo/redo against a controlled geometry stub.

    This checks command wiring and history, NOT the host's geometry kernel.
    """
    def _edit_wall(self):
        tree=ast.parse((ROOT/'commands.py').read_text('utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EditWall')
        build_calls=[]
        def build(values,**kwargs):
            build_calls.append(copy.deepcopy(values))
            parts = values['layers'] if values['structure']=='composite' else [values]
            return [NS(mesh=NS(faces=[NS(attrs={'ap_wall_side':name}) for name in
                                      ('left','right','start','end','top','bottom')],
                                _mut_serial=10,_attrs_dirty=False,_chunk_dirty=False))
                    for _part in parts]
        env={'__name__':'OpenTrace_BIM.commands_geometry_test',
             '__package__':'OpenTrace_BIM','Command':type('Command',(),{}),
             'copy':copy,'KEY':KEY,'DERIVED_KEY':'derived',
             'WallError':ValueError,'root_edit_allowed':lambda scene:None,
             'QMatrix4x4':lambda x:x,'validate':lambda data:data,
             'read_wall':lambda g:copy.deepcopy(g.ext[KEY]),
             'wall_record':lambda g:g.ext[KEY],
             'wall_path_kind':lambda g:'line',
             'wall_path':lambda g:['p0','p1'],
             'path_length':lambda path:1.0,
             'path_length_from_record':lambda rec:rec.get('length',1.0),
             'build_children':build,
             'finalize_wall_surface_maps':lambda *a,**kw:None,
             'stamp_structured_materials':stamp_structured_materials,
             'stamp_wall_edge_finishes':stamp_wall_edge_finishes,
             'edit_placement':lambda group,base:group.xform,
             'record':lambda p,path,**kw:{**p,'kind':'wall','path':copy.deepcopy(path)},
             'wall_caps':lambda g:None}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'commands.py'),'exec'),env)
        return env['EditWall'],build_calls

    def test_simple_composite_conversion_geometry_material_edges_and_history(self):
        Edit,build_calls=self._edit_wall()
        group,scene=wall('simple')
        group.xform='identity'
        original_children=list(group.children)
        group.ext[KEY].update({'length':1.0,'thickness':0.12,'height':3.0,'base':0.0,
                               'base_profile':[0,0],'top_profile':[3,3],
                               'top_xy':[[0,0],[0,0]],'path':['p0','p1']})
        layers=[{'id':'outer','role':'finish','thickness':.02,'material_name':'paint'},
                {'id':'core','role':'core','thickness':.1,'material_name':'steel'}]
        vals=copy.deepcopy(group.ext[KEY])
        vals['structure']='composite';vals['layers']=layers
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            command=Edit(scene,group,vals)
        self.assertEqual(len(build_calls),1)
        self.assertEqual(group.children,original_children)  # constructor does not commit
        mod=NS(sync_hosted_fill_placements=lambda scene,host_id:False)
        with patch.dict(sys.modules,{'OpenTrace_BIM.door_window_commands':mod}):
            command.do(scene)
            self.assertEqual(group.ext[KEY]['structure'],'composite')
            self.assertEqual(len(group.children),2)
            self.assertEqual(group.children[0].mesh.faces[0].attrs['mat'],'paint')
            self.assertEqual(group.children[1].mesh.faces[0].attrs['mat'],'steel')
            self.assertEqual([g.mesh.faces[4].attrs['mat'] for g in group.children],['glass','glass'])
            self.assertEqual(group.uid,'wall-1')
            command.undo(scene)
            self.assertEqual(group.ext[KEY]['structure'],'simple')
            self.assertIs(group.children[0],original_children[0])
            command.do(scene)
            self.assertEqual(group.ext[KEY]['structure'],'composite')
            self.assertEqual(len(group.children),2)
            # Going back to simple is also a real EditWall geometry command.
            old_composite_children=list(group.children)
            reverse=copy.deepcopy(group.ext[KEY]);reverse.update(structure='simple',layers=[],material_name='brick')
            with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
                opposite=Edit(scene,group,reverse)
            opposite.do(scene)
            self.assertEqual(group.ext[KEY]['structure'],'simple')
            self.assertEqual(len(group.children),1)
            self.assertEqual(group.children[0].mesh.faces[0].attrs['mat'],'brick')
            self.assertEqual(group.children[0].mesh.faces[4].attrs['mat'],'glass')
            opposite.undo(scene)
            self.assertEqual(group.ext[KEY]['structure'],'composite')
            self.assertIs(group.children[0],old_composite_children[0])

    def test_composite_height_regeneration_retains_layer_and_edge_finishes(self):
        Edit,build_calls=self._edit_wall()
        group,scene=wall('composite');group.xform='identity'
        group.ext[KEY].update({'length':1.0,'thickness':0.12,'height':3.0,'base':0.0,
                               'base_profile':[0,0],'top_profile':[3,3],
                               'top_xy':[[0,0],[0,0]],'path':['p0','p1']})
        vals=copy.deepcopy(group.ext[KEY]);vals['height']=3.8
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            edit=Edit(scene,group,vals)
        self.assertEqual(build_calls[-1]['top_profile'],[3.8,3.8])
        with patch.dict(sys.modules,{'OpenTrace_BIM.door_window_commands':NS(sync_hosted_fill_placements=lambda *a,**k:False)}):
            edit.do(scene)
            self.assertEqual(group.ext[KEY]['height'],3.8)
            self.assertEqual([c.mesh.faces[0].attrs['mat'] for c in group.children],['brick','steel'])
            self.assertEqual([c.mesh.faces[4].attrs['mat'] for c in group.children],['glass','glass'])
            edit.undo(scene)
            self.assertEqual(group.ext[KEY]['height'],3.0)
            edit.do(scene)
            self.assertEqual(group.ext[KEY]['height'],3.8)


class DispatcherIntegrationTests(unittest.TestCase):
    """Run the production UI method bodies through simulated signal dispatch."""
    def _ui_method(self, method, extra):
        tree = ast.parse((ROOT/'ui.py').read_text('utf-8'))
        controller = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WallController')
        node = next(n for n in controller.body if isinstance(n,ast.FunctionDef) and n.name==method)
        env = {'__name__':'OpenTrace_BIM.ui_event_test','copy':copy,
               'selected_walls':lambda scene:list(scene.selection),
               'read_wall':lambda g:g.ext[KEY],
               'WallError':ValueError}
        env.update(extra)
        exec(compile(ast.Module(body=[node], type_ignores=[]),str(ROOT/'ui.py'),'exec'),env)
        return env[method]

    def _controller(self, group, scene):
        executed=[]
        class History:
            last_error=None
            def execute(self,cmd):
                cmd.do(scene)
                executed.append(cmd)
        class Viewport:
            history=History()
            notices=0
            def notify_scene_changed(self):self.notices+=1
        vp=Viewport()
        app=NS(scene=scene,viewport=vp)
        ctrl=NS(app=app, _loading=False,target=None,target_scene=None,
                defaults={'edge_materials':{}},_state_key=None,_loaded_key=None,
                refresh=lambda:None,message=lambda *a,**k:None)
        return ctrl,executed

    def test_edge_selector_stages_then_apply_executes_native_faces_command(self):
        group,scene=wall('composite')
        c,executed=self._controller(group,scene)
        c.edge_apply_button=NS(setEnabled=lambda state: setattr(c,'apply_enabled',state))
        c._selected_edge_finishes=lambda:{'start':'paint','end':'steel',
                                             'top':'glass','bottom':'paint'}
        c.target=None  # selection is resolved live, not via stale cached target
        stage=self._ui_method('edge_finishes_changed',{})
        commit=self._ui_method('apply_edge_finishes',
            {'PaintWallEdgeFinishes':real_command('PaintWallEdgeFinishes'),
             'log':NS(exception=lambda *a:None)})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            stage(c)
            self.assertEqual(executed,[])
            self.assertEqual(scene.version,1)
            self.assertTrue(c.apply_enabled)
            self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
            commit(c)
        self.assertEqual(len(executed),1)
        self.assertEqual(scene.version,2)
        self.assertEqual(group.children[0].mesh.faces[2].attrs['mat'],'paint')
        self.assertEqual(group.children[1].mesh.faces[3].attrs['mat'],'steel')
        self.assertEqual(c.app.viewport.notices,1)
        self.assertFalse(c.apply_enabled)
        executed[0].undo(scene)
        self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            executed[0].do(scene)
        self.assertEqual(group.ext[KEY]['edge_materials']['start'],'paint')

    def test_edge_apply_on_simple_wall_and_undo(self):
        group,scene=wall('simple')
        c,executed=self._controller(group,scene)
        c.edge_apply_button=NS(setEnabled=lambda flag: setattr(c,'enabled',flag))
        c._selected_edge_finishes=lambda:{'start':'paint','bottom':'steel'}
        stage=self._ui_method('edge_finishes_changed',{})
        apply=self._ui_method('apply_edge_finishes',
            {'PaintWallEdgeFinishes':real_command('PaintWallEdgeFinishes'),
             'log':NS(exception=lambda *a:None)})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            stage(c)
            self.assertEqual(scene.version,1)
            self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
            apply(c)
        self.assertEqual(scene.version,2)
        self.assertEqual(group.children[0].mesh.faces[2].attrs['mat'],'paint')
        self.assertEqual(group.children[0].mesh.faces[5].attrs['mat'],'steel')
        self.assertEqual(group.ext[KEY]['edge_materials'],{'start':'paint','bottom':'steel'})
        executed[0].undo(scene)
        self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})

    def test_edge_pending_cannot_paint_a_different_selected_wall(self):
        group,scene=wall('composite')
        c,executed=self._controller(group,scene)
        c.edge_apply_button=NS(setEnabled=lambda flag:None)
        c._selected_edge_finishes=lambda:{'end':'paint'}
        errors=[]
        c.message=lambda text,**kwargs:errors.append((text,kwargs))
        stage=self._ui_method('edge_finishes_changed',{})
        apply=self._ui_method('apply_edge_finishes',
            {'PaintWallEdgeFinishes':real_command('PaintWallEdgeFinishes'),
             'log':NS(exception=lambda *a:None)})
        stage(c)
        other=NS(ext={KEY:{'kind':'wall','edge_materials':{}}},uid='another-wall')
        scene.selection=[other]
        apply(c)
        self.assertEqual(executed,[])
        self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
        self.assertIsNone(c._edge_pending)
        self.assertTrue(any('selection changed' in text.lower() for text,_ in errors))

    def test_creation_edge_apply_only_updates_next_wall_defaults(self):
        group,scene=wall('simple')
        scene.selection=[]
        c,executed=self._controller(group,scene)
        c.edge_apply_button=NS(setEnabled=lambda flag:setattr(c,'enabled',flag))
        c.app.viewport.update=lambda:None
        c._selected_edge_finishes=lambda:{'start':'paint'}
        stage=self._ui_method('edge_finishes_changed',{})
        apply=self._ui_method('apply_edge_finishes',
            {'PaintWallEdgeFinishes':real_command('PaintWallEdgeFinishes'),
             'log':NS(exception=lambda *a:None)})
        stage(c)
        self.assertEqual(c.defaults['edge_materials'],{})
        self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
        apply(c)
        self.assertEqual(c.defaults['edge_materials'],{'start':'paint'})
        self.assertEqual(group.ext[KEY]['edge_materials'],{'top':'glass'})
        self.assertFalse(c.enabled)
        self.assertEqual(executed,[])

    def test_edge_selector_same_material_never_enables_apply(self):
        group,scene=wall('simple')
        c,executed=self._controller(group,scene)
        c.edge_apply_button=NS(setEnabled=lambda flag:setattr(c,'enabled',flag))
        c._selected_edge_finishes=lambda:{'top':'glass'}
        stage=self._ui_method('edge_finishes_changed',{})
        stage(c)
        self.assertIsNone(c._edge_pending)
        self.assertFalse(c.enabled)
        self.assertEqual(executed,[])

    def test_simple_material_dispatch_executes_paint_with_stale_target(self):
        group,scene=wall('simple')
        c,executed=self._controller(group,scene)
        c.material=NS(currentData=lambda:'paint')
        handler=self._ui_method('wall_material_changed',
            {'PaintWallBodyMaterial':real_command('PaintWallBodyMaterial')})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe):
            handler(c)
        self.assertEqual(len(executed),1)
        self.assertEqual(group.ext[KEY]['material_name'],'paint')
        self.assertEqual(group.children[0].mesh.faces[0].attrs['mat'],'paint')
        self.assertEqual(c.app.viewport.notices,1)
        executed[0].undo(scene)
        self.assertEqual(group.ext[KEY]['material_name'],'brick')

    def test_composite_button_dispatches_real_conversion_and_undo(self):
        Edit,_calls=GeometryCommandIntegrationTests()._edit_wall()
        group,scene=wall('simple')
        group.xform='identity'
        group.ext[KEY].update({'length':1.0,'thickness':0.12,'height':3.0,'base':0.0,
                               'base_profile':[0,0],'top_profile':[3,3],
                               'top_xy':[[0,0],[0,0]],'path':['p0','p1']})
        c,executed=self._controller(group,scene)
        c.structure=NS(currentData=lambda:'composite')
        c._update_structure_ui=lambda:None
        handler=self._ui_method('structure_changed',{'EditWall':Edit})
        with patch('OpenTrace_BIM.materials.material_face_attrs',side_effect=recipe),\
             patch.dict(sys.modules,{'OpenTrace_BIM.door_window_commands':NS(sync_hosted_fill_placements=lambda *a,**k:False)}):
            handler(c)
            self.assertEqual(len(executed),1)
            self.assertEqual(group.ext[KEY]['structure'],'composite')
            self.assertEqual(len(group.children),1)  # one real core layer
            self.assertEqual(group.children[0].mesh.faces[0].attrs['mat'],'brick')
            self.assertEqual(group.children[0].mesh.faces[4].attrs['mat'],'glass')
            self.assertEqual(c.app.viewport.notices,1)
            executed[0].undo(scene)
            self.assertEqual(group.ext[KEY]['structure'],'simple')
            executed[0].do(scene)
            self.assertEqual(group.ext[KEY]['structure'],'composite')

    def test_no_selection_changes_next_wall_not_stale_existing_group(self):
        group,scene=wall('simple')
        scene.selection=[]
        c,executed=self._controller(group,scene)
        c.target=group
        c.material=NS(currentData=lambda:'paint')
        c.app.viewport.update=lambda:None
        handler=self._ui_method('wall_material_changed',
            {'PaintWallBodyMaterial':real_command('PaintWallBodyMaterial')})
        handler(c)
        self.assertEqual(executed,[])
        self.assertEqual(c.defaults['material_name'],'paint')
        self.assertEqual(group.ext[KEY]['material_name'],'brick')


if __name__=='__main__':
    unittest.main()
