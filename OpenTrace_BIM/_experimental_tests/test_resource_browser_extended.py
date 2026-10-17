"""Host-free tests: portable object and category flows for experimental UI."""
import json
import sys
import types
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

from OpenTrace_BIM.resource_exchange import (export_resource, import_resource_file,
    collection_of_resources, add_to_personal_library)
from OpenTrace_BIM.resource_collections import (classify_material, material_folders,
    write_collection,read_collection,validate_collection)

def fake_preset_module(mocked):
    mod=types.ModuleType('OpenTrace_BIM.preset_catalog')
    mod.upsert_personal=mocked
    return mod


class ResourceExchangeTests(unittest.TestCase):
    def setUp(self):
        self.wall={'kind':'wall','id':'a','name':'Parede revestida','folder':'Paredes / Alvenaria',
                   'data':{'name':'Parede revestida','config':{'thickness':.15}},'source':'user'}
        self.profile={'kind':'profile','id':'b','name':'Perfil de sanca','folder':'Perfis / Sancas',
                      'data':{'loops':[{'points':[[0,0],[1,0],[1,1]],'edges':[{}, {}, {}]}]},'source':'user'}

    def test_single_export_round_trip_and_exclusive_save(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'wall.otitem'
            export_resource(self.wall,f)
            self.assertEqual(import_resource_file(f),self.wall)
            with self.assertRaises(FileExistsError):export_resource(self.wall,f)
            bad=Path(d)/'wrong.otitem';bad.write_text('{"format":"fake"}')
            with self.assertRaises(ValueError):import_resource_file(bad)

    def test_exchange_and_subcollections_keep_nested_paths(self):
        pack=collection_of_resources('Projeto',[self.wall,self.profile],folder='Arquitetura / Padrão')
        self.assertEqual(len(pack['resources']),2)
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'collection.otlib'
            write_collection(pack,file)
            loaded=read_collection(file)
            self.assertEqual(loaded,pack)
            self.assertEqual(loaded['resources'][1]['folder'],'Perfis / Sancas')

    def test_repeated_ids_regenerated_only_on_collection_export(self):
        b=dict(self.wall,name='Parede nova')
        out=collection_of_resources('Cópias',[self.wall,b])
        self.assertEqual(len(set(r['id'] for r in out['resources'])),2)

    def test_import_preset_nondestructive_unique_id(self):
        source=dict(self.wall)
        source['data']=dict(source['data'],id='builtin:wall:example',builtin=True)
        mocked=Mock(side_effect=lambda kind,item:item)
        with patch.dict(sys.modules, {'OpenTrace_BIM.preset_catalog': fake_preset_module(mocked)}):
            kind,ident=add_to_personal_library(source)
            self.assertEqual(kind,'wall')
            self.assertNotEqual(ident,'builtin:wall:example')
            self.assertFalse(mocked.call_args.args[1]['builtin'])
        self.assertEqual(source['data']['id'],'builtin:wall:example')

    def test_import_composition_as_wall(self):
        source=dict(self.wall,data={'layers':[{'name':'A','thickness':0.08},{'name':'B','thickness':0.03}]})
        mocked=Mock(side_effect=lambda kind,item:item)
        with patch.dict(sys.modules, {'OpenTrace_BIM.preset_catalog': fake_preset_module(mocked)}):
            add_to_personal_library(source)
            cfg=mocked.call_args.args[1]['config']
            self.assertAlmostEqual(cfg['thickness'],0.11)
            self.assertEqual(cfg['structure'],'composite')

    def test_broken_resource_does_not_mutate_existing(self):
        with self.assertRaises(ValueError):add_to_personal_library(dict(self.wall,data={}))

    def test_materials_are_conservative_categories(self):
        names=['Concreto aparente','Bloco cerâmico','Aço escovado','Mármore','Porcelanato',
               'Tinta verde','Floral','Ficticio sem pistas']
        expected=['Cimentos e Argamassas','Blocos ou Tijolos','Metais','Pedras',
                  'Revestimentos','Pinturas','Estampas e Tecidos','Diversos']
        self.assertEqual([classify_material(n) for n in names],expected)
        groups=material_folders(names)
        self.assertEqual(sum(map(len,groups.values())),len(names))

    def test_ui_hooks_are_native_not_ai_assistant(self):
        root=Path(__file__).resolve().parents[1]
        suite=(root/'suite_panel.py').read_text()
        ui=(root/'resource_collections_ui.py').read_text()
        setup=(root/'project_setup_dialog.py').read_text()
        self.assertNotIn('A consulta e a importação de recursos individuais estão disponíveis.',suite)
        self.assertIn('add_to_personal_library',ui)
        self.assertIn('preview_resource',ui)
        self.assertIn('Create library from selection',ui)
        self.assertIn('WARNING: CLASSIFICATION CATALOGUES',setup)
        self.assertIn('self._save_fill_favourite_btn', (root/'door_window_properties.py').read_text())

if __name__=='__main__':unittest.main()
