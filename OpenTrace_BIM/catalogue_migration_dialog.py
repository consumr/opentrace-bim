# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental catalogue-switch review inside BIM properties.

No action mutates the scene until user confirms. Codes in an external national
catalogue are imported from an actual CSV/JSON supplied by the user; OpenTrace
never presents IFC4 entities as an official Uniclass or ABNT taxonomy.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QDialog, QFileDialog, QLineEdit,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from .project_setup import empty_catalogue, read_catalogue, catalogue_from_document
from .catalogue_migration import preview_migration, apply_migration
from .classification_equivalences import read_crosswalk, crosswalks_from_document


class CatalogueMigrationDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.catalogue = None
        self.preview = None
        self.crosswalks = crosswalks_from_document(app.document_data(default=None))
        self.setWindowTitle('EXPERIMENTAL · Migrate IFC classification catalogue')
        self.resize(920, 570)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            'Choose a destination catalogue and review the mappings '
            'before confirming. Geometry, layers, parameters, GlobalIds, and favourites '
            'will not be replaced. ABNT, Uniclass, and other systems require their '
            'real data imported as CSV/JSON.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        row = QHBoxLayout()
        self.destination = QComboBox(self)
        self.destination.addItem('Internal IFC4 (not a national classification)', 'builtin')
        self.destination.addItem('Choose CSV / JSON / XLSX / ZIP…', 'external')
        active = catalogue_from_document(app.document_data(default=None))
        self._loaded_destinations = {}
        for system in sorted({v.get('system') for v in active.get('classifications', {}).values() if v.get('system')}):
            defs = {k: v for k,v in active['classifications'].items() if v.get('system') == system}
            self._loaded_destinations[system] = {
                'id': 'loaded:' + system, 'name': system + ' · loaded in project',
                'classifications': defs,
            }
            self.destination.addItem(f'{system} · já carregado ({len(defs):,} codes)', 'loaded:' + system)
        self.destination.currentIndexChanged.connect(self._catalogue_changed)
        row.addWidget(QLabel('Migrate to:'))
        row.addWidget(self.destination, 1)
        self.browse = QPushButton('Choose file…')
        self.browse.clicked.connect(self._select_file)
        row.addWidget(self.browse)
        layout.addLayout(row)
        crossrow = QHBoxLayout()
        self.map_button = QPushButton('Load equivalence catalogue…')
        self.map_button.setToolTip('Import a versioned CSV/JSON crosswalk for ABNT, Uniclass, OmniClass, etc. Only verified exact matches can be proposed automatically.')
        self.map_button.clicked.connect(self._load_crosswalk)
        crossrow.addWidget(self.map_button)
        self.manual_map_button = QPushButton('Record mapping…')
        self.manual_map_button.clicked.connect(self._author_crosswalk)
        crossrow.addWidget(self.manual_map_button)
        self.map_info = QLabel(f'{len(self.crosswalks)} equivalence catalogues in this project')
        self.map_info.setWordWrap(True)
        crossrow.addWidget(self.map_info, 1)
        layout.addLayout(crossrow)
        self.summary = QLabel('Choose a catalogue to prepare the comparison.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            ['Current classification', 'IFC class', 'Objects', 'Status', 'Target classification'])
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 68)
        self.table.setColumnWidth(3, 100)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.retain = QCheckBox('Keep unmatched classifications pending (without deleting them)')
        self.retain.setChecked(True)
        layout.addWidget(self.retain)
        note = QLabel('Preview: no changes are made before confirming the migration. '
                      'Unmatched items remain stored in the project for later review. '
                      'Undo restores the previous classifications and catalogue.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel = QPushButton('Cancel')
        self.apply_btn = QPushButton('Confirm migration')
        self.apply_btn.setEnabled(False)
        buttons.addWidget(self.cancel)
        buttons.addWidget(self.apply_btn)
        layout.addLayout(buttons)
        self.cancel.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self._apply)
        self._catalogue_changed()

    def _catalogue_changed(self, *_):
        if self.destination.currentData() == 'builtin':
            self.catalogue = empty_catalogue()
            self._preview()
        elif str(self.destination.currentData()).startswith('loaded:'):
            self.catalogue = self._loaded_destinations[self.destination.currentData()[7:]]
            self._preview()
        else:
            self.catalogue = None
            self.table.setRowCount(0)
            self.apply_btn.setEnabled(False)
            self.summary.setText('Select a real catalogue file (.csv/.json).')

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Target catalogue', '', 'Classification catalogues (*.csv *.json *.xlsx *.zip)')
        if not path:
            return
        try:
            if path.lower().endswith(('.xlsx', '.zip')):
                from .official_classification_import import import_publisher_catalogue
                from PySide6.QtWidgets import QInputDialog
                name, ok = QInputDialog.getItem(self, 'Sistema do destino', 'System:',
                    ['Uniclass 2015', 'ABNT NBR 15965', 'OmniClass', 'MasterFormat', 'UniFormat', 'CoClass'], 0, False)
                if not ok: return
                self.catalogue = import_publisher_catalogue(path, name)
            else:
                try:
                    self.catalogue = read_catalogue(path)
                except (ValueError, UnicodeDecodeError):
                    from .official_classification_import import import_publisher_catalogue
                    from PySide6.QtWidgets import QInputDialog
                    name, ok = QInputDialog.getItem(self, 'Sistema do destino', 'System:',
                        ['Uniclass 2015', 'ABNT NBR 15965', 'OmniClass', 'MasterFormat', 'UniFormat', 'CoClass'], 0, False)
                    if not ok: return
                    self.catalogue = import_publisher_catalogue(path, name)
            self.destination.blockSignals(True)
            self.destination.setCurrentIndex(1)
            self.destination.blockSignals(False)
            self._preview()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Catalogue invalid', str(exc))

    def _author_crosswalk(self):
        from .classification_crosswalk_editor import CrosswalkAuthorDialog
        dlg = CrosswalkAuthorDialog(self)
        if dlg.exec() and dlg.crosswalk:
            self.crosswalks.append(dlg.crosswalk)
            self.map_info.setText(f'{len(self.crosswalks)} crosswalk catalogues · '
                                  f'{sum(len(c["relations"]) for c in self.crosswalks)} relations')
            self._preview()

    def _load_crosswalk(self):
        name, _ = QFileDialog.getOpenFileName(
            self, 'Verified equivalence catalogue', '',
            'Equivalence catalogues (*.csv *.json)')
        if not name:
            return
        try:
            mapping = read_crosswalk(name)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Invalid equivalences', str(exc))
            return
        self.crosswalks = [c for c in self.crosswalks if c['id'] != mapping['id']]
        self.crosswalks.append(mapping)
        self.map_info.setText(f'{len(self.crosswalks)} equivalence catalogues · '
                              f'{sum(len(c["relations"]) for c in self.crosswalks)} relations')
        self._preview()

    def _preview(self):
        self.table.setRowCount(0)
        self.apply_btn.setEnabled(False)
        if self.catalogue is None:
            return
        try:
            raw = self.app.document_data(default=None)
            self.preview = preview_migration(self.app.scene.groups, raw, self.catalogue, self.crosswalks)
        except (ValueError, TypeError) as exc:
            self.summary.setText('Could not prepare preview: ' + str(exc))
            return
        self.table.setRowCount(len(self.preview.rows))
        # Large official catalogues can contain tens of thousands of codes.
        # A drop-down with EVERY code repeated for EVERY element type exhausts
        # the GUI. A single search completion model keeps editing responsive.
        options = sorted(self.catalogue.get('classifications', {}).items())
        from PySide6.QtCore import QStringListModel
        keys = [key for key, _definition in options]
        self._completion_model = QStringListModel(keys, self)
        for row_idx, row in enumerate(self.preview.rows):
            current = ' · '.join(row['source']) if row['source'] else '(unclassified)'
            for col, value in enumerate((current, row['ifc_class'], str(row['count']), row['status'])):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, col, item)
            editor = QLineEdit(self.table)
            editor.setPlaceholderText('Pending · enter a catalogue code or name')
            completion = QCompleter(self._completion_model, editor)
            completion.setFilterMode(Qt.MatchContains)
            completion.setCaseSensitivity(Qt.CaseInsensitive)
            completion.setCompletionMode(QCompleter.PopupCompletion)
            editor.setCompleter(completion)
            proposed = row['proposal']
            if proposed is not None:
                key = next((k for k, defn in options
                            if (defn.get('system'), defn.get('code')) ==
                            (proposed['system'], proposed['code'])), '')
                editor.setText(key)
            if row.get('suggestions'):
                editor.setToolTip('Some mappings require source verification; search for a target.')
            self.table.setCellWidget(row_idx, 4, editor)
        self.summary.setText(
            f"Destination: {self.catalogue.get('name', '')} · "
            f"{len(options)} codes · {self.preview.count} BIM objects · "
            f"{self.preview.unresolved} classification types with conflicts/pending items"
            + (f" · {len(self.preview.library_conflicts)} library definitions sharing a code but with different meanings (both will be preserved)"
               if self.preview.library_conflicts else ''))
        self.apply_btn.setEnabled(True)

    def _apply(self):
        if self.preview is None or self.catalogue is None:
            return
        choices = {}
        outstanding = 0
        for idx, row in enumerate(self.preview.rows):
            code = self.table.cellWidget(idx, 4).text().strip() or None
            if code is not None and code not in self.catalogue.get('classifications', {}):
                QMessageBox.warning(self, 'Code not found',
                    f'The code on row {idx + 1} does not belong to the destination catalogue. '
                    'Choose a complete suggestion or leave it blank.')
                return
            choices[row['key']] = code
            if code is None:
                outstanding += row['count']
        if outstanding and not self.retain.isChecked():
            QMessageBox.warning(self, 'Migration pending',
                                'Resolve every mapping or allow unmatched classifications to remain pending.')
            return
        msg = (f"Destination: {self.catalogue.get('name', '')}\n"
               f"Objects avaliados: {self.preview.count}\n"
               f"Objects com classificação mantida como pendente: {outstanding}\n\n"
               'Confirm changing IFC classifications only?')
        if QMessageBox.question(self, 'Confirm migration', msg,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            changed, pending = apply_migration(
                self.app, self.preview, choices, keep_pending=self.retain.isChecked())
        except (ValueError, TypeError, RuntimeError) as exc:
            QMessageBox.warning(self, 'Migration not applied', str(exc))
            return
        QMessageBox.information(self, 'IFC migration',
                                f'{changed} objects updated; {len(pending)} mappings pending. '
                                'Save the project to keep the changes.')
        self.accept()
