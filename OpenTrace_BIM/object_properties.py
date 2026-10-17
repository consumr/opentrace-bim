# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared layer and IFC properties backed by host entities and native history."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from core.layers import DEFAULT_LAYER, layer_of
from core.history import AssignLayerCommand
from .bim import KIND_TO_CLASS, DEFAULT_PREDEFINED, ifc_identity_data, set_ifc_metadata
from .creation_properties import creation_defaults
from .host import WALL_TOOL_KEY, SLAB_TOOL_KEY, COLUMN_TOOL_KEY, BEAM_TOOL_KEY, host_tool
from .i18n import t
from .ifc_catalog import predefined_types

TOOL_KEYS = {
    "wall": WALL_TOOL_KEY, "slab": SLAB_TOOL_KEY,
    "column": COLUMN_TOOL_KEY, "beam": BEAM_TOOL_KEY,
    "door": "opentrace_wall_door_tool", "window": "opentrace_wall_window_tool",
}


def creation_kind(app):
    active = app.viewport.active_tool
    for kind, key in TOOL_KEYS.items():
        if active is host_tool(app, key):
            return kind
    return None


def selected_entities(scene):
    if scene.edit_group is not None:
        return []
    result = []
    for item in scene.selection:
        entity = getattr(item, "owner", None) or item
        if entity not in result:
            result.append(entity)
    return result


class ObjectProperties(QWidget):
    """One sidebar editor, with a mirrored layer selector in the Info Box."""
    def __init__(self, suite):
        super().__init__(suite.panel)
        self.suite = suite
        self.app = suite.app
        self._layer_combos = []
        self._signature = None
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        self.context = QLabel()
        from .panel_sections import EditorSection
        body = QWidget()
        content = QVBoxLayout(body)
        content.setContentsMargins(0,0,0,0)
        content.addWidget(self.context)
        form = QFormLayout()
        self.layer = self.make_layer_combo(self)
        form.addRow(t("Layer"), self.layer)
        content.addLayout(form)
        fields = QFormLayout()
        content.addLayout(fields)
        self.ifc_class = QLabel()
        self.predefined = QComboBox()
        self.library = QComboBox()
        self.library.setObjectName("opentrace_ifc_classification_catalog")
        self.library.setEditable(True)
        self.library.setInsertPolicy(QComboBox.NoInsert)
        self.library.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.library.completer().setFilterMode(Qt.MatchContains)
        self.library.setMaxVisibleItems(25)
        self.library.setToolTip("Full IFC4 (internal categories) and personal/imported classifications. IFC4 entity classes do not replace ABNT, Uniclass, or other codes.")
        self.library.activated.connect(self.choose_classification)
        self.system = QLineEdit()
        self.code = QLineEdit()
        for field in (self.system, self.code):
            field.setPlaceholderText(t("Not defined"))
        fields.addRow(t("Classe IFC"), self.ifc_class)
        fields.addRow(t("Tipo predefinido"), self.predefined)
        fields.addRow(t("Biblioteca de classificações"), self.library)
        fields.addRow(t("Sistema de classificação"), self.system)
        fields.addRow(t("Código de classificação"), self.code)
        self.apply = QLabel("Changes take effect when a field is confirmed.")
        self.apply.setWordWrap(True)
        fields.addRow(self.apply)
        # Only user activation, never programmatic refresh, commits a new type.
        self.predefined.activated.connect(self.apply_ifc)
        self.system.editingFinished.connect(self.apply_ifc)
        self.code.editingFinished.connect(self.apply_ifc)
        # Project-wide operation in BIM properties, not a per-object command.
        self.migrate_catalogue = QPushButton('Migrate IFC classification catalogue…')
        self.migrate_catalogue.setObjectName('opentrace_object_properties_migrate_catalogue')
        self.migrate_catalogue.clicked.connect(self._open_catalogue_migration)
        fields.addRow(self.migrate_catalogue)
        self.status = QLabel()
        self.status.setWordWrap(True)
        content.addWidget(self.status)
        # One real collapsible line, including Layer + IFC + classification.
        self.section = EditorSection(t("Layer / BIM / IFC"), body, collapsed=True)
        root.addWidget(self.section)

    def make_layer_combo(self, parent):
        combo = QComboBox(parent)
        combo.setObjectName("opentrace_object_layer")
        combo.setMinimumWidth(110)
        combo.setMaximumWidth(210)
        combo.setFocusPolicy(Qt.StrongFocus)
        combo.activated.connect(lambda _i, w=combo: self.assign_layer(w.currentData()))
        self._layer_combos.append(combo)
        return combo

    def _context(self):
        kind = creation_kind(self.app)
        entities = [] if kind else selected_entities(self.app.scene)
        return kind, entities

    def refresh(self):
        scene = self.app.scene
        kind, entities = self._context()
        defaults = creation_defaults(scene).get(kind, {})
        editable = scene.edit_group is None and (bool(kind) or bool(entities))
        editable = editable and all(scene.entity_selectable(e) for e in entities)
        values = {layer_of(e) for e in entities}
        chosen = defaults.get("layer", DEFAULT_LAYER) if kind else (next(iter(values)) if len(values) == 1 else None)
        names = [layer.name for layer in scene.layers]
        if chosen not in names and kind:
            chosen = DEFAULT_LAYER
        for combo in self._layer_combos:
            blocked = combo.blockSignals(True)
            combo.clear()
            if chosen is None and entities:
                combo.addItem(t("Vários layers"), None)
            for name in names:
                combo.addItem(name, name)
            combo.setCurrentIndex(combo.findData(chosen))
            combo.setEnabled(editable)
            combo.blockSignals(blocked)
        self.migrate_catalogue.setEnabled(self.suite.controllers.get('bim') is not None)
        group = entities[0] if len(entities) == 1 and entities[0] in scene.groups else None
        meta = defaults.get("ifc", {}) if kind else (getattr(group, "ifc", None) or {})
        from .bim import element_kind
        cls = KIND_TO_CLASS.get(kind) if kind else (meta.get("class") or KIND_TO_CLASS.get(element_kind(group), "IfcBuildingElementProxy" if group else None))
        from .bim import load_document_data
        from .bim_library import merged_library
        library = merged_library(load_document_data(self.app))["classifications"]
        # Do not replace a partially typed classification on cursor movements.
        signature = (kind, tuple(id(e) for e in entities), repr(meta), cls, editable,
                     len(library))
        if signature == self._signature:
            return
        self._signature = signature
        self.context.setText(t("New objects") if kind else t("Selected objects"))
        self.ifc_class.setText(cls or t("Not defined"))
        _old_predefined_signals = self.predefined.blockSignals(True)
        try:
            self.predefined.clear()
            if cls:
                self.predefined.addItems(predefined_types(cls))
                value = meta.get("predefined_type", DEFAULT_PREDEFINED.get(cls, "NOTDEFINED") if kind else "NOTDEFINED")
                self.predefined.setCurrentText(value)
        finally:
            self.predefined.blockSignals(_old_predefined_signals)
        from .ifc_catalog import default_internal_classification
        fallback = default_internal_classification(cls) if cls and not meta.get("classification_opt_out") else None
        system = str(meta.get("classification_system") or (fallback or {}).get("system") or "")
        code = str(meta.get("classification_code") or (fallback or {}).get("code") or "")
        self.system.setText(system)
        self.code.setText(code)
        # Layer remains editable even for objects without an IFC class.
        for field in (self.predefined, self.library, self.system, self.code, self.apply):
            field.setEnabled(editable and bool(cls))
        self.library.blockSignals(True)
        self.library.clear()
        self.library.addItem(t("No classification (optional)"), None)
        current = 0
        recommended = None
        for name, definition in library.items():
            if definition.get("system") == system and definition.get("code") == code:
                recommended = (name, definition)
                break
        if recommended is not None:
            self.library.addItem("✓ " + recommended[0], recommended[1])
            current = 1
            self.library.insertSeparator(self.library.count())
        for name, definition in sorted(library.items()):
            if recommended is not None and name == recommended[0]:
                continue
            self.library.addItem(name, definition)
        self.library.setCurrentIndex(current)
        self.library.blockSignals(False)
        assigned = [item for item in meta.get("classifications", [])
                    if isinstance(item, dict) and item.get("system") and item.get("code")]
        if assigned:
            self.status.setText("; ".join(f'{item["system"]}: {item["code"]}' for item in assigned))
        else:
            self.status.setText(("Internal IFC4 identity · external classification codes may be imported."
                                 if system == "OpenTrace BIM / IFC4" and code else
                                 "Classification: not defined" if not (system and code) else
                                 f"Classification: {system} · {code}"))

    def _open_catalogue_migration(self):
        controller = self.suite.controllers.get('bim')
        if controller is not None:
            controller.migrate_catalogue()
            self._signature = None
            self.refresh()

    def choose_classification(self, index):
        definition = self.library.itemData(index)
        if definition is None:
            self.system.clear()
            self.code.clear()
        else:
            self.system.setText(str(definition.get("system", "")))
            self.code.setText(str(definition.get("code", "")))
        self.apply_ifc()  # library selection is itself a committed user action

    def assign_layer(self, name):
        scene = self.app.scene
        if not name or scene.layer(name) is None:
            return
        kind, entities = self._context()
        if scene.edit_group is not None:
            return
        if kind:
            creation_defaults(scene).setdefault(kind, {})["layer"] = name
        elif entities and all(scene.entity_selectable(e) for e in entities):
            self.app.viewport.history.execute(AssignLayerCommand(entities, name))
            self.app.viewport.notify_scene_changed()
        self.refresh()
        self.app.viewport.setFocus()

    def apply_ifc(self, *_):
        kind, entities = self._context()
        system, code = self.system.text().strip(), self.code.text().strip()
        changes = {"predefined_type": self.predefined.currentText() or "NOTDEFINED",
                   "classification_system": system,
                   "classification_code": code,
                   "classification_opt_out": not bool(system or code)}
        if kind and self.app.scene.edit_group is None:
            creation_defaults(self.app.scene).setdefault(kind, {})["ifc"] = changes
        elif len(entities) == 1 and entities[0] in self.app.scene.groups and self.app.scene.entity_selectable(entities[0]):
            meta = ifc_identity_data(entities[0])
            meta.update(changes)
            if changes["classification_opt_out"]:
                meta["classifications"] = []
            previous = ifc_identity_data(entities[0])
            if meta != previous:
                set_ifc_metadata(self.app, entities[0], meta)
        self._signature = None
        self.refresh()
