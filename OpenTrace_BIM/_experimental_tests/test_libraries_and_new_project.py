"""Host-free regression: portable collections, templates and fast creation indexes."""
import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from OpenTrace_BIM.resource_collections import (
    make_collection, validate_collection, search_resources, material_folders,
    sample_collections, write_collection, read_collection,
)
from OpenTrace_BIM.template_bundle import (
    inspect_template, extract_template, save_complete_template,
)
from OpenTrace_BIM.catalogue_migration import automatic_for_class_multi
from OpenTrace_BIM.project_setup import configure_new_project, empty_template, empty_catalogue

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return make_collection('Portas e paredes', [
        {'id':'a1','kind':'wall','name':'Parede rebocada',
         'folder':'Paredes / Alvenaria','data':{'config':{'thickness':0.14}}},
        {'id':'b1','kind':'profile','name':'Sanca simples',
         'folder':'Perfis complexos / Forro','data':{'loops':[[1,2]]}},
    ],ident='test:1',folder='Arquitetura / Padrão')


class CollectionTests(unittest.TestCase):
    def test_folder_and_search(self):
        a=sample()
        self.assertEqual(len(search_resources([a],'alvenaria')),1)
        self.assertEqual(search_resources([a], 'rebocada')[0][1]['kind'],'wall')
        self.assertEqual(len(search_resources([a],kind='profile')),1)

    def test_reject_path_traversal_duplicate_unknown(self):
        a=sample()
        for change in (lambda x:x['resources'][0].update(folder='../outside'),
                       lambda x:x['resources'][1].update(id='a1',kind='wall'),
                       lambda x:x['resources'][1].update(kind='cad')):
            bad=copy.deepcopy(a);change(bad)
            with self.assertRaises(ValueError):validate_collection(bad)

    def test_exclusive_file_import_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'samples.otlib'
            original=sample()
            write_collection(original,path)
            self.assertEqual(read_collection(path),original)
            with self.assertRaises(ValueError if False else FileExistsError):
                write_collection(original,path)

    def test_packs_have_real_recipes(self):
        presets={'wall':[{'id':'p1','name':'Concreta','config':{'thickness':0.1}}],
                 'slab':[{'id':'s1','name':'Laje','config':{'thickness':0.15}}]}
        packs=sample_collections(presets,[])
        self.assertEqual(len(packs),3)
        self.assertEqual(len(packs[0]['resources']),2)
        self.assertEqual(packs[0]['resources'][0]['data']['config']['thickness'],0.1)

    def test_material_folders(self):
        f=material_folders(['RAL 1000','Tijolo','Local'],catalog={
            'Tijolo':{'texture':{'path':'resources/textures/library/brick/red.png'}},
        })
        self.assertIn('RAL 1000',f['Pinturas / Cores RAL'])
        self.assertIn('Tijolo',f['Blocos ou Tijolos'])
        self.assertIn('Local',f['Diversos'])

    def test_setup_embeds_selected_library(self):
        p=configure_new_project({},empty_template(),empty_catalogue(),
                                resource_libraries=[sample()])
        reloaded=json.loads(json.dumps(p))
        self.assertEqual(reloaded['project_setup']['resource_libraries'][0]['resources'][1]['name'], 'Sanca simples')


class CompleteTemplateTests(unittest.TestCase):
    def test_pack_scene_plus_resources_independent(self):
        class Scene: pass
        calls=[]
        def save_scene(scene, path):
            calls.append(scene)
            Path(path).write_bytes(b'IGZ TEST SCENE AND MATERIALS')
        core=types.ModuleType('core')
        core.igz_format=types.SimpleNamespace(save_scene=save_scene)
        app=types.SimpleNamespace(scene=Scene())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules,{'core':core}):
            bundle=Path(tmp)/'template.ottemplate'
            original_path=Path(tmp)/'my-current-project.igz'
            original_path.write_bytes(b'ORIGINAL')
            save_complete_template(app,bundle,'Meu Modelo',[sample()])
            manifest, resources=inspect_template(bundle)
            self.assertEqual(manifest['name'],'Meu Modelo')
            self.assertEqual(resources[0]['resources'][1]['name'],'Sanca simples')
            self.assertEqual(original_path.read_bytes(),b'ORIGINAL')
            copydest=Path(tmp)/'new-project.igz'
            extract_template(bundle,copydest)
            self.assertEqual(copydest.read_bytes(),b'IGZ TEST SCENE AND MATERIALS')
            with self.assertRaises(ValueError):extract_template(bundle,copydest)
            self.assertEqual(copydest.read_bytes(),b'IGZ TEST SCENE AND MATERIALS')
            with self.assertRaises(ValueError):save_complete_template(app,bundle,'Meu Modelo',[sample()])
            self.assertEqual(len(calls),1)


class CacheAndUIContracts(unittest.TestCase):
    def test_creation_index_reused_without_rescanning(self):
        cats={f'x{x}': {'system':'Uniclass','code':str(x),
                        'ifc_classes':['IfcSlab'] if x==23 else []}
              for x in range(7000)}
        catalogue={'classifications':cats}
        first=automatic_for_class_multi(catalogue,'IfcSlab')
        self.assertEqual(len(first),1)
        self.assertIn('_opentrace_creation_index',catalogue)
        index=catalogue['_opentrace_creation_index']
        second=automatic_for_class_multi(catalogue,'IfcSlab')
        self.assertIs(index,catalogue['_opentrace_creation_index'])
        self.assertEqual(first,second)
        second[0]['code']='tampered'
        self.assertEqual(automatic_for_class_multi(catalogue,'IfcSlab')[0]['code'],'23')

    def test_host_ctrl_n_and_manual_button_present(self):
        layers=(ROOT/'layer_combinations/__init__.py').read_text(encoding='utf8')
        wizard=(ROOT/'project_setup_dialog.py').read_text(encoding='utf8')
        suite=(ROOT/'suite_panel.py').read_text(encoding='utf8')
        self.assertIn('self._connect_native_new_action()',layers)
        self.assertIn('self.app.scene._opentrace_native_new_document = True',layers)
        self.assertIn('self.project_setup_button.setEnabled(True)',suite)
        self.assertIn("getattr(win, '_on_new', None)",wizard)
        self.assertIn("Save a complete template of this project",wizard)
        self.assertIn("Use complete .ottemplate",wizard)

    def test_material_search_picker_used_by_tools(self):
        for tool in ('layer_ui.py','ui.py','slab_ui.py','beam_ui.py','column_ui.py'):
            self.assertIn('MaterialPickerCombo', (ROOT/tool).read_text(encoding='utf8'))

if __name__=='__main__': unittest.main()
