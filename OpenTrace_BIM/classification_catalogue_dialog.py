# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPERIMENTAL catalogue sources and per-object classifier dialogs."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QInputDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .classification_access import (
    download_uniclass_archive, load_uniclass_archive, classification_cache_dir,
    NBS_CURRENT, ARCHIVE_EDITION,
)
from .classification_assignments import (add_reference, normalized_entries, remove_reference)
from .official_classification_import import import_publisher_catalogue
from .project_setup import catalogue_from_document, merge_classification_catalogues
from .siclic_bsdd_access import download_siclic_preview

SYSTEMS = ('Uniclass 2015', 'ABNT NBR 15965', 'OmniClass', 'MasterFormat', 'UniFormat', 'CoClass')


class _DownloadThread(QThread):
    stage = Signal(str)
    installed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            folder = classification_cache_dir()
            def progress(n, total, name):
                self.stage.emit(f'Obtendo {name} ({n}/{total}) — edição histórica 2022…')
            download_uniclass_archive(folder, progress=progress)
            self.installed.emit(load_uniclass_archive(folder))
        except Exception as exc:
            self.failed.emit(str(exc))


class _SiclicThread(QThread):
    stage = Signal(str)
    installed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            def progress(page, total, count):
                self.stage.emit(
                    f'SICLIC bSDD: página {page} · {count} códigos recebidos '
                    f'· total de classes: {total if total is not None else "não informado"}')
            self.installed.emit(download_siclic_preview(progress=progress))
        except Exception as exc:
            self.failed.emit(str(exc))


class CatalogueSourcesDialog(QDialog):
    """An explicit installation workflow; never download a source on startup."""
    def __init__(self, catalogues=None, parent=None):
        super().__init__(parent)
        self.catalogues = copy.deepcopy(list(catalogues or []))
        self.worker = None
        self.setWindowTitle('EXPERIMENTAL · Catalogues de classification')
        self.resize(760, 490)
        lay = QVBoxLayout(self)
        intro = QLabel('IFC is the exchange schema; these tables are independent classification systems. '
                       'Similar names or IFC classes do not establish automatic equivalence.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.rows = QListWidget(self)
        lay.addWidget(self.rows, 1)
        self.status = QLabel('No automatic network requests. Use the buttons to add tables.')
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.fetch = QPushButton('Install Uniclass 2015 — complete 2022 archive (online, one click)')
        self.fetch.clicked.connect(self._fetch)
        lay.addWidget(self.fetch)
        self.siclic = QPushButton('Browse and install ABNT via bSDD — SICLIC preview 0.1.2')
        self.siclic.setToolTip('Queries the source cited by SICLIC/FAU-USP. This is not the complete standard.')
        self.siclic.clicked.connect(self._fetch_siclic)
        lay.addWidget(self.siclic)
        self.cache = QPushButton('Use Uniclass 2022 already installed on this computer')
        self.cache.clicked.connect(self._cached)
        lay.addWidget(self.cache)
        row = QHBoxLayout()
        self.browse = QPushButton('Import original CSV/XLSX/ZIP table…')
        self.browse.clicked.connect(self._browse)
        row.addWidget(self.browse)
        self.manual_abnt = QPushButton('Add a verified ABNT code…')
        self.manual_abnt.clicked.connect(self._manual_abnt)
        row.addWidget(self.manual_abnt)
        remove = QPushButton('Remove from selection')
        remove.clicked.connect(self._remove)
        row.addWidget(remove)
        lay.addLayout(row)
        refs = QHBoxLayout()
        for label, url in (('Current Uniclass · NBS', NBS_CURRENT),
                           ('Dictionaries · buildingSMART', 'https://search.bsdd.buildingsmart.org/'),
                           ('OmniClass · CSI', 'https://www.csiresources.org/csistore/oc-eula')):
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            refs.addWidget(btn)
        lay.addLayout(refs)
        license = QLabel('The previous SICLIC link was removed from installation. '
                         'Use the ABNT button above to query bSDD directly. '
                         'Uniclass 2022 is a historic public mirror of NBS data. '
                         'The current July 2026 edition can be imported from NBS files. '
                         'ABNT: use the SICLIC/bSDD preview or import a Code/Term spreadsheet. '
                         'The preview does not replace the full standard. OmniClass requires an external file.')
        license.setWordWrap(True)
        lay.addWidget(license)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('Use selected catalogues')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self._refresh()

    def _refresh(self):
        self.rows.clear()
        for cat in self.catalogues:
            item = QListWidgetItem(f"{cat.get('system', '')} · {len(cat.get('classifications', {})):,} codes · {cat.get('edition') or cat.get('source_file') or 'local file'}")
            item.setData(Qt.UserRole, cat.get('id'))
            item.setToolTip(f"Source: {cat.get('source_url') or cat.get('source_file') or ''}\nHash: {cat.get('source_sha256') or ''}")
            self.rows.addItem(item)

    def _add(self, cat):
        if any(x.get('id') == cat.get('id') for x in self.catalogues):
            self.status.setText('This catalogue edition is already loaded in this project.')
            return False
        try:
            merge_classification_catalogues(self.catalogues + [cat])
        except ValueError as exc:
            QMessageBox.warning(self, 'Conflicting catalogue', str(exc))
            return False
        self.catalogues.append(cat)
        self._refresh()
        self.status.setText(f"Catalogue loaded: {cat.get('system')} · {len(cat['classifications']):,} códigos")
        return True

    def _cached(self):
        try:
            self._add(load_uniclass_archive(classification_cache_dir()))
        except (ValueError, OSError, KeyError) as exc:
            QMessageBox.warning(self, 'Cache Uniclass', str(exc))

    def _fetch(self):
        if self.worker and self.worker.isRunning():
            return
        self.fetch.setEnabled(False)
        self.cache.setEnabled(False)
        self.siclic.setEnabled(False)
        self.browse.setEnabled(False)
        self.manual_abnt.setEnabled(False)
        self.status.setText('Download started by your request; please wait…')
        worker = _DownloadThread(self)
        self.worker = worker
        worker.stage.connect(self.status.setText)
        worker.installed.connect(self._downloaded)
        worker.failed.connect(self._download_failed)
        worker.finished.connect(self._worker_finished)
        worker.start()

    def _worker_finished(self):
        self.fetch.setEnabled(True)
        self.siclic.setEnabled(True)
        self.cache.setEnabled(True)
        self.browse.setEnabled(True)
        self.manual_abnt.setEnabled(True)

    def _fetch_siclic(self):
        if self.worker and self.worker.isRunning():
            return
        answer = QMessageBox.question(
            self, 'SICLIC — demonstration dictionary',
            'O SICLIC/FAU-USP aponta um dicionário de demonstração no '
            'buildingSMART bSDD (versão 0.1.2). Ele NÃO contém necessariamente '
            'as tabelas completas da ABNT NBR 15965.\n\n'
            'Consultar os códigos disponíveis e associá-los ao projeto?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.fetch.setEnabled(False)
        self.siclic.setEnabled(False)
        self.cache.setEnabled(False)
        self.browse.setEnabled(False)
        self.manual_abnt.setEnabled(False)
        self.status.setText('Querying SICLIC on bSDD as requested…')
        worker = _SiclicThread(self)
        self.worker = worker
        worker.stage.connect(self.status.setText)
        worker.installed.connect(self._siclic_downloaded)
        worker.failed.connect(self._siclic_failed)
        worker.finished.connect(self._worker_finished)
        worker.start()

    def _siclic_downloaded(self, catalogue):
        if self._add(catalogue):
            self.status.setText(
                f'SICLIC demonstrativo: {len(catalogue["classifications"]):,} códigos; '
                f'{len(catalogue.get("table_counts", {}))} tabelas. '
                'Prévia bSDD — não substitui a norma ABNT completa.')

    def _siclic_failed(self, message):
        self.status.setText('bSDD query unavailable. You can import an ABNT CSV/XLSX/ZIP instead.')
        QMessageBox.warning(self, 'SICLIC / ABNT — query incomplete',
            'O serviço bSDD não retornou a prévia SICLIC. Nenhum dado incompleto foi instalado.\n\n'
            + str(message) + '\n\n'
            'Alternativa: clique em Import original CSV/XLSX/ZIP table… '
            'e selecione ABNT NBR 15965.')

    def accept(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, 'Download em curso', 'Aguarde terminar antes de fechar.')
            return
        super().accept()

    def _downloaded(self, catalogue):
        self._add(catalogue)

    def _download_failed(self, message):
        self.status.setText('Download did not complete; no incomplete catalogue was installed.')
        QMessageBox.warning(self, 'Uniclass — falha de rede ou fonte', message)

    def reject(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, 'Download em curso', 'Aguarde terminar antes de fechar.')
            return
        super().reject()

    def _browse(self):
        name, ok = QInputDialog.getItem(
            self, 'Classification', 'System:', list(SYSTEMS) + ['Personalizado'], 0, False)
        if not ok:
            return
        if name == 'Personalizado':
            name, ok = QInputDialog.getText(
                self, 'System personalizado', 'Nome do sistema:')
            if not ok or not name.strip():
                return
        paths, _ = QFileDialog.getOpenFileNames(self, 'Tabelas originais do editor', '',
                                                'Classificações (*.csv *.xlsx *.zip)')
        if not paths:
            return
        try:
            cats = [import_publisher_catalogue(path, name) for path in paths]
            merge_classification_catalogues(self.catalogues + cats)
        except (ValueError, OSError, TypeError) as exc:
            QMessageBox.warning(self, 'Import incomplete', str(exc))
            return
        for cat in cats:
            self._add(cat)

    def _manual_abnt(self):
        from .siclic_bsdd_access import _abnt_table, SICLIC_SOURCE
        code, ok = QInputDialog.getText(
            self, 'Code ABNT consultado',
            'Code consultado na NBR 15965 / SICLIC (ex.: 3E.xx.xx):')
        if not ok:
            return
        code = code.strip()
        table = _abnt_table(code)
        if not table or len(code) > 160:
            QMessageBox.warning(self, 'Code invalid',
                                'Enter a code from one of the 13 ABNT tables (0M, 0P, 1F, etc.).')
            return
        name, ok = QInputDialog.getText(self, 'ABNT code description',
                                         'Term verified against the source (not generated):')
        if not ok or not name.strip():
            return
        name = name.strip()
        if len(name) > 500:
            QMessageBox.warning(self, 'Invalid description', 'Maximum 500 characters.')
            return
        fingerprint = hashlib.sha256((code + '\0' + name).encode('utf-8')).hexdigest()
        self._add({'id': 'abnt:user:' + fingerprint,
                   'name': 'ABNT NBR 15965 — código informado pelo usuário',
                   'system': 'ABNT NBR 15965',
                   'source_file': 'código informado pelo usuário',
                   'source_sha256': fingerprint, 'source_url': SICLIC_SOURCE,
                   'edition': 'Termo informado — validar com a edição da norma',
                   'table_counts': {table: 1}, 'user_supplied': True,
                   'classifications': {'ABNT NBR 15965 · ' + code: {
                       'system': 'ABNT NBR 15965', 'code': code, 'name': name,
                       'table': table, 'ifc_classes': [], 'matches': []}}})

    def _remove(self):
        item = self.rows.currentItem()
        if item:
            self.catalogues = [c for c in self.catalogues if c.get('id') != item.data(Qt.UserRole)]
            self._refresh()


class ObjectClassificationDialog(QDialog):
    """Search/assign explicit system codes, simultaneously, using IFC history."""
    def __init__(self, app, group, document, parent=None):
        super().__init__(parent)
        self.app, self.group = app, group
        self.catalogue = catalogue_from_document(document)
        self.definitions = list(self.catalogue.get('classifications', {}).values())
        self.meta = copy.deepcopy(getattr(group, 'ifc', None) or {})
        self.setWindowTitle('Object BIM classifications · multiple systems')
        self.resize(900, 630)
        root = QVBoxLayout(self)
        self.selected = QListWidget(self)
        root.addWidget(QLabel('Classifications assigned to the element (geometry unchanged):'))
        root.addWidget(self.selected)
        row = QHBoxLayout()
        self.query = QLineEdit(); self.query.setPlaceholderText('Search code or description…')
        self.query.textChanged.connect(self._search)
        row.addWidget(self.query, 1)
        self.system = QComboBox()
        self.system.addItem('Todos os sistemas', '')
        for sys in sorted({str(x.get('system')) for x in self.definitions if x.get('system')}):
            self.system.addItem(sys, sys)
        self.system.currentIndexChanged.connect(self._search)
        row.addWidget(self.system)
        root.addLayout(row)
        self.results = QTableWidget(0, 3)
        self.results.setHorizontalHeaderLabels(('Sistema', 'Código', 'Descrição'))
        self.results.setColumnWidth(0, 160); self.results.setColumnWidth(1, 160)
        self.results.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.results, 1)
        buttons = QHBoxLayout()
        add = QPushButton('Associar code selected')
        add.clicked.connect(self._add_selected)
        buttons.addWidget(add)
        rm = QPushButton('Remove selected association')
        rm.clicked.connect(self._remove_selected)
        buttons.addWidget(rm)
        make_main = QPushButton('Tornar principal')
        make_main.clicked.connect(self._set_primary)
        buttons.addWidget(make_main)
        root.addLayout(buttons)
        manual = QFormLayout()
        self.manual_system = QComboBox()
        self.manual_system.setEditable(True)
        for sys in SYSTEMS:
            self.manual_system.addItem(sys)
        self.manual_code = QLineEdit(); self.manual_code.setPlaceholderText('Code consultado na fonte')
        self.manual_name = QLineEdit(); self.manual_name.setPlaceholderText('Verified description (optional)')
        manual.addRow('System', self.manual_system)
        manual.addRow('Code', self.manual_code)
        manual.addRow('Description', self.manual_name)
        root.addLayout(manual)
        add_manual = QPushButton('Assign manually entered code (not verified by OpenTrace)')
        add_manual.clicked.connect(self._add_manual)
        root.addWidget(add_manual)
        self.info = QLabel('Check every code against its official source. IFC4/IFC4.3 and export profiles are independent.')
        self.info.setWordWrap(True)
        root.addWidget(self.info)
        footer = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        footer.button(QDialogButtonBox.Save).setText('Save classifications to object')
        footer.accepted.connect(self._save)
        footer.rejected.connect(self.reject)
        root.addWidget(footer)
        self._refresh_selected()
        self._search()

    def _refresh_selected(self):
        self.selected.clear()
        for definition in normalized_entries(self.meta):
            item = QListWidgetItem(f"{definition['system']}  ·  {definition['code']}  ·  {definition.get('name') or ''}")
            item.setData(Qt.UserRole, (definition['system'], definition['code']))
            self.selected.addItem(item)

    def _search(self, *_):
        text = self.query.text().strip().casefold()
        system = self.system.currentData()
        matches = [x for x in self.definitions if (not system or x.get('system') == system)
                   and (not text or text in (str(x.get('code'))+' '+str(x.get('name'))).casefold())]
        self.results.setRowCount(min(200, len(matches)))
        for i, definition in enumerate(matches[:200]):
            for col, val in enumerate((definition.get('system', ''), definition.get('code', ''), definition.get('name', ''))):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.UserRole, definition)
                self.results.setItem(i, col, item)
        self.info.setText(f'{len(matches)} resultados · exibindo até 200; refine a pesquisa para localizar o código.')

    def _add_selected(self):
        row = self.results.currentRow()
        if row < 0:
            return
        item = self.results.item(row, 0)
        if item is None:
            return
        definition = item.data(Qt.UserRole)
        # A catalogue's provenance travels with its entry when available.
        source = next((x for x in (self.catalogue.get('sources') or []) if x.get('system') == definition.get('system')), {})
        self.meta = add_reference(self.meta, definition, provenance=source)
        self._refresh_selected()

    def _add_manual(self):
        definition = {'system': self.manual_system.currentText(), 'code': self.manual_code.text(),
                      'name': self.manual_name.text()}
        try:
            self.meta = add_reference(self.meta, definition)
        except ValueError as exc:
            QMessageBox.warning(self, 'Code invalid', str(exc))
            return
        self._refresh_selected()

    def _set_primary(self):
        item = self.selected.currentItem()
        if item:
            system, code = item.data(Qt.UserRole)
            self.meta['classification_system'] = system
            self.meta['classification_code'] = code
            self.meta['classification_opt_out'] = False
            self.info.setText(f'Classificação principal: {system} · {code}')

    def _remove_selected(self):
        item = self.selected.currentItem()
        if item:
            self.meta = remove_reference(self.meta, *item.data(Qt.UserRole))
            self._refresh_selected()

    def _save(self):
        from .bim import set_ifc_metadata
        try:
            set_ifc_metadata(self.app, self.group, self.meta)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, 'Could not save classifications', str(exc))
            return
        self.accept()
