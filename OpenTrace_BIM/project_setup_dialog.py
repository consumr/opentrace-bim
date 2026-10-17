# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental single first-run configuration (layers + BIM + resources).

The host opens this once for a new, unsaved document; never for an .igz reopen.
The layer-combinations service keeps ownership of its separate data namespace.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)
from .i18n import t
from .project_setup import (
    empty_template, empty_catalogue, read_template, configure_new_project,
    can_configure_new_document, copy_igz_template, configure_cloned_igz,
    file_sha256, merge_classification_catalogues,
)
from .classification_equivalences import read_crosswalk
from .official_classification_import import import_publisher_catalogue
from .resource_collections_ui import available_collections, LibraryManagerDialog
from .resource_collections import validate_collection, capture_personal_resources
from .template_bundle import save_complete_template, inspect_template, extract_template

SYSTEMS = ['Uniclass 2015', 'OmniClass', 'ABNT NBR 15965', 'MasterFormat', 'UniFormat', 'CoClass', 'Other…']
PROJECT_FIELDS = (
    ('name', 'Project'), ('client', 'Client'),
    ('location', 'Localização'), ('description', 'Descrição'),
    ('author', 'Author'), ('organization', 'Escritório / Organização'),
    ('site', 'Terreno IFC'), ('building', 'Edifício IFC'),
)


class NewProjectSetupDialog(QDialog):
    def __init__(self, app, bim, parent=None, *, layer_controller=None, startup=False):
        super().__init__(parent)
        self.app, self.bim = app, bim
        self.layer_controller = layer_controller
        self.startup = bool(startup)
        self.applied_setup = False
        self.template = empty_template()
        self.template_igz = None
        self.template_bundle = None
        self.template_bundle_resources = []
        self.available_libraries = available_collections()
        self.catalogues = []
        self.crosswalks = []
        self.setWindowTitle('EXPERIMENTAL · Initial project setup')
        self.resize(660, 720)
        if startup:
            self.setModal(False)
            self.setWindowModality(Qt.NonModal)

        outer = QVBoxLayout(self)
        header = QLabel('<b>New OpenTrace BIM project</b> — independent choices<br>'
                        'Template, layer combination set, IFC schema, catalogues and libraries '
                        'will be saved with this project and not requested again on reopen.')
        header.setWordWrap(True)
        outer.addWidget(header)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget(scroll)
        root = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        project_box = QGroupBox('1 · Project template', content)
        project_form = QFormLayout(project_box)
        self.template_choice = QComboBox(project_box)
        self.template_choice.addItem('Default OpenTrace (empty project)', 'builtin')
        self.template_choice.addItem('Use my .igz project as a complete template…', 'igz')
        self.template_choice.addItem('Use settings template (.json)…', 'json')
        self.template_choice.addItem('Use complete .ottemplate (scene + resources)…', 'bundle')
        self.template_choice.currentIndexChanged.connect(self._template_changed)
        project_form.addRow('Template', self.template_choice)
        self.template_info = QLabel('No original files will be modified.')
        self.template_info.setWordWrap(True)
        project_form.addRow('', self.template_info)
        root.addWidget(project_box)

        layer_box = QGroupBox('2 · Layer Combination Set', content)
        layer_form = QFormLayout(layer_box)
        self.layer_choice = QComboBox(layer_box)
        self.layer_choice.addItem('Keep existing layers / start empty', None)
        if layer_controller is not None:
            from .layer_combinations import builtin_templates
            for name in builtin_templates():
                self.layer_choice.addItem(name + ' · included', ('builtin', name))
            for name in sorted(layer_controller.personal_templates(), key=str.casefold):
                self.layer_choice.addItem(name + ' · personal', ('personal', name))
            # Default first-run reproduces previous Layer Combinations chooser.
            if self.layer_choice.count() > 1:
                self.layer_choice.setCurrentIndex(1)
        layer_form.addRow('Layer set', self.layer_choice)
        self.layer_info = QLabel('Includes individual layers, folders, visibility and combinations.')
        self.layer_info.setWordWrap(True)
        layer_form.addRow('', self.layer_info)
        root.addWidget(layer_box)

        # Same authoritative project fields as BIM / Informações do Projeto.
        # No new storage namespace: these write to document['project'].
        info_box = QGroupBox('Project information', content)
        info_layout = QVBoxLayout(info_box)
        self.project_fields = {}
        current = (self.bim.data.get('project') or {}) if isinstance(self.bim.data, dict) else {}
        for section_name, keys in (
            ('Identification', ('name', 'client', 'location', 'description')),
            ('Responsible parties', ('author', 'organization')),
            ('Project structure', ('site', 'building')),
        ):
            heading = QLabel('<b>' + t(section_name) + '</b>', info_box)
            info_layout.addWidget(heading)
            form = QFormLayout()
            for key in keys:
                caption = dict(PROJECT_FIELDS)[key]
                editor = QLineEdit(info_box)
                editor.setMaxLength(500)
                editor.setText(str(current.get(key) or ''))
                self.project_fields[key] = editor
                form.addRow(t(caption), editor)
            info_layout.addLayout(form)
        try:
            from .levels import available_levels
            names = [level['name'] for level in available_levels(self.app)]
            level_status = ', '.join(names) if names else 'nenhum nível cadastrado'
        except Exception:
            level_status = 'dados indisponíveis'
        info_layout.addWidget(QLabel('Storeys linked to levels: ' + t(level_status), info_box))
        root.addWidget(info_box)

        bim_box = QGroupBox('3 · BIM schema and classification', content)
        bim_form = QFormLayout(bim_box)
        self.schema_choice = QComboBox(bim_box)
        self.schema_choice.addItem('IFC4 · stable', 'IFC4')
        self.schema_choice.addItem('IFC4.3 ADD2 · experimental; validation required', 'IFC4X3_ADD2')
        bim_form.addRow('IFC version', self.schema_choice)
        self.catalogue_list = QListWidget(bim_box)
        self.catalogue_list.setMaximumHeight(100)
        bim_form.addRow('Selected catalogues', self.catalogue_list)
        cat_buttons = QHBoxLayout()
        add = QPushButton('Add official/external catalogue…', bim_box)
        add.clicked.connect(self._add_catalogue)
        rem = QPushButton('Remove selected', bim_box)
        rem.clicked.connect(self._remove_catalogue)
        cat_buttons.addWidget(add)
        cat_buttons.addWidget(rem)
        bim_form.addRow('', cat_buttons)
        ready = QPushButton('Install Uniclass or ABNT / manage catalogues…', bim_box)
        ready.clicked.connect(self._open_catalogue_sources)
        bim_form.addRow('', ready)
        abnt = QPushButton('Install ABNT · SICLIC (direct bSDD query)…', bim_box)
        abnt.setToolTip('Queries the demo dictionary on bSDD. Does not open SICLIC or claim to be the full ABNT standard.')
        abnt.clicked.connect(self._open_abnt_sources)
        bim_form.addRow('', abnt)
        self.catalogue_info = QLabel('IFC defines entities and properties. Uniclass, OmniClass '
                                     'and ABNT are independent classification systems, not substitutes for IFC4.')
        self.catalogue_info.setWordWrap(True)
        bim_form.addRow('', self.catalogue_info)
        performance_warning = QLabel(
            '<b>WARNING: CLASSIFICATION CATALOGUES AND CROSSWALKS MAY SLOW DOWN '
            'OBJECT CREATION.</b>', bim_box)
        performance_warning.setWordWrap(True)
        performance_warning.setStyleSheet('color: #e8a45b; font-weight: 700;')
        bim_form.addRow('', performance_warning)
        performance_details = QLabel(
            'When an element is created, OpenTrace assigns its IFC entity and checks '
            'the codes in the selected tables. Lookup is optimized and '
            'reuses in-memory indices, but extra classification work and metadata '
            'storage can increase the time before the object appears in the viewport.', bim_box)
        performance_details.setWordWrap(True)
        performance_details.setStyleSheet('font-size: 10px;')
        bim_form.addRow('', performance_details)
        sources = QLabel(
            'Official sources: <a href="https://uniclass.thenbs.com/download">Uniclass · NBS</a>'
            '  ·  <a href="https://www.csiresources.org/standards/omniclass/standards-omniclass-about">OmniClass · CSI</a>'
            '  ·  <a href="https://search.bsdd.buildingsmart.org/">Dicionários · buildingSMART</a>', bim_box)
        sources.setOpenExternalLinks(True)
        sources.setWordWrap(True)
        bim_form.addRow('Get tables', sources)
        self.primary_choice = QComboBox(bim_box)
        self.primary_choice.addItem('None · manually classify when needed', '')
        bim_form.addRow('Primary catalogue', self.primary_choice)
        self.map_choice = QComboBox(bim_box)
        self.map_choice.addItem('No verified external equivalences', 'none')
        self.map_choice.addItem('Load equivalence catalogue (CSV/JSON)…', 'file')
        self.map_choice.currentIndexChanged.connect(self._equivalences_changed)
        bim_form.addRow('Equivalences', self.map_choice)
        self.map_info = QLabel('Code crosswalks are imported with their source and edition. '
                               'Table-level comparisons do not authorize automatic code conversions.')
        self.map_info.setWordWrap(True)
        bim_form.addRow('', self.map_info)
        author = QPushButton('Record a manual crosswalk with evidence…', bim_box)
        author.clicked.connect(self._author_crosswalk)
        bim_form.addRow('', author)
        families = QPushButton('View table-level correspondences (not codes)…', bim_box)
        families.clicked.connect(self._show_table_families)
        bim_form.addRow('', families)
        root.addWidget(bim_box)

        libs_box = QGroupBox('4 · Libraries and sublibraries', content)
        libs_layout = QVBoxLayout(libs_box)
        libs_help = QLabel('The full collection remains searchable. Only selected libraries '
                           'are loaded into the new project; personal objects can be '
                           'imported individually through the library manager.')
        libs_help.setWordWrap(True)
        libs_layout.addWidget(libs_help)
        self.libraries_list = QListWidget(libs_box)
        self.libraries_list.setMaximumHeight(125)
        libs_layout.addWidget(self.libraries_list)
        self._refresh_resource_libraries()
        manage = QPushButton('Manage libraries, folders and objects…', libs_box)
        manage.clicked.connect(self._manage_resource_libraries)
        libs_layout.addWidget(manage)
        root.addWidget(libs_box)

        save = QPushButton('Save a complete template of this project…', content)
        save.setToolTip('Exports the .igz scene, layers, document materials and selected presets '
                        'to a portable .ottemplate file. '
                        'Does not change the current project.')
        save.clicked.connect(self._save_current_template)
        root.addWidget(save)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.button(QDialogButtonBox.Ok).setText('Create project')
        buttons.button(QDialogButtonBox.Cancel).setText('Not now')
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _template_changed(self, index):
        choice = self.template_choice.itemData(index)
        if choice == 'builtin':
            self.template_igz = None
            self.template_bundle = None
            self.template_bundle_resources = []
            self.template = empty_template()
            self.template_info.setText('New project with no imported geometry.')
            if self.layer_choice.count() > 1:
                self.layer_choice.setCurrentIndex(1)
            return
        if choice == 'bundle':
            name, _ = QFileDialog.getOpenFileName(self, 'Template OpenTrace completo',
                                  '', 'Templates OpenTrace (*.ottemplate)')
            if not name:
                self.template_choice.setCurrentIndex(0)
                return
            try:
                manifest, collections = inspect_template(name)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                QMessageBox.warning(self, 'Template', str(exc))
                self.template_choice.setCurrentIndex(0)
                return
            self.template_bundle = Path(name)
            self.template_igz = Path(name)
            self.template = empty_template()
            self.template_bundle_resources = collections
            ids = {p['id'] for p in self.available_libraries}
            self.available_libraries.extend(p for p in collections if p['id'] not in ids)
            self._refresh_resource_libraries()
            self.layer_choice.setCurrentIndex(0)
            for field in self.project_fields.values(): field.clear()
            self.template_info.setText('Template completo: '+manifest['name']+' · cena e recursos portáteis')
            return
        if choice == 'igz':
            self.template_bundle = None
            self.template_bundle_resources = []
            name, _ = QFileDialog.getOpenFileName(self, 'Template .igz', '', 'Projetos IngeTrazo (*.igz)')
            if not name:
                self.template_choice.setCurrentIndex(0)
                return
            source = Path(name)
            if not source.is_file() or source.suffix.lower() != '.igz':
                QMessageBox.warning(self, 'Template', 'Invalid .igz file.')
                self.template_choice.setCurrentIndex(0)
                return
            self.template_igz = source
            self.template = empty_template()
            self.template_info.setText(source.name + ' · cria cópia independente; original intocado')
            self.layer_choice.setCurrentIndex(0)  # Preserve the project's layers unless overridden.
            # A copied .igz has its own project metadata: don't overwrite it
            # with defaults from the currently empty document.
            for field in self.project_fields.values():
                field.clear()
            return
        name, _ = QFileDialog.getOpenFileName(self, 'Template JSON', '', 'OpenTrace JSON (*.json)')
        if not name:
            self.template_choice.setCurrentIndex(0)
            return
        try:
            self.template = read_template(name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Invalid template', str(exc))
            self.template_choice.setCurrentIndex(0)
            return
        self.template_igz = None
        self.template_bundle = None
        self.template_bundle_resources = []
        # Show the selected JSON template's project fields, so the wizard
        # does not silently replace them with the blank-document defaults.
        template_project = self.template.get('settings', {}).get('project', {})
        if isinstance(template_project, dict):
            for key, editor in self.project_fields.items():
                if key in template_project:
                    editor.setText(str(template_project[key] or ''))
        self.template_info.setText(f"{self.template['name']} · configurações, sem geometria")

    def _open_catalogue_sources(self):
        self._catalogue_sources_dialog(start_abnt=False)

    def _open_abnt_sources(self):
        self._catalogue_sources_dialog(start_abnt=True)

    def _catalogue_sources_dialog(self, *, start_abnt=False):
        from .classification_catalogue_dialog import CatalogueSourcesDialog
        dlg = CatalogueSourcesDialog(self.catalogues, self)
        if start_abnt:
            # Explicit user action: this will ask confirmation and start the
            # actual bSDD API request, not open a broken browser link.
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, dlg._fetch_siclic)
        if dlg.exec():
            self.catalogues = dlg.catalogues
            self.catalogue_list.clear()
            for cat in self.catalogues:
                item = QListWidgetItem(
                    f"{cat.get('system', '')} · {len(cat['classifications'])} códigos · {cat.get('edition') or cat.get('source_file') or ''}")
                item.setData(Qt.UserRole, cat['id'])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.catalogue_list.addItem(item)
            self._refresh_primary()

    def _add_catalogue(self):
        system, ok = QInputDialog.getItem(self, 'Add classification',
                                           'Classification system:', SYSTEMS, 0, False)
        if not ok:
            return
        if system == 'Other…':
            system, ok = QInputDialog.getText(self, 'New classification system', 'Identificador do sistema:')
            if not ok or not str(system).strip():
                return
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Selecionar tabelas do editor original', '',
            'Tabelas de classificação (*.zip *.xlsx *.csv)')
        if not paths:
            return
        try:
            imported = [import_publisher_catalogue(path, system) for path in paths]
            # Test merge before adding anything, so incomplete selections do not leak in.
            merge_classification_catalogues(self.catalogues + imported)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, 'Catalogue not loaded', str(exc))
            return
        for cat in imported:
            self.catalogues.append(cat)
            item = QListWidgetItem(f"{cat['system']} · {len(cat['classifications'])} códigos · {cat['source_file']}")
            item.setToolTip('Fonte: ' + cat['source_sha256'] + '\n' + cat['source_file'])
            item.setData(Qt.UserRole, cat['id'])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.catalogue_list.addItem(item)
        self._refresh_primary()

    def _remove_catalogue(self):
        row = self.catalogue_list.currentRow()
        if row < 0:
            return
        item = self.catalogue_list.takeItem(row)
        self.catalogues = [c for c in self.catalogues if c['id'] != item.data(Qt.UserRole)]
        self._refresh_primary()

    def _selected_catalogues(self):
        ids = {self.catalogue_list.item(i).data(Qt.UserRole)
               for i in range(self.catalogue_list.count())
               if self.catalogue_list.item(i).checkState() == Qt.Checked}
        return [c for c in self.catalogues if c['id'] in ids]

    def _refresh_primary(self):
        previous = self.primary_choice.currentData()
        self.primary_choice.clear()
        self.primary_choice.addItem('Nenhum / classificar manualmente', '')
        for system in sorted({c['system'] for c in self.catalogues}):
            self.primary_choice.addItem(system, system)
        if previous:
            i = self.primary_choice.findData(previous)
            if i >= 0:
                self.primary_choice.setCurrentIndex(i)
        self.catalogue_info.setText(
            f'{len(self.catalogues)} arquivo(s) incorporáveis, '
            f'{sum(len(c["classifications"]) for c in self.catalogues)} códigos disponíveis. '
            'Códigos sem correspondência IFC explícita não serão atribuídos por suposição.')

    def _equivalences_changed(self, index):
        if self.map_choice.itemData(index) != 'file':
            self.crosswalks = []
            self.map_info.setText('No external equivalences; classifications preserved')
            return
        names, _ = QFileDialog.getOpenFileNames(
            self, 'Importar correspondências verificadas', '', 'Equivalências (*.csv *.json)')
        if not names:
            self.map_choice.setCurrentIndex(0)
            return
        try:
            self.crosswalks = [read_crosswalk(name) for name in names]
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Invalid equivalences', str(exc))
            self.map_choice.setCurrentIndex(0)
            return
        self.map_info.setText(f'{len(self.crosswalks)} fontes · '
            f'{sum(len(c["relations"]) for c in self.crosswalks)} relações identificadas')

    def _author_crosswalk(self):
        from .classification_crosswalk_editor import CrosswalkAuthorDialog
        dlg = CrosswalkAuthorDialog(self)
        if dlg.exec() and dlg.crosswalk:
            self.crosswalks.append(dlg.crosswalk)
            self.map_info.setText(f'{len(self.crosswalks)} catálogo(s) de correspondências · '
                f'{sum(len(c["relations"]) for c in self.crosswalks)} relações registradas')

    def _show_table_families(self):
        """Reference-only taxonomy families, never submitted to migration engine."""
        path = Path(__file__).parent / 'classification_crosswalks' / 'table_families.json'
        try:
            table = json.loads(path.read_text(encoding='utf-8'))
            lines = []
            for family in table['families']:
                cells = []
                for key in ('uniclass', 'omniclass', 'abnt'):
                    entry = family.get(key)
                    if isinstance(entry, dict):
                        cells.append(key.title() + ' ' + str(entry['table']))
                lines.append(str(family['subject']) + ': ' + ' · '.join(cells))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, 'Table-level correspondences', str(exc))
            return
        QMessageBox.information(
            self, 'Classification table-family reference',
            'Comparação conceitual de TABELAS, não equivalência de códigos individuais.\n'
            'NUNCA aplicar estas referências como migração automática.\n\n'
            + '\n'.join(lines)
            + '\n\nFontes: NBS Uniclass · CSI OmniClass · SICLIC FAU-USP.')

    def _layer_template(self):
        if self.layer_controller is None or self.layer_choice.currentData() is None:
            return None
        source, name = self.layer_choice.currentData()
        if source == 'builtin':
            from .layer_combinations import builtin_templates
            template = builtin_templates()[name]
        else:
            template = self.layer_controller.personal_templates()[name]
        return self.layer_controller.validate_template(template)

    def _project_information(self):
        # No duplicate settings store; metadata persists in the existing BIM
        # project record and remains editable in Informações do Projeto.
        values = {key: edit.text().strip() for key, edit in self.project_fields.items()}
        if self.template_igz is not None:
            # Do not overwrite a copied project's fields with empty input.
            return {key: val for key, val in values.items() if val}
        return values

    def _refresh_resource_libraries(self):
        self.libraries_list.clear()
        for pack in self.available_libraries:
            item = QListWidgetItem(pack['name'] + ' · ' + str(len(pack['resources'])) + ' objetos')
            saved=next((p for p in (self.template_bundle_resources or [])
                        if p.get('id')==pack['id']),None)
            item.setData(Qt.UserRole, saved if saved is not None else pack)
            if saved is not None and len(saved['resources'])!=len(pack['resources']):
                item.setText(pack['name']+' · '+str(len(saved['resources']))+' / '+str(len(pack['resources']))+' selected')
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            selected = pack['id'] == 'ot:arq:basica'
            if self.template_bundle_resources:
                selected = saved is not None
            item.setCheckState(Qt.Checked if selected else Qt.Unchecked)
            self.libraries_list.addItem(item)

    def _manage_resource_libraries(self):
        selected = self._library_choices()
        dlg = LibraryManagerDialog(self.app, self, selected=selected)
        if dlg.exec():
            selected_packs = dlg.selected_collections()
            self.available_libraries = dlg.packs
            self.libraries_list.clear()
            wanted = {p['id']:p for p in selected_packs}
            for pack in self.available_libraries:
                chosen=wanted.get(pack['id'])
                count=len(chosen['resources']) if chosen is not None else len(pack['resources'])
                item = QListWidgetItem(pack['name']+' · '+str(count)+' / '+str(len(pack['resources']))+' selected')
                # Preserve a partial selection rather than silently expanding
                # it to a whole library when the setup dialog is confirmed.
                item.setData(Qt.UserRole,chosen if chosen is not None else pack)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if chosen is not None else Qt.Unchecked)
                self.libraries_list.addItem(item)

    def _save_current_template(self):
        path, _ = QFileDialog.getSaveFileName(self,'Save complete template',
                       'My_OpenTrace_Template.ottemplate',
                       'Complete OpenTrace template (*.ottemplate)')
        if not path:
            return
        if not path.lower().endswith('.ottemplate'):
            path += '.ottemplate'
        try:
            name = Path(path).stem
            packs = self._library_choices()
            personal = capture_personal_resources()
            if personal['resources']:
                packs.append(personal)
            save_complete_template(self.app, path, name, packs)
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            QMessageBox.warning(self,'Save template', str(exc))
            return
        QMessageBox.information(self,'Template saved',
             'Complete template exported to:\n'+path+'\n'
             'Includes the native scene, layers, materials saved in the project, and '
             'selected libraries/presets. The current project was not replaced.')

    def _library_choices(self):
        return [copy.deepcopy(self.libraries_list.item(i).data(Qt.UserRole))
                for i in range(self.libraries_list.count())
                if self.libraries_list.item(i).checkState() == Qt.Checked
                and isinstance(self.libraries_list.item(i).data(Qt.UserRole), dict)]

    def _new_document_state(self):
        raw = self.app.document_data(default=None)
        win = self.app.window
        groups = len(getattr(self.app.scene, 'groups', ()) or ())
        clean = (getattr(win, '_current_path', None) is None and
                 getattr(self.app.scene, 'version', None) ==
                 getattr(win, '_saved_version', object()))
        clean = clean or bool(getattr(self.app.scene, '_opentrace_native_new_document', False))
        return raw, can_configure_new_document(
            raw, groups, has_saved_path=getattr(win, '_current_path', None) is not None,
            clean_untitled=clean)

    def apply(self):
        try:
            raw, allowed = self._new_document_state()
            if not allowed and self.template_igz is None:
                # User deliberately clicked "Criar projeto" with a document open.
                # Use the host's native new action (and its Save/Discard/Cancel
                # prompt). Never silently clear an existing document.
                win = self.app.window
                before_version = getattr(self.app.scene, 'version', None)
                before_path = getattr(win, '_current_path', None)
                native_new = getattr(win, '_on_new', None)
                if not callable(native_new):
                    raise ValueError('This IngeTrazo version cannot create a new document.')
                lc = (self.layer_controller or getattr(win, '_layer_combinations_controller', None))
                if lc is not None:
                    lc._suppress_next_native_new_prompt = True
                native_new()
                # The host reuses Scene and may retain the previous saved
                # version counter even after successfully creating a new file.
                if (before_version != getattr(self.app.scene, 'version', None)
                    and getattr(win, '_current_path', None) is None):
                    self.app.scene._opentrace_native_new_document = True
                raw, allowed = self._new_document_state()
                if (not allowed or
                    (before_version == getattr(self.app.scene, 'version', None)
                     and before_path == getattr(win, '_current_path', None))):
                    raise ValueError('New project cancelled; the current document was preserved.')
            elif not allowed and self.template_igz is not None:
                # .igz templates already open an independent native copy after
                # the host's own unsaved-changes confirmation.
                pass
            layer_template = self._layer_template()
            layer_meta = ({'name': layer_template['name'],
                           'source': self.layer_choice.currentData()[0],
                           'layer_count': len(layer_template['layer_names']),
                           'combination_count': len(layer_template['combinations'])}
                          if layer_template is not None else {'name': 'Preserved / empty'})
            chosen = self._selected_catalogues()
            catalogue = merge_classification_catalogues(chosen)
            primary = self.primary_choice.currentData() or ''
            if primary and primary not in {c['system'] for c in chosen}:
                raise ValueError('The primary catalogue must be one of the selected catalogues.')
            libraries = self._library_choices()
            if self.template_igz is None:
                data = configure_new_project(
                    raw, self.template, catalogue,
                    ifc_schema=self.schema_choice.currentData() or 'IFC4',
                    equivalence_catalogues=self.crosswalks,
                    primary_system=primary, layer_combination_set=layer_meta,
                    resource_libraries=libraries,
                    project_information=self._project_information())
                self.app.set_document_data(data)
                self.bim.data = data
                self.bim.refresh()
                if self.layer_controller is not None:
                    if layer_template is not None:
                        self.layer_controller.apply_template(layer_template)
                    else:
                        self.layer_controller._initial_prompt_pending = False
                        self.layer_controller.save_data()
            else:
                self._create_from_igz(catalogue, primary, layer_template, layer_meta, libraries)
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
            QMessageBox.warning(self, 'Project setup not completed', str(exc))
            return
        self.applied_setup = True
        panel = getattr(self.app.window, '_arquitetura_parametrica_suite_panel', None)
        refresh = getattr(panel, 'refresh_project_setup', None)
        if callable(refresh):
            try:
                refresh()
            except RuntimeError:
                pass
        self.accept()

    def _create_from_igz(self, catalogue, primary, layer_template, layer_meta, libraries):
        source = self.template_igz
        suggested = source.with_name(source.stem + ' - Novo projeto.igz')
        name, _ = QFileDialog.getSaveFileName(
            self, 'Salvar NOVO projeto', str(suggested), 'Projetos IngeTrazo (*.igz)')
        if not name:
            raise ValueError('Criação cancelada; origem preservada.')
        dest = Path(name)
        if dest.suffix.lower() != '.igz':
            dest = dest.with_suffix('.igz')
        win = self.app.window
        if not callable(getattr(win, 'open_path', None)):
            raise ValueError('Este IngeTrazo não expõe abertura nativa de .igz.')
        confirm = getattr(win, '_confirm_discard', None)
        if callable(confirm) and not confirm('Criar projeto independente a partir do template?'):
            raise ValueError('Operação cancelada.')
        if self.template_bundle is not None:
            extract_template(self.template_bundle, dest)
        else:
            dest = copy_igz_template(source, dest)
        if not win.open_path(dest):
            try:
                dest.unlink()
            except OSError:
                pass
            raise ValueError('Não foi possível abrir o novo .igz; origem intocada.')
        initial_digest = file_sha256(dest)
        data = configure_cloned_igz(
            self.app.document_data(default=None), source, catalogue,
            ifc_schema=self.schema_choice.currentData() or 'IFC4',
            equivalence_catalogues=self.crosswalks, primary_system=primary,
            layer_combination_set=layer_meta, resource_libraries=libraries,
            project_information=self._project_information())
        self.app.set_document_data(data)
        self.bim.data = data
        self.bim.refresh()
        if layer_template is not None and self.layer_controller is not None:
            self.layer_controller.apply_template(layer_template)
        save = getattr(win, '_do_save', None)
        if not callable(save):
            raise ValueError('Projeto copiado e aberto; salve no IngeTrazo para '
                             'gravar as novas configurações.')
        save(dest)
        if getattr(win, '_current_path', None) != dest or file_sha256(dest) == initial_digest:
            raise ValueError('Cópia aberta, mas a gravação não foi confirmada. '
                             'Salve manualmente antes de fechar.')
