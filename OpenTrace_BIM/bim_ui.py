# SPDX-License-Identifier: GPL-3.0-or-later
"""OpenTrace BIM project metadata and IFC export UI."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .bim import (ensure_spatial_ids, ifc_identity_data, load_document_data,
                  prepare_scene_identities, save_document_data, scan_scene,
                  set_ifc_metadata)
from .ifc_export import EXPORT_PROFILES, IfcExportError, export_ifc, normalize_export_schema
from .ifc_import import IfcImportError, import_ifc


class BimController:
    def __init__(self, app):
        self.app = app
        self.action = None
        self.data = load_document_data(app)
        self._document_source_signature = self._source_signature()
        self._refresh_queued = False
        self.panel = self._build_panel()
        try:
            app.viewport.sceneVersionChanged.connect(self.schedule_refresh)
        except Exception:
            pass
        try:
            app.on_document_changed(self._document_changed)
        except Exception:
            pass
        self.refresh()

    def _build_panel(self):
        w = QWidget()
        root = QVBoxLayout(w); root.setContentsMargins(8, 8, 8, 8); root.setSpacing(9)
        title = QLabel("<b style='font-size:14pt'>BIM / IFC</b><br><span style='color:#777'>openBIM semantics on top of OpenTrace parametric geometry.</span>")
        title.setWordWrap(True); root.addWidget(title)

        # Project information is one separate page in the master sidebar.
        # The same fields and document record remain authoritative for IFC.
        self.project_panel = QWidget()
        project_root = QVBoxLayout(self.project_panel)
        project_root.setContentsMargins(10, 10, 10, 10)
        project_root.setSpacing(9)
        project_heading = QLabel("<b style='font-size:14pt'>Project information</b>")
        project_root.addWidget(project_heading)
        from .panel_sections import EditorSection
        # The existing record fields stay exactly the same QObject instances.
        # Only their presentation is reorganized into the approved areas.
        self.project_name = QLineEdit()
        self.client = QLineEdit()
        self.location = QLineEdit()
        self.description = QLineEdit()
        self.author = QLineEdit()
        self.organization = QLineEdit()
        self.site_name = QLineEdit()
        self.building_name = QLineEdit()

        def project_section(title, rows):
            content=QWidget(self.project_panel)
            form=QFormLayout(content)
            form.setContentsMargins(0,0,0,0);form.setSpacing(7)
            form.setRowWrapPolicy(QFormLayout.WrapLongRows)
            for label, field in rows:
                form.addRow(label,field)
            section=EditorSection(title,content,parent=self.project_panel)
            project_root.addWidget(section)
            return section

        self.project_identity_section=project_section(
            "Identification",
            (("Project",self.project_name),("Client",self.client),
             ("Location",self.location),("Description",self.description)))
        self.project_people_section=project_section(
            "Responsible parties",
            (("Author",self.author),("Office / Organization",self.organization)))
        self.project_structure_section=project_section(
            "Project structure",
            (("IFC site",self.site_name),("IFC building",self.building_name)))
        self.project_levels_summary = QLabel()
        self.project_levels_summary.setWordWrap(True)
        project_root.addWidget(self.project_levels_summary)
        project_root.addStretch(1)

        options = QFrame(); options.setFrameShape(QFrame.StyledPanel)
        opt = QVBoxLayout(options); opt.setContentsMargins(8, 8, 8, 8); opt.setSpacing(5)
        opt.addWidget(QLabel("<b>IFC schema · independent of profile</b>"))
        schema_row = QHBoxLayout(); schema_row.addWidget(QLabel('IFC version'))
        self.export_schema = QComboBox()
        self.export_schema.addItem('IFC4 (stable)', 'IFC4')
        self.export_schema.addItem('IFC4.3 ADD2 (experimental · validate in target app)', 'IFC4X3_ADD2')
        self.export_schema.setToolTip('IFC4.3 ADD2: architectural subset under testing; not buildingSMART certified')
        schema_row.addWidget(self.export_schema, 1); opt.addLayout(schema_row)
        profile_row=QHBoxLayout();profile_row.addWidget(QLabel('Export profile'))
        self.export_profile=QComboBox()
        for key,cfg in EXPORT_PROFILES.items():self.export_profile.addItem(cfg["label"],key)
        profile_row.addWidget(self.export_profile,1);opt.addLayout(profile_row)
        self.profile_hint=QLabel();self.profile_hint.setWordWrap(True);self.profile_hint.setStyleSheet("color:#777;");opt.addWidget(self.profile_hint)

        # Keep file I/O immediately next to the active export profile: the user
        # can always see which compatibility strategy will be used before
        # pressing Export. Open/Import/Link live here too so all IFC ingress /
        # egress is one compact block.
        io_row=QHBoxLayout()
        self.open_btn=QPushButton("Open IFC…");self.import_btn=QPushButton("Import IFC…");self.link_btn=QPushButton("Link IFC…")
        io_row.addWidget(self.open_btn);io_row.addWidget(self.import_btn);io_row.addWidget(self.link_btn);opt.addLayout(io_row)
        export_row=QHBoxLayout()
        self.identify_btn=QPushButton("Prepare IFC identities")
        self.export_btn=QPushButton("Export IFC…")
        export_row.addWidget(self.identify_btn);export_row.addWidget(self.export_btn);opt.addLayout(export_row)
        self.advanced_btn=QPushButton('Advanced BIM · Psets · libraries · relationships · georeferencing…')
        opt.addWidget(self.advanced_btn)
        self.catalogue_status = QLabel('IFC catalogue: IFC4 built-in')
        self.catalogue_status.setWordWrap(True)
        opt.addWidget(self.catalogue_status)
        self.migrate_catalogue_btn = QPushButton('Migrate IFC classification catalogue…')
        self.migrate_catalogue_btn.setObjectName('opentrace_migrate_ifc_catalogue')
        self.migrate_catalogue_btn.setToolTip('Choose destination catalogue, compare equivalences, and review unresolved codes before committing the migration')
        opt.addWidget(self.migrate_catalogue_btn)
        self.manage_catalogue_btn = QPushButton('Manage / install classification catalogues…')
        opt.addWidget(self.manage_catalogue_btn)

        self.psets = QCheckBox('IFC Property Sets + OpenTrace parametrics')
        self.layers = QCheckBox('Materials and assemblies via IfcMaterialLayerSet')
        self.openings = QCheckBox('Openings as IfcOpeningElement + void relations')
        self.quantities = QCheckBox('IFC quantities (Qto_*) + imported quantities')
        self.styles = QCheckBox('IFC material appearances (color / transparency)')
        self.roundtrip = QCheckBox('OpenTrace parametric round-trip within IFC')
        self.repmaps = QCheckBox('RepresentationMap for repeated instances/components')
        opt.addWidget(self.psets); opt.addWidget(self.layers); opt.addWidget(self.openings); opt.addWidget(self.quantities);opt.addWidget(self.styles);opt.addWidget(self.roundtrip);opt.addWidget(self.repmaps)
        root.addWidget(options)

        self.summary = QLabel(); self.summary.setWordWrap(True); self.summary.setStyleSheet("color:#555;")
        root.addWidget(self.summary)

        element_box = QFrame(); element_box.setFrameShape(QFrame.StyledPanel)
        element_form = QFormLayout(element_box); element_form.setContentsMargins(8, 8, 8, 8); element_form.setSpacing(6)
        element_form.addRow(QLabel("<b>Elemento selecionado</b>"))
        self.element_class = QLabel("—"); self.element_guid = QLabel("—")
        self.element_name = QLineEdit(); self.element_type = QLineEdit(); self.element_predefined = QComboBox()
        self.classification_system = QLineEdit(); self.classification_code = QLineEdit()
        self.common_reference = QLineEdit(); self.common_status = QComboBox()
        self.common_status.addItem('Not defined', None)
        for code, label in (("NEW", "New"), ("EXISTING", "Existing"), ("DEMOLISH", "To demolish"), ("TEMPORARY", "Temporary")):
            self.common_status.addItem(label, code)
        self.common_external = QComboBox(); self.common_loadbearing = QComboBox()
        for combo in (self.common_external, self.common_loadbearing):
            combo.addItem('Not defined', None); combo.addItem("Yes", True); combo.addItem('No', False)
        self.common_fire = QLineEdit()
        element_form.addRow("IFC class", self.element_class); element_form.addRow("GlobalId", self.element_guid)
        element_form.addRow('IFC name', self.element_name); element_form.addRow("Type", self.element_type)
        element_form.addRow("PredefinedType", self.element_predefined)
        element_form.addRow('Primary classification', self.classification_system); element_form.addRow('Primary code', self.classification_code)
        self.classification_browser_btn = QPushButton('Search and assign codes · multiple systems…')
        element_form.addRow('', self.classification_browser_btn)
        element_form.addRow(QLabel('<b>Common IFC properties</b>'))
        element_form.addRow("Reference", self.common_reference); element_form.addRow("Status", self.common_status)
        element_form.addRow("External", self.common_external); element_form.addRow("Load bearing", self.common_loadbearing)
        element_form.addRow("Fire rating", self.common_fire)
        self.apply_element_btn = QLabel("Changes are saved on Enter, focus change or option selection.")
        self.apply_element_btn.setWordWrap(True)
        element_form.addRow(self.apply_element_btn); root.addWidget(element_box)
        info = QLabel(
            'Shapes are exported from already-resolved OpenTrace geometry. Curves, inclinations, profiles, holes and junctions are not rebuilt by the Bonsai wall modeller.'
        )
        info.setWordWrap(True); info.setStyleSheet("color:#777;"); root.addWidget(info)

        self.status = QLabel('IFC4 stable / IFC4.3 experimental · profile-based export')
        self.status.setWordWrap(True); self.status.setStyleSheet("color:#666;"); root.addWidget(self.status)
        root.addStretch(1)

        for edit in (self.project_name, self.client, self.location, self.site_name, self.building_name, self.author, self.organization, self.description):
            edit.editingFinished.connect(self.save)
        for check in (self.psets, self.layers, self.openings, self.quantities, self.styles, self.roundtrip, self.repmaps):
            check.toggled.connect(self.save)
        self.export_profile.currentIndexChanged.connect(self.profile_changed)
        self.export_schema.currentIndexChanged.connect(self.schema_changed)
        self.open_btn.clicked.connect(lambda:self._choose_ifc("open",False))
        self.import_btn.clicked.connect(lambda:self._choose_ifc("import",False))
        self.link_btn.clicked.connect(lambda:self._choose_ifc("import",True))
        self.identify_btn.clicked.connect(self.prepare_identities)
        self.export_btn.clicked.connect(self.export)
        self.advanced_btn.clicked.connect(self.open_advanced)
        self.migrate_catalogue_btn.clicked.connect(self.migrate_catalogue)
        self.manage_catalogue_btn.clicked.connect(self.manage_catalogues)
        self.classification_browser_btn.clicked.connect(self.open_classification_browser)
        for field in (self.element_name, self.element_type, self.classification_system,
                      self.classification_code, self.common_reference, self.common_fire):
            field.editingFinished.connect(self.apply_selected_metadata)
        for combo in (self.element_predefined, self.common_status,
                      self.common_external, self.common_loadbearing):
            combo.activated.connect(self.apply_selected_metadata)
        return w

    def manage_catalogues(self):
        from .classification_catalogue_dialog import CatalogueSourcesDialog
        from .classification_assignments import extend_project_catalogue
        from .bim import save_document_data
        dlg = CatalogueSourcesDialog([], self.panel)
        if not dlg.exec():
            return
        try:
            newdata = load_document_data(self.app)
            # Validate all before committing any of them to the project.
            for catalogue in dlg.catalogues:
                newdata = extend_project_catalogue(newdata, catalogue)
            self.data = save_document_data(self.app, newdata)
            self.refresh()
        except (TypeError, ValueError, OSError) as exc:
            QMessageBox.warning(self.panel, 'Catalogues not installed', str(exc))

    def open_classification_browser(self):
        group = self._selected_group()
        if group is None:
            QMessageBox.information(self.panel, 'Classifications', 'Select exactly one BIM object to classify it.')
            return
        from .classification_catalogue_dialog import ObjectClassificationDialog
        dlg = ObjectClassificationDialog(self.app, group, load_document_data(self.app), self.panel)
        if dlg.exec():
            self.refresh_selected()

    def migrate_catalogue(self):
        from .catalogue_migration_dialog import CatalogueMigrationDialog
        dlg = CatalogueMigrationDialog(self.app, self.panel)
        if dlg.exec():
            self.data = load_document_data(self.app)
            self.refresh()

    def open_advanced(self):
        try:
            from .bim_advanced_ui import BimAdvancedDialog
            dlg=BimAdvancedDialog(self,self.panel);dlg.exec();self.data=load_document_data(self.app);self.refresh()
        except Exception as exc:
            QMessageBox.critical(self.panel,"OpenTrace BIM",f"Could not open the advanced BIM editor:\n{type(exc).__name__}: {exc}")

    def _source_signature(self):
        # IngeTrazo replaces plugin_data[key] when its BIM data changes, but
        # keeps that same dict object when only geometry/selection changes.
        # Reading this identity avoids a JSON roundtrip of 15k codes on every
        # new wall, slab or mouse selection. Never mutate the host-owned dict.
        scene = self.app.scene
        data = getattr(scene, 'plugin_data', {}) or {}
        return (id(scene), id(data.get(getattr(self.app, 'key', ''), None)))

    def _document_changed(self):
        signature = self._source_signature()
        if signature == self._document_source_signature:
            self.refresh_selected()
            self.schedule_refresh()
            return
        self._document_source_signature = signature
        self.data = load_document_data(self.app)
        self.refresh()

    def schedule_refresh(self, *_):
        if self._refresh_queued:
            return
        self._refresh_queued = True
        QTimer.singleShot(0, self._run_refresh)

    def _run_refresh(self):
        self._refresh_queued = False
        self.refresh_counts()

    def refresh(self):
        setup = self.data.get('project_setup') or {}
        pending = setup.get('migration_pending') or []
        self.catalogue_status.setText(
            'IFC catalogue: ' + str(setup.get('catalogue_name') or 'IFC4 built-in')
            + (f' · {len(pending)} pending migrations' if pending else ''))
        project = self.data.get("project", {})
        export = self.data.get("export", {})
        mapping = (
            (self.project_name, project.get("name", "")), (self.client, project.get("client", "")),
            (self.location, project.get("location", "")), (self.site_name, project.get("site", "")),
            (self.building_name, project.get("building", "")), (self.author, project.get("author", "")),
            (self.organization, project.get("organization", "")), (self.description, project.get("description", "")),
        )
        for widget, value in mapping:
            old = widget.blockSignals(True); widget.setText(str(value or "")); widget.blockSignals(old)
        try:
            from .levels import available_levels
            level_names = [lv["name"] for lv in available_levels(self.app)]
            self.project_levels_summary.setText(
                "Pavimentos vinculados aos Níveis: " + (", ".join(level_names) if level_names else "nenhum nível cadastrado")
            )
        except Exception:
            self.project_levels_summary.setText("Storeys: level data unavailable.")
        old=self.export_schema.blockSignals(True)
        idx=self.export_schema.findData(str(export.get('schema') or 'IFC4'))
        self.export_schema.setCurrentIndex(idx if idx >= 0 else 0)
        self.export_schema.blockSignals(old)
        old=self.export_profile.blockSignals(True);idx=self.export_profile.findData(str(export.get("profile") or "bonsai"));self.export_profile.setCurrentIndex(idx if idx>=0 else 0);self.export_profile.blockSignals(old)
        for widget, key in ((self.psets, "include_property_sets"), (self.layers, "include_material_layers"), (self.openings, "include_opening_relations"), (self.quantities, "include_quantities"), (self.styles,"include_styles"),(self.roundtrip,"include_parametric_roundtrip"),(self.repmaps,"use_representation_maps")):
            old = widget.blockSignals(True); widget.setChecked(bool(export.get(key, True))); widget.blockSignals(old)
        self._update_profile_ui()
        self.refresh_counts()
        self.refresh_selected()
        # Host-neutral creation commands read this session cache. It is
        # reconstructed from the saved .igz on each document change/reopen.
        from .project_setup import catalogue_from_document
        # A class catalogue can have >15,000 entries. Keep the scene-local
        # index across object creation / BIM refresh, rebuilding only when the
        # chosen catalogue or project's classifications change.
        keys = setup.get('catalogue_keys') or []
        library = self.data.get('libraries', {}).get('classifications', {})
        catalogue_key = (self._source_signature(),
                         self.data.get('spatial_ids', {}).get('project'),
                         setup.get('catalogue_id'),
                         setup.get('primary_classification_system'),
                         len(library), tuple(keys))
        if getattr(self, '_creation_catalogue_key', None) != catalogue_key:
            self.app.scene._opentrace_catalogue_for_creation = catalogue_from_document(self.data)
            self._creation_catalogue_key = catalogue_key
        # Choose small preset lists once per setup, not every viewport event.
        collection_key = (self._source_signature(),
                          self.data.get('spatial_ids', {}).get('project'),
                          setup.get('library_selection_mode'),
                          tuple((p.get('id'), len(p.get('resources', ())))
                                for p in setup.get('resource_libraries', ())
                                if isinstance(p, dict)))
        if getattr(self, '_resource_collection_key', None) != collection_key:
            from .preset_catalog import set_active_collections
            set_active_collections(self.data)
            self._resource_collection_key = collection_key

    def _selected_group(self):
        scene = self.app.scene
        if getattr(scene, "edit_group", None) is not None:
            return None
        found = []
        from .bim import element_kind
        for item in list(getattr(scene, "selection", ()) or ()):
            group = getattr(item, "owner", None) or item
            if group in getattr(scene, "groups", ()) and element_kind(group) and group not in found:
                found.append(group)
        return found[0] if len(found) == 1 else None

    def refresh_selected(self):
        group = self._selected_group()
        if group is None:
            self.element_class.setText("—"); self.element_guid.setText("—")
            for widget in (self.element_name, self.element_type, self.classification_system, self.classification_code, self.common_reference, self.common_fire):
                old = widget.blockSignals(True); widget.clear(); widget.setEnabled(False); widget.blockSignals(old)
            old = self.element_predefined.blockSignals(True); self.element_predefined.clear(); self.element_predefined.setEnabled(False); self.element_predefined.blockSignals(old)
            for combo in (self.common_status, self.common_external, self.common_loadbearing):
                old = combo.blockSignals(True); combo.setCurrentIndex(0); combo.setEnabled(False); combo.blockSignals(old)
            self.apply_element_btn.setEnabled(False); self.classification_browser_btn.setEnabled(False); return
        from .bim import KIND_TO_CLASS, element_kind
        raw_meta = getattr(group, "ifc", None)
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        ifc_class = str(meta.get("class") or KIND_TO_CLASS.get(element_kind(group)) or "IfcBuildingElementProxy")
        self.element_class.setText(ifc_class); self.element_guid.setText(str(meta.get("global_id") or "Pendente — use Preparar identidades IFC"))
        from .ifc_catalog import predefined_types
        values = predefined_types(ifc_class)
        old = self.element_predefined.blockSignals(True); self.element_predefined.clear(); self.element_predefined.addItems(values)
        current = str(meta.get("predefined_type") or "NOTDEFINED").upper()
        idx = self.element_predefined.findText(current); self.element_predefined.setCurrentIndex(idx if idx >= 0 else self.element_predefined.findText("NOTDEFINED")); self.element_predefined.setEnabled(True); self.element_predefined.blockSignals(old)
        for widget, value in ((self.element_name, meta.get("name", "")), (self.element_type, meta.get("type_name", "")), (self.classification_system, meta.get("classification_system", "")), (self.classification_code, meta.get("classification_code", ""))):
            old = widget.blockSignals(True); widget.setText(str(value or "")); widget.setEnabled(True); widget.blockSignals(old)
        common = meta.get("common") if isinstance(meta.get("common"), dict) else {}
        old = self.common_reference.blockSignals(True); self.common_reference.setText(str(common.get("Reference") or "")); self.common_reference.setEnabled(True); self.common_reference.blockSignals(old)
        old = self.common_fire.blockSignals(True); self.common_fire.setText(str(common.get("FireRating") or "")); self.common_fire.setEnabled(True); self.common_fire.blockSignals(old)
        for combo, key in ((self.common_status, "Status"), (self.common_external, "IsExternal"), (self.common_loadbearing, "LoadBearing")):
            old = combo.blockSignals(True); combo.setEnabled(True)
            wanted = common.get(key, None); idx = combo.findData(wanted); combo.setCurrentIndex(idx if idx >= 0 else 0); combo.blockSignals(old)
        self.apply_element_btn.setEnabled(True)
        self.classification_browser_btn.setEnabled(True)

    def apply_selected_metadata(self, *_):
        group = self._selected_group()
        if group is None:
            return
        meta = ifc_identity_data(group)
        meta["name"] = self.element_name.text().strip() or getattr(group, "name", None) or meta.get("class")
        meta["type_name"] = self.element_type.text().strip() or meta.get("type_name")
        meta["predefined_type"] = self.element_predefined.currentText().strip().upper() or "NOTDEFINED"
        meta["classification_system"] = self.classification_system.text().strip()
        meta["classification_code"] = self.classification_code.text().strip()
        # Never erase classification references for the other loaded systems.
        # Explicitly edited principal is retained as an additional reference.
        from .classification_assignments import add_reference
        if meta["classification_system"] and meta["classification_code"]:
            meta = add_reference(meta, {
                'system': meta['classification_system'],
                'code': meta['classification_code'],
            }, primary=True)
        common = {
            "Reference": self.common_reference.text().strip() or None,
            "Status": self.common_status.currentData(),
            "IsExternal": self.common_external.currentData(),
            "LoadBearing": self.common_loadbearing.currentData(),
            "FireRating": self.common_fire.text().strip() or None,
        }
        meta["common"] = {k: v for k, v in common.items() if v is not None}
        if meta != ifc_identity_data(group):
            set_ifc_metadata(self.app, group, meta)
            self.status.setText("Element BIM data updated.")
            self.refresh_selected()

    def refresh_counts(self):
        stats = scan_scene(self.app.scene)
        c = stats["counts"]
        self.summary.setText(
            f"BIM elements in document: <b>{stats['total']}</b> · "
            f"{c.get('wall',0)} walls · {c.get('slab',0)} slabs · {c.get('beam',0)} beams · {c.get('column',0)} columns · "
            f"{c.get('space',0)} spaces · {c.get('roof',0)} roofs · {c.get('door',0)} doors · {c.get('window',0)} windows. "
            f"Composites: {stats['composite']} · parametric openings: {stats['openings']} · "
            f"imported/reference IFC: {stats.get('imported',0)} (linked: {stats.get('linked',0)})."
        )
        self.export_btn.setEnabled(stats["total"] > 0)
        self.refresh_selected()

    def save(self, *_):
        # Merge instead of replacing the whole record: unknown project
        # fields from a future release or imported BIM remain preserved.
        project = dict(self.data.get("project") or {})
        project.update({
            "name": self.project_name.text().strip(),
            "client": self.client.text().strip(),
            "location": self.location.text().strip(),
            "site": self.site_name.text().strip(),
            "building": self.building_name.text().strip(),
            "author": self.author.text().strip(),
            "organization": self.organization.text().strip(),
            "description": self.description.text().strip(),
        })
        self.data["project"] = project
        self.data["export"] = {
            "schema": self.export_schema.currentData() or "IFC4", "profile": self.export_profile.currentData() or "bonsai", "include_property_sets": self.psets.isChecked(),
            "include_material_layers": self.layers.isChecked(),
            "include_opening_relations": self.openings.isChecked(),
            "include_quantities": self.quantities.isChecked(),
            "include_styles": self.styles.isChecked(),
            "include_parametric_roundtrip": self.roundtrip.isChecked(),
            "use_representation_maps": self.repmaps.isChecked(),
        }
        try:
            try:
                from .levels import available_levels
                levels = available_levels(self.app)
                names = [str(x.get("name") or "") for x in levels if isinstance(x, dict)]
            except Exception:
                names = ["Pavimento 0"]
            ensure_spatial_ids(self.data, names or ["Pavimento 0"])
            self.data = save_document_data(self.app, self.data)
        except Exception as exc:
            self.status.setText(f"Could not save BIM data: {type(exc).__name__}: {exc}")

    def _update_profile_ui(self):
        key=self.export_profile.currentData() or "bonsai"
        cfg=EXPORT_PROFILES.get(key,EXPORT_PROFILES["bonsai"])
        compat=key!="opentrace"
        self.openings.setEnabled(not compat)
        if compat:
            old=self.openings.blockSignals(True);self.openings.setChecked(False);self.openings.blockSignals(old)
            if key=="bonsai":
                self.profile_hint.setText("Bonsai / Blender: complete Body + Axis contexts, native solids when safe, and BRep for the remainder. OpenTrace walls are not advertised as Bonsai-editable DumbLayer2 elements.")
            elif key=="archicad":
                self.profile_hint.setText("Archicad: prioritizes SweptSolid, IFC axes and native compositions for architectural conversion; advanced shapes preserve geometry as BRep.")
            else:
                self.profile_hint.setText("Revit: prioritizes SweptSolid, IFC axes and standard types/materials; shapes that cannot be represented as an extrusion remain BRep to preserve form.")
        else:
            self.profile_hint.setText("OpenTrace fidelity: IFC4 PolygonalFaceSet with optional IfcOpeningElement relations. Useful for openBIM inspection and future round-trip workflows.")

    def profile_changed(self,*_):
        self._update_profile_ui();self.save()

    def schema_changed(self, *_):
        self.save()

    def _choose_ifc(self,mode,linked):
        title="Open IFC as project" if mode=="open" else ("Link IFC" if linked else "Import IFC")
        filename,_=QFileDialog.getOpenFileName(self.panel,title,"","Industry Foundation Classes (*.ifc)")
        if not filename:return
        if mode=="open" and list(getattr(self.app.scene,"groups",()) or ()):
            answer=QMessageBox.question(self.panel,"OpenTrace BIM","Opening this IFC will replace the elements in the current document (the operation is undoable). Continue?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if answer!=QMessageBox.Yes:return
        try:
            result=import_ifc(self.app,Path(filename),mode=mode,linked=linked)
            if linked:
                links=list(self.data.get("links",[]) or []);links.append({"path":str(filename),"mode":"linked"});self.data["links"]=links
            if mode=="open":
                proj=result.get("project",{})
                for widget,key in ((self.project_name,"name"),(self.site_name,"site"),(self.building_name,"building")):
                    if proj.get(key):widget.setText(str(proj[key]))
            self.save();self.refresh_counts()
            skipped=int(result.get("unsupported",0) or 0)
            kind="linked" if linked else ("opened" if mode=="open" else "imported")
            unit=float(result.get("unit_scale",1.0) or 1.0);reader=str(result.get("reader") or "")
            unit_msg=(f" · file units converted to metres (×{unit:g})" if abs(unit-1.0)>1e-12 else "")
            self.status.setText(f"IFC {kind}: {len(result['groups'])} element(s) with compatible geometry"+(f" · {skipped} unsupported representation(s)" if skipped else "")+unit_msg+(f" · reader {reader}" if reader else "")+".")
        except IfcImportError as exc:QMessageBox.warning(self.panel,"OpenTrace BIM",str(exc))
        except Exception as exc:QMessageBox.critical(self.panel,"OpenTrace BIM",f"Could not read IFC:\n{type(exc).__name__}: {exc}")

    def prepare_identities(self):
        try:
            changed = prepare_scene_identities(self.app)
            self.status.setText(f"IFC identities prepared. {changed} element(s) received or migrated BIM metadata.")
        except Exception as exc:
            QMessageBox.critical(self.panel, "OpenTrace BIM", f"Could not prepare IFC identities:\n{type(exc).__name__}: {exc}")

    def export(self):
        self.save()
        default_name = (self.project_name.text().strip() or "OpenTrace_BIM").replace("/", "-").replace("\\", "-") + ".ifc"
        filename, _ = QFileDialog.getSaveFileName(self.panel, "Export OpenTrace BIM", default_name, "Industry Foundation Classes (*.ifc)")
        if not filename:
            return
        if not filename.lower().endswith(".ifc"):
            filename += ".ifc"
        try:
            changed = prepare_scene_identities(self.app)
            result = export_ifc(self.app, Path(filename), data=self.data)
            reps=result.get("representations",{})
            self.status.setText(
                f"IFC exported ({result.get('profile','')}): {result['elements']} elements · {result['openings']} semantic openings · "
                f"{result['storeys']} storeys · {result['types']} types · "
                f"{reps.get('SweptSolid',0)} SweptSolid / {reps.get('Brep',0)} BRep / {reps.get('Tessellation',0)} Tessellation."
            )
            QMessageBox.information(self.panel, "OpenTrace BIM", f"IFC4 exported successfully.\n\n{filename}")
        except IfcExportError as exc:
            QMessageBox.warning(self.panel, "OpenTrace BIM", str(exc))
        except Exception as exc:
            QMessageBox.critical(self.panel, "OpenTrace BIM", f"Could not export IFC:\n{type(exc).__name__}: {exc}")
