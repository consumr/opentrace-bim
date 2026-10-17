"""Source-only UI regression checks: keep old project and resource identities."""
import unittest
from pathlib import Path
from OpenTrace_BIM.library_display import (
    builtin_name, folder_label, library_label, resource_label,
)
from OpenTrace_BIM.resource_collections import (
    classify_material, material_folders, BUNDLED,
)

ROOT = Path(__file__).resolve().parents[1]


class LibraryLanguageRegression(unittest.TestCase):
    def test_archived_builtin_names_are_english_without_id_rewriting(self):
        old = {'id': 'builtin:column:concrete:20x20', 'kind': 'column',
               'name': 'Concreto · 20 × 20 cm', 'source': 'opentrace:bundled'}
        self.assertEqual(resource_label(old), 'Concrete · 20 × 20 cm')
        self.assertEqual(old['name'], 'Concreto · 20 × 20 cm')
        self.assertEqual(old['id'], 'builtin:column:concrete:20x20')
        self.assertEqual(builtin_name('Aço · HEB 200'), 'Steel · HEB 200')

    def test_custom_object_and_material_names_not_changed(self):
        personal = {'kind': 'wall', 'id': 'user:wall:1', 'source': 'personal',
                    'name': 'Minha parede personalizada'}
        material = {'kind': 'material', 'id': 'material:Pedra verde',
                    'source': 'host', 'name': 'Pedra verde'}
        self.assertEqual(resource_label(personal), personal['name'])
        self.assertEqual(resource_label(material), material['name'])

    def test_older_packs_and_material_categories_render_english(self):
        self.assertEqual(library_label({'id': 'ot:arq:basica', 'name': 'Arquitetura · Básica'}),
                         'Architecture · Basic')
        self.assertEqual(folder_label('Cimentos e Argamassas'), 'Cement & Mortars')
        self.assertEqual(folder_label('Estampas e Tecidos'), 'Patterns & Fabrics')
        self.assertEqual(folder_label('Diversos'), 'Miscellaneous')
        self.assertEqual(folder_label('Custom fabrics'), 'Custom fabrics')
        # Material source data is still addressed by its original name.
        self.assertEqual(classify_material('Tijolo'), 'Blocos ou Tijolos')
        self.assertIn('Tijolo', material_folders(['Tijolo'])['Blocos ou Tijolos'])

    def test_starter_pack_ids_stable(self):
        self.assertEqual([s['id'] for s in BUNDLED],
                         ['ot:arq:basica','ot:arq:padrao','ot:estrutural'])
        self.assertEqual([s['name'] for s in BUNDLED],
                         ['Architecture · Basic','Architecture · Standard',
                          'Structure · Essential'])

    def test_screenshot_ui_labels_are_english(self):
        resources = (ROOT/'resource_collections_ui.py').read_text(encoding='utf8')
        materials = (ROOT/'materials_ui.py').read_text(encoding='utf8')
        suite = (ROOT/'suite_panel.py').read_text(encoding='utf8')
        presets = (ROOT/'preset_catalog.py').read_text(encoding='utf8')
        self.assertIn('Create library from selection…', resources)
        self.assertIn('Browse full library', resources)
        self.assertIn('Categories and materials', materials)
        self.assertIn('▾ Detailed properties', suite)
        self.assertIn('f"Concrete · ', presets)
        self.assertIn('f"Steel · ', presets)
        self.assertNotIn('Propriedades detalhadas', suite)


if __name__ == '__main__':
    unittest.main()
