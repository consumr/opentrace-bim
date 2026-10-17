# SPDX-License-Identifier: GPL-3.0-or-later
"""EXPERIMENTAL: author explicit, evidence-backed classification correspondences.

A manually entered pair is not asserted by OpenTrace to be a standard mapping.
Only an explicitly reviewed exact relation with URI and edition is eligible
for the existing proposal engine; conflict resolution remains reviewable.
"""
from __future__ import annotations
import uuid
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QVBoxLayout,
)
from .classification_equivalences import validate_crosswalk

SYSTEMS = ('Uniclass 2015', 'ABNT NBR 15965', 'OmniClass', 'MasterFormat', 'UniFormat', 'CoClass')


class CrosswalkAuthorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crosswalk = None
        self.setWindowTitle('Add reviewable mapping between classifications')
        self.resize(610, 380)
        lay = QVBoxLayout(self)
        message = QLabel('Enter codes verified against source tables. The same IFC class or similar name DOES NOT prove equivalence. '
                         'Unverified mappings remain pending review.')
        message.setWordWrap(True)
        lay.addWidget(message)
        form = QFormLayout()
        self.source_system = QComboBox(); self.source_system.setEditable(True)
        self.target_system = QComboBox(); self.target_system.setEditable(True)
        for system in SYSTEMS:
            self.source_system.addItem(system)
            self.target_system.addItem(system)
        self.target_system.setCurrentIndex(1)
        self.source_code = QLineEdit()
        self.target_code = QLineEdit()
        self.kind = QComboBox()
        for relation, desc in (('related','Related (review)'),
                               ('similar','Similar (review)'),
                               ('broader','Broader source'),
                               ('narrower','Narrower source'),
                               ('exact','Exact equivalence (with evidence)')):
            self.kind.addItem(desc, relation)
        self.publisher = QLineEdit()
        self.edition = QLineEdit()
        self.url = QLineEdit()
        self.url.setPlaceholderText('https://... original reference')
        self.verified = QCheckBox('I reviewed the cited source directly')
        for label, field in (
            ('Source system',self.source_system),('Source code',self.source_code),
            ('Target system',self.target_system),('Target code',self.target_code),
            ('Relation type',self.kind),('Reference publisher',self.publisher),
            ('Source edition/revision',self.edition),('Evidence URL',self.url),
            ('Reference review',self.verified)):
            form.addRow(label,field)
        lay.addLayout(form)
        footer = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        footer.button(QDialogButtonBox.Ok).setText('Add for review')
        footer.accepted.connect(self._apply)
        footer.rejected.connect(self.reject)
        lay.addWidget(footer)

    def _apply(self):
        verified = bool(self.verified.isChecked())
        if verified and (not self.edition.text().strip() or not self.url.text().startswith('https://')):
            QMessageBox.warning(self, 'Incomplete evidence',
                'A reviewed mapping requires an HTTPS URL and source edition; '
                'otherwise uncheck the reviewed option.')
            return
        crosswalk = {
            'format':'opentrace-classification-equivalences', 'version':1,
            'id': 'user:local:'+str(uuid.uuid4()),
            'name':'Correspondência informada pelo usuário (não homologada pelo OpenTrace)',
            'revision':'1', 'relations':[{ 
                'source':{'system':self.source_system.currentText().strip(), 'code':self.source_code.text().strip()},
                'target':{'system':self.target_system.currentText().strip(), 'code':self.target_code.text().strip()},
                'relation':self.kind.currentData(),
                'evidence':{'status':'verified' if verified else 'unreviewed',
                            'uri':self.url.text().strip(), 'edition':self.edition.text().strip(),
                            'publisher':self.publisher.text().strip(),
                            'note':'Correspondência fornecida pelo usuário; não homologada pelo OpenTrace'},
            }],
        }
        try:
            self.crosswalk = validate_crosswalk(crosswalk)
        except ValueError as exc:
            QMessageBox.warning(self, 'Invalid mapping', str(exc))
            return
        self.accept()
