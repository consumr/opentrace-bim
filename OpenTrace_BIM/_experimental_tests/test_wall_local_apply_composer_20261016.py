"""Experimental interface wiring contracts; no IngeTrazo/Qt runtime here."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


def method(module, classname, name, globals):
    tree=ast.parse((ROOT/module).read_text('utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==classname)
    func=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[func], type_ignores=[]),str(ROOT/module),'exec'),globals)
    return globals[name]


class WallEdgeApplyAndComposerContracts(unittest.TestCase):
    def test_apply_below_all_four_side_finish_pickers(self):
        text=(ROOT/'ui.py').read_text('utf-8')
        section=text[text.index('self.edge_finish_fields = {}'):text.index('self.structure=QComboBox()')]
        self.assertIn('("start", "Start end")',section)
        self.assertIn('("end", "Finish end")',section)
        self.assertIn('("top", "Wall top")',section)
        self.assertIn('("bottom", "Wall bottom")',section)
        self.assertLess(section.index('self.edge_finish_fields[face] = choice'),
                        section.index('edge_form.addRow(self.edge_apply_button)'))
        self.assertIn('clicked.connect(self.apply_edge_finishes)',section)
        self.assertEqual(section.count('QPushButton("Apply"'),1)

    def test_composer_uses_existing_editor_and_has_new_title(self):
        source=(ROOT/'layer_ui.py').read_text('utf-8')
        self.assertIn('dlg.setWindowTitle("Material Composer")',source)
        self.assertIn('ed = LayerEditor(',source)
        bar=(ROOT/'contextual_bar.py').read_text('utf-8')
        self.assertIn('lambda v: self._choose_wall_structure(v)',bar)
        self.assertIn('(("Simples", "simple"), ("Material Composer", "composite"))',bar)
        self.assertIn('self.wall.open_material_composer()',bar)

    def test_click_composite_opens_even_if_already_checked(self):
        calls=[]
        parent=NS(scene=NS(groups=[],selection=[]))
        wall=NS(structure=NS(currentData=lambda:'composite'),
                open_material_composer=lambda:calls.append('open'),
                _state_key=None,_loaded_key=None)
        bar=NS(wall=wall,app=parent,
               _select_combo=lambda w,k:calls.append(('select',k)))
        fn=method('contextual_bar.py','ContextualBar','_choose_wall_structure',
                  {'__name__':'OpenTrace_BIM.context_bar_stub',
                   '__package__':'OpenTrace_BIM'})
        # Inject just the imported selection helper; the actual callback body
        # executes (Qt itself is unavailable in this Linux environment).
        with patch.dict(sys.modules,{'OpenTrace_BIM.ui':NS(selected_walls=lambda scene:[])}):
            fn(bar, 'composite')
        self.assertEqual(calls,[('select','composite'),'open'])
        calls.clear()
        # Direct controller command still checks actual type and schedules
        # live-linked floating window, rather than rebuilding an editor.
        scheduled=[]
        selected=NS(ext={'structure':'composite'})
        controller=NS(structure=NS(currentData=lambda:'composite'),
                      app=NS(scene=NS(selection=[selected])),
                      layer_editor=NS(_open_floating_editor=lambda:calls.append('dialog')))
        open_composer=method('ui.py','WallController','open_material_composer',
            {'selected_walls':lambda s:s.selection,'read_wall':lambda g:g.ext,
             'QTimer':NS(singleShot=lambda ms,f:scheduled.append(f))})
        open_composer(controller)
        self.assertEqual(len(scheduled),1)
        scheduled[0]()
        self.assertEqual(calls,['dialog'])

    def test_failed_composite_conversion_does_not_open_editor(self):
        scheduled=[]
        selected=NS(ext={'structure':'simple'})
        ctrl=NS(structure=NS(currentData=lambda:'composite'),
                app=NS(scene=NS(selection=[selected])),
                layer_editor=NS(_open_floating_editor=lambda:None))
        open_composer=method('ui.py','WallController','open_material_composer',
            {'selected_walls':lambda s:s.selection,'read_wall':lambda g:g.ext,
             'QTimer':NS(singleShot=lambda ms,f:scheduled.append(f))})
        open_composer(ctrl)
        self.assertEqual(scheduled,[])

    def test_other_edits_do_not_commit_unapplied_paints(self):
        source=(ROOT/'ui.py').read_text('utf-8')
        code=source[source.index('def values(self):'):source.index('def _selected_edge_finishes')]
        self.assertIn('read_wall(self.target).get("edge_materials")',code)
        self.assertIn('self.defaults.get("edge_materials")',code)
        self.assertNotIn('out["edge_materials"] = self._selected_edge_finishes()',code)

if __name__=='__main__':unittest.main()
