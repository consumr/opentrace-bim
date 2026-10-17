"""Isolated regression tests; do not require Qt/Windows to run."""
import copy
import json
from pathlib import Path
import unittest
from OpenTrace_BIM.project_setup import (
    empty_template, empty_catalogue, configure_new_project,
    configure_cloned_igz, should_offer_initial_setup,
)

ROOT = Path(__file__).resolve().parents[1]

class StartupPromptTests(unittest.TestCase):
    def test_pristine_new_project_gets_one_offer(self):
        self.assertTrue(should_offer_initial_setup(None, 0, clean_untitled=True))
        self.assertTrue(should_offer_initial_setup(None, 1, clean_untitled=True))
        self.assertFalse(should_offer_initial_setup(None, 1, clean_untitled=True, already_offered=True))

    def test_objects_and_existing_projects_never_trigger_wizard(self):
        self.assertFalse(should_offer_initial_setup(None, 2, clean_untitled=False))
        self.assertFalse(should_offer_initial_setup(None, 0, has_saved_path=True, clean_untitled=True))
        self.assertFalse(should_offer_initial_setup({'project_setup': {'version':1}}, 0, clean_untitled=True))

    def test_dismissed_dialog_no_rearm_on_document_change(self):
        source=(ROOT/'layer_combinations/__init__.py').read_text(encoding='utf-8')
        self.assertIn('self._initial_prompt_offered_for_scene = self.scene',source)
        self.assertIn('if self._initial_prompt_offered_for_scene is self.scene:',source)
        self.assertIn('if self.scene is self._initial_prompt_offered_for_scene:',source)
        self.assertIn('should_offer_initial_setup(raw_bim, groups',source)

class ProjectMetadataTests(unittest.TestCase):
    FIELDS = ('name','client','location','description','author','organization','site','building')

    def test_project_info_saved_and_reopened(self):
        info = {key: key+' informado' for key in self.FIELDS}
        made = configure_new_project({}, empty_template(), empty_catalogue(),
                                     project_information=info)
        reopened=json.loads(json.dumps(made))
        self.assertEqual({k: reopened['project'][k] for k in info}, info)
        self.assertIn('project_setup',reopened)

    def test_existing_settings_preserved_and_only_requested_fields_updated(self):
        original = {'project': {'name': 'Projeto existente', 'author': 'Nome anterior'}}
        clone = configure_new_project(original, empty_template(), empty_catalogue(),
                                      project_information={'client': 'Novo cliente'})
        self.assertEqual(clone['project']['author'], 'Nome anterior')
        self.assertEqual(clone['project']['name'], 'Projeto existente')
        self.assertEqual(clone['project']['client'], 'Novo cliente')
        self.assertEqual(original['project'], {'name':'Projeto existente','author':'Nome anterior'})

    def test_invalid_project_fields_rejected(self):
        with self.assertRaises(ValueError):
            configure_new_project({}, empty_template(), empty_catalogue(),
                                  project_information={'geometry': 'não permitido'})

    def test_wizard_fields_match_authoritative_bim_record(self):
        wizard = (ROOT/'project_setup_dialog.py').read_text(encoding='utf-8')
        bim = (ROOT/'bim_ui.py').read_text(encoding='utf-8')
        for field in self.FIELDS:
            self.assertIn("('"+field+"',",wizard)
        self.assertIn("QGroupBox('Project information'",wizard)
        self.assertLess(wizard.index("QGroupBox('2 · Layer Combination Set"),
                        wizard.index("QGroupBox('Project information'"))
        self.assertLess(wizard.index("QGroupBox('Project information'"),
                        wizard.index("QGroupBox('3 · BIM schema"))

    def test_direct_abnt_button_does_not_use_broken_siclic_page(self):
        wizard = (ROOT/'project_setup_dialog.py').read_text(encoding='utf-8')
        catalogue = (ROOT/'classification_catalogue_dialog.py').read_text(encoding='utf-8')
        self.assertIn('Install ABNT · SICLIC (direct bSDD query)', wizard)
        self.assertIn('QTimer.singleShot(0, dlg._fetch_siclic)', wizard)
        self.assertNotIn('https://siclic.fau.usp.br/busca', wizard)
        self.assertNotIn('https://siclic.fau.usp.br/busca', catalogue)

if __name__ == '__main__': unittest.main()
