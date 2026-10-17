# SPDX-License-Identifier: GPL-3.0-or-later
"""Built-in and personal architectural presets for model elements.

This library is deliberately host-light: presets are plain dictionaries and can
later be shared by the IngeTrazo, Blender/Bonsai and FreeCAD adapters.
"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from .layers import normalize_layers, total_thickness
from .i18n import t
from .library_display import builtin_name, folder_label

SETTINGS_KEY = "arquitetura_parametrica/element_presets_v2"
FILE_FORMAT = "parametric-architecture-preset"
FILE_VERSION = 1
_BUILTIN_PRESETS = None


def _layer(name, thickness, function="finish", role="finish", material=None):
    return {
        "id": uuid.uuid4().hex[:12], "name": name, "role": role,
        "function": function, "thickness": float(thickness),
        "material_name": material,
    }


def _composite(rows):
    layers=[]
    for row in rows:
        if len(row)==3:
            name,t,function=row; role="finish"
        else:
            name,t,function,role=row
        layers.append(_layer(name,t,function,role))
    layers=normalize_layers(layers)
    return {"structure":"composite", "layers":layers,
            "thickness":total_thickness(layers), "material_name":None}


def _p(pid, name, config, group, description=""):
    return {"id":f"builtin:{pid}","name":name,"kind":pid.split(":",1)[0],
            "group":group,"description":description,"builtin":True,
            "config":copy.deepcopy(config),"revision":1}


def builtins():
    global _BUILTIN_PRESETS
    if _BUILTIN_PRESETS is not None:
        return copy.deepcopy(_BUILTIN_PRESETS)
    wall=[]
    wall.append(_p("wall:generic10","Generic · 10 cm",
                   {"structure":"simple","thickness":0.10,"material_name":None},
                   "Generic","Starter simple wall."))
    for tag,core,name in (("cer9",.09,"Clay block 9 + render"),
                          ("cer115",.115,"Clay block 11.5 + render"),
                          ("cer14",.14,"Clay block 14 + render"),
                          ("con9",.09,"Concrete block 9 + render"),
                          ("con14",.14,"Concrete block 14 + render")):
        wall.append(_p(f"wall:{tag}",name,_composite([
            ("Exterior render",.015,"finish"),
            (("Concrete block" if tag.startswith("con") else "Clay block"),core,"structure","core"),
            ("Interior render",.015,"finish"),
        ]),"Masonry"))
    wall.append(_p("wall:cer9_tile1","Clay block 9 + tile on one side",_composite([
        ("Exterior render",.015,"finish"),("Clay block",.09,"structure","core"),
        ("Interior base plaster",.015,"substrate"),("Tile adhesive",.005,"bonding"),
        ("Ceramic tile",.009,"finish"),
    ]),"Clad masonry"))
    wall.append(_p("wall:cer14_tile2","Clay block 14 + tile on both sides",_composite([
        ("Exterior ceramic tile",.009,"finish"),("Exterior tile adhesive",.005,"bonding"),
        ("Exterior base plaster",.015,"substrate"),("Clay block",.14,"structure","core"),
        ("Interior base plaster",.015,"substrate"),("Interior tile adhesive",.005,"bonding"),
        ("Interior ceramic tile",.009,"finish"),
    ]),"Clad masonry"))
    # Expanded ready-to-use masonry; each physical band receives a visible
    # default material below, without baking colors into user-created presets.
    for tag, name, core_name, thickness in (
        ('clay_brick_10','Exposed clay brick · 10 cm','Clay brick',.10),
        ('clay_brick_15','Exposed clay brick · 15 cm','Clay brick',.15),
        ('clay_block_14_bare','Exposed clay block · 14 cm','Clay block',.14),
        ('clay_block_19_bare','Exposed clay block · 19 cm','Clay block',.19),
        ('struct_con_14','Structural concrete block · 14 cm','Structural concrete block',.14),
        ('struct_con_19','Structural concrete block · 19 cm','Structural concrete block',.19),
        ('struct_con_20','Structural concrete block · 20 cm','Structural concrete block',.20),
    ):
        wall.append(_p('wall:'+tag,name,_composite([
            (core_name,thickness,'structure','core'),
        ]),'Exposed masonry' if 'Structural' not in name else 'Structural masonry'))
    wall.append(_p('wall:brick_render','Clay brick + render on both sides',_composite([
        ('Exterior render',.015,'finish'),('Clay brick',.10,'structure','core'),
        ('Interior render',.015,'finish'),
    ]),'Masonry'))
    wall.append(_p('wall:struct_con19_render','Structural concrete block 19 + render',_composite([
        ('Exterior render',.015,'finish'),('Structural concrete block',.19,'structure','core'),
        ('Interior render',.015,'finish'),
    ]),'Structural masonry'))
    wall.append(_p('wall:clay19_render','Clay block 19 + render',_composite([
        ('Exterior render',.015,'finish'),('Clay block',.19,'structure','core'),
        ('Interior render',.015,'finish'),
    ]),'Masonry'))
    wall.append(_p('wall:wet_con14','Concrete block 14 + wet-area tile',_composite([
        ('Exterior render',.015,'finish'),('Concrete block',.14,'structure','core'),
        ('Interior base plaster',.015,'substrate'),('Interior tile adhesive',.005,'bonding'),
        ('Interior ceramic tile',.009,'finish'),
    ]),'Clad masonry'))
    wall.append(_p('wall:dry95_insulated','Insulated drywall 95 mm',_composite([
        ('Exterior gypsum board',.0125,'finish'),
        ('70 mm stud + mineral insulation',.070,'insulation','core'),
        ('Interior gypsum board',.0125,'finish'),
    ]),'Drywall'))

    wall.append(_p("wall:dry95","Drywall 95 mm",_composite([
        ("Exterior gypsum board",.0125,"finish"),("70 mm stud",.070,"technical","core"),
        ("Interior gypsum board",.0125,"finish"),
    ]),"Drywall"))
    wall.append(_p("wall:dry120","Double drywall 120 mm",_composite([
        ("Exterior gypsum board 1",.0125,"finish"),("Exterior gypsum board 2",.0125,"finish"),
        ("70 mm stud + insulation",.070,"insulation","core"),
        ("Interior gypsum board 1",.0125,"finish"),("Interior gypsum board 2",.0125,"finish"),
    ]),"Drywall"))

    slab=[]
    slab.append(_p("slab:generic12","Generic · 12 cm",
                   {"structure":"simple","thickness":.12,"material_name":None},"Generic"))
    slab.append(_p("slab:concrete12","Exposed reinforced concrete · 12 cm",
                   _composite([("Reinforced concrete",.12,"structure","core")]),"Structural"))
    slab.append(_p("slab:floor10","Concrete 10 + screed + porcelain tile",_composite([
        ("Reinforced concrete",.10,"structure","core"),("Screed",.04,"substrate"),
        ("Tile adhesive",.005,"bonding"),("Porcelain tile",.010,"finish"),
    ]),"Floors"))
    slab.append(_p("slab:floor12","Concrete 12 + screed + porcelain tile",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Screed",.04,"substrate"),
        ("Tile adhesive",.005,"bonding"),("Porcelain tile",.010,"finish"),
    ]),"Floors"))
    slab.append(_p("slab:wood","Concrete 12 + acoustic layer + timber floor",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Acoustic underlay",.005,"insulation"),
        ("Screed",.04,"substrate"),("Timber flooring",.015,"finish"),
    ]),"Floors"))
    slab.append(_p("slab:wet","Waterproofed wet area",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Leveling / falls",.03,"substrate"),
        ("Waterproofing",.004,"waterproofing"),("Tile adhesive",.005,"bonding"),
        ("Ceramic tile",.010,"finish"),
    ]),"Wet areas"))
    slab.append(_p("slab:roof","Waterproofed roof",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Leveling / falls",.03,"substrate"),
        ("Waterproofing",.004,"waterproofing"),("Protection screed",.04,"substrate"),
    ]),"Roofs"))
    slab.append(_p("slab:inverted","Insulated inverted roof",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Leveling / falls",.03,"substrate"),
        ("Waterproofing",.004,"waterproofing"),("XPS thermal insulation",.05,"insulation"),
        ("Protection screed",.04,"substrate"),
    ]),"Roofs"))
    slab.append(_p("slab:green","Basic green roof",_composite([
        ("Reinforced concrete",.12,"structure","core"),("Leveling / falls",.03,"substrate"),
        ("Root-resistant waterproofing",.005,"waterproofing"),("Drainage layer",.025,"technical"),
        ("Planting substrate",.15,"other"),
    ]),"Roofs"))

    beam=[]
    for w,h in ((.15,.30),(.20,.40),(.20,.50),(.20,.60),(.25,.60),(.30,.60)):
        beam.append(_p(f"beam:concrete:{int(w*100)}x{int(h*100)}",
            f"Reinforced concrete · {int(w*100)} × {int(h*100)} cm",
            {"section_type":"simple","profile":"rect","width":w,"height":h,
             "diameter":min(w,h),"material_name":None},"Reinforced concrete"))
    for w,h in ((.05,.15),(.06,.20),(.08,.20),(.10,.30)):
        beam.append(_p(f"beam:wood:{int(w*100)}x{int(h*100)}",
            f"Timber · {int(w*100)} × {int(h*100)} cm",
            {"section_type":"simple","profile":"rect","width":w,"height":h,
             "diameter":min(w,h),"material_name":None},"Timber"))
    for code in ("W 150 x 13,0","W 200 x 19,3","W 250 x 22,3","W 310 x 28,3","W 360 x 32,9",
                 "IPE 160","IPE 200","IPE 240","HEA 200","HEB 200"):
        family="gerdau_w" if code.startswith("W ") else code.split()[0].lower()
        slug=code.lower().replace(" ","").replace(",",".").replace("/","-")
        beam.append(_p(f"beam:steel:{slug}",f"Steel · {code}",
            {"section_type":"complex","profile_ref":f"builtin:steel:{family}:{slug}","material_name":None},
            "Steel"))

    column=[]
    for w,d in ((.20,.20),(.20,.30),(.25,.25),(.30,.30),(.30,.40)):
        column.append(_p(f"column:concrete:{int(w*100)}x{int(d*100)}",
            f"Concrete · {int(w*100)} × {int(d*100)} cm",
            {"section_type":"simple","profile":"rect","width":w,"depth":d,
             "diameter":min(w,d),"material_name":None,"stations":None},"Reinforced concrete"))
    for side in (.15,.20):
        column.append(_p(f"column:wood:{int(side*100)}",
            f"Timber · {int(side*100)} × {int(side*100)} cm",
            {"section_type":"simple","profile":"rect","width":side,"depth":side,
             "diameter":side,"material_name":None,"stations":None},"Timber"))
    for code in ("HEA 160","HEA 200","HEB 200"):
        family=code.split()[0].lower(); slug=code.lower().replace(" ","")
        column.append(_p(f"column:steel:{slug}",f"Steel · {code}",
            {"section_type":"complex","profile_ref":f"builtin:steel:{family}:{slug}",
             "material_name":None,"stations":None},"Steel"))

    # Give BUILT-IN wall composites ready-to-render starter appearances for
    # each physical layer. This is opt-in by choosing the preset; never alter
    # old projects or personalized material choices on re-open.
    from .materials import default_wall_layer_material
    for preset in wall:
        cfg = preset.get("config", {})
        if cfg.get("structure") != "composite":
            continue
        for layer in cfg.get("layers", ()):
            if not layer.get("material_name"):
                layer["material_name"] = default_wall_layer_material(layer)

    _BUILTIN_PRESETS={"wall":wall,"slab":slab,"beam":beam,"column":column}
    return copy.deepcopy(_BUILTIN_PRESETS)


def load_personal():
    raw=QSettings().value(SETTINGS_KEY,"{}")
    try:data=json.loads(str(raw or "{}"))
    except Exception:data={}
    if not isinstance(data,dict):data={}
    return {k:[x for x in v if isinstance(x,dict)] for k,v in data.items() if isinstance(v,list)}


def save_personal(data):
    QSettings().setValue(SETTINGS_KEY,json.dumps(data,ensure_ascii=False,separators=(",",":")))


def personal_for(kind): return copy.deepcopy(load_personal().get(kind,[]))


# A None selection means a legacy project: preserve its preexisting behavior.
# Only new opt-in resource collections restrict the quick-tool preset lists.
_ACTIVE_COLLECTIONS = None


def set_active_collections(project):
    global _ACTIVE_COLLECTIONS
    setup = project.get('project_setup', {}) if isinstance(project, dict) else {}
    records = setup.get('resource_libraries', ()) if isinstance(setup, dict) else ()
    if not isinstance(records, list) or (
            setup.get('library_selection_mode') != 'curated' and
            not any(isinstance(p, dict) and
                    p.get('format') == 'opentrace-resource-collection' for p in records)):
        _ACTIVE_COLLECTIONS = None
        return
    from .resource_collections import validate_collection
    selections=[]
    for pack in records:
        try:
            selections.append(validate_collection(pack))
        except (TypeError, ValueError):
            continue
    _ACTIVE_COLLECTIONS=selections


def all_for(kind):
    # The master catalog stays intact and browseable in LibraryManagerDialog.
    # The quick list only contains recipes explicitly loaded for this project.
    personal = personal_for(kind)
    if _ACTIVE_COLLECTIONS is None:
        return copy.deepcopy(builtins().get(kind, [])) + personal
    keys = {}
    for collection in _ACTIVE_COLLECTIONS:
        for rec in collection['resources']:
            if rec['kind'] != kind:
                continue
            data = rec.get('data', {})
            if not isinstance(data, dict) or not data.get('config'):
                continue
            # Preserve original preset ID: a re-opened project sees the same
            # resource identity and existing modeled elements are untouched.
            keys[str(data.get('id') or rec['id'])] = copy.deepcopy(data)
    for rec in personal:
        keys[str(rec.get('id'))] = rec
    return list(keys.values())


def _clean_name(value): return " ".join(str(value or "").split())


def upsert_personal(kind,preset):
    data=load_personal(); items=data.setdefault(kind,[]); item=copy.deepcopy(preset)
    item["id"]=str(item.get("id") or uuid.uuid4().hex); item["kind"]=kind;item["builtin"]=False
    item["name"]=_clean_name(item.get("name") or "Preset") or "Preset"
    item["revision"]=max(1,int(item.get("revision",1) or 1))
    for i,old in enumerate(items):
        if str(old.get("id"))==item["id"]:items[i]=item;break
    else:items.append(item)
    save_personal(data);return copy.deepcopy(item)


def delete_personal(kind,pid):
    data=load_personal();data[kind]=[x for x in data.get(kind,[]) if str(x.get("id"))!=str(pid)];save_personal(data)


def _source_values(kind, controller):
    if kind=="wall":
        from .model import read_wall
        src=read_wall(controller.target) if controller.target is not None else controller.defaults
        keys=("thickness","height","alignment","material_name","structure","layers")
    elif kind=="slab":
        from .slab_model import read_slab
        src=read_slab(controller.target) if controller.target is not None else controller.defaults
        keys=("thickness","reference_plane","material_name","structure","layers")
    elif kind=="beam":
        from .beam_model import read_beam
        src=read_beam(controller.target) if controller.target is not None else controller.defaults
        keys=("section_type","profile_ref","profile_data","profile","width","height","diameter","rotation","anchor","material_name")
    elif kind=="column":
        from .column_model import read_column
        src=read_column(controller.target) if controller.target is not None else controller.defaults
        keys=("section_type","profile_ref","profile_data","profile","width","depth","diameter","rotation","anchor","material_name","stations")
    else: return {}
    return {k:copy.deepcopy(src.get(k)) for k in keys if k in src}


def apply_preset(kind,controller,preset):
    config=copy.deepcopy(preset.get("config",{}))
    if kind=="wall":
        from .model import read_wall
        base=read_wall(controller.target) if controller.target is not None else copy.deepcopy(controller.defaults)
        base.update(config);controller.load_fields(base);controller.defaults_changed()
    elif kind=="slab":
        controller.defaults.update(config);controller._load_defaults();controller.apply_current_values()
    elif kind=="beam":
        from .beam_model import read_beam
        base=read_beam(controller.target) if controller.target is not None else copy.deepcopy(controller.defaults)
        base.update(config)
        if base.get("section_type")=="complex" and base.get("profile_ref"):
            from .profile_library import profile_by_id
            base["profile_data"]=profile_by_id(base["profile_ref"])
        controller._load_fields(base);controller.values_changed()
    elif kind=="column":
        from .column_model import read_column
        base=read_column(controller.target) if controller.target is not None else copy.deepcopy(controller.defaults)
        base.update(config)
        if base.get("section_type")=="complex" and base.get("profile_ref"):
            from .profile_library import profile_by_id
            base["profile_data"]=profile_by_id(base["profile_ref"])
        controller._load_fields(base);controller.values_changed()


class ElementPresetPanel(QWidget):
    LABELS={"wall":"Wall","slab":"Slab","beam":"Beam","column":"Column"}
    def __init__(self,kind,controller,parent=None):
        super().__init__(parent or controller.panel);self.kind=kind;self.controller=controller;self._rows=[]
        lay=QVBoxLayout(self);lay.setContentsMargins(0,4,0,5);lay.setSpacing(4)
        title=QLabel(f"<b>Library · {self.LABELS.get(kind,kind)}</b>");lay.addWidget(title)
        self.combo=QComboBox();self.combo.currentIndexChanged.connect(self._sync);lay.addWidget(self.combo)
        row=QHBoxLayout();self.apply_btn=QPushButton("Apply preset");self.save_btn=QPushButton("Save as…");self.rename_btn=QPushButton("Rename");row.addWidget(self.apply_btn);row.addWidget(self.save_btn);row.addWidget(self.rename_btn);lay.addLayout(row)
        row2=QHBoxLayout();self.delete_btn=QPushButton("Delete");self.export_btn=QPushButton("Export "+self.LABELS.get(kind,kind).lower()+"…");self.import_btn=QPushButton("Import "+self.LABELS.get(kind,kind).lower()+"…");row2.addWidget(self.delete_btn);row2.addWidget(self.export_btn);row2.addWidget(self.import_btn);lay.addLayout(row2)
        if kind == "wall":
            note = QLabel("Saved wall styles: choose a preset and use Apply preset only to replace the wall type. Material, dimensions and layer edits below update immediately.")
            note.setWordWrap(True)
            note.setStyleSheet("color:#8e98a2;font-size:9pt;")
            lay.addWidget(note)
        self.info=QLabel();self.info.setWordWrap(True);self.info.setStyleSheet("color:#777;font-size:9pt;");lay.addWidget(self.info)
        self.apply_btn.setToolTip("Replace the current object's configuration with this saved preset. Other property edits are automatic.")
        self.apply_btn.clicked.connect(self.apply);self.save_btn.clicked.connect(self.save_current);self.rename_btn.clicked.connect(self.rename);self.delete_btn.clicked.connect(self.delete);self.export_btn.clicked.connect(self.export);self.import_btn.clicked.connect(self.import_file)
        self.refresh()
    def refresh(self,select_id=None):
        old=select_id if select_id is not None else self.combo.currentData();self.combo.blockSignals(True);self.combo.clear();self._rows=[]
        current_group=None;idx=-1;first_real=-1
        for item in all_for(self.kind):
            group=item.get("group") or "Other"
            if item.get("builtin"):group=folder_label(group)
            if group!=current_group:
                if self.combo.count():self.combo.insertSeparator(self.combo.count())
                self.combo.addItem(f"— {group} —",None);self.combo.model().item(self.combo.count()-1).setEnabled(False);current_group=group
            self.combo.addItem(builtin_name(item["name"]) if item.get("builtin") else item["name"],item["id"]);self._rows.append(item)
            if first_real<0:first_real=self.combo.count()-1
            if item["id"]==old:idx=self.combo.count()-1
        self.combo.setCurrentIndex(idx if idx>=0 else first_real);self.combo.blockSignals(False);self._sync()
    def selected(self):
        pid=self.combo.currentData()
        if pid is None:return None
        return next((x for x in all_for(self.kind) if x.get("id")==pid),None)
    def _sync(self,*_):
        p=self.selected();enabled=p is not None;personal=enabled and not p.get("builtin",False)
        self.apply_btn.setEnabled(enabled);self.rename_btn.setEnabled(personal);self.delete_btn.setEnabled(personal);self.export_btn.setEnabled(enabled)
        self.info.setText((p.get("description") or ("Preset bundled with the plugin." if p and p.get("builtin") else "Personal preset.")) if p else "")
    def apply(self):
        p=self.selected()
        if not p:return
        try:apply_preset(self.kind,self.controller,p);self.controller.message(f"Preset '{p['name']}' applied.")
        except Exception as exc:self.controller.message(str(exc),error=True)
    def save_current(self):
        name,ok=QInputDialog.getText(self,"Save preset", "Preset name:")
        if not ok or not _clean_name(name):return
        item=upsert_personal(self.kind,{"name":_clean_name(name),"group":"My presets","revision":1,"config":_source_values(self.kind,self.controller)})
        self.refresh(item["id"])
    def rename(self):
        p=self.selected()
        if not p or p.get("builtin"):return
        name,ok=QInputDialog.getText(self,"Rename preset","New name:",text=p["name"])
        if not ok or not _clean_name(name):return
        p["name"]=_clean_name(name);p["revision"]=int(p.get("revision",1))+1;item=upsert_personal(self.kind,p);self.refresh(item["id"])
    def delete(self):
        p=self.selected()
        if not p or p.get("builtin"):return
        if QMessageBox.question(self,"Delete preset",f"Delete '{p['name']}'?",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        delete_personal(self.kind,p["id"]);self.refresh()
    def export(self):
        p=self.selected()
        if not p:return
        path,_=QFileDialog.getSaveFileName(self,"Export preset",f"{p['name'].replace('/','-')}.apreset","Preset Parametric Architecture (*.apreset);;JSON (*.json)")
        if not path:return
        if not Path(path).suffix:path += ".apreset"
        payload={"format":FILE_FORMAT,"version":FILE_VERSION,"preset":p}
        Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    def import_file(self):
        # OpenTrace's own hierarchical browser, filtered to this tool.
        # No IngeTrazo AI assistant, no external workspace or library installer.
        from .resource_collections_ui import LibraryManagerDialog
        dialog=LibraryManagerDialog(None,self,current_kind=self.kind)
        dialog._browse_complete()
        if dialog.exec():
            # No project handle in this legacy tool-side entry point: keep
            # the checked recipes active for the current session. The project
            # library manager is responsible for persisting the selections.
            from .resource_collections import validate_collection
            global _ACTIVE_COLLECTIONS
            _ACTIVE_COLLECTIONS=[validate_collection(p) for p in dialog.selected_collections()]
        self.refresh()


class PresetCatalogController:
    def __init__(self,controllers):
        self.panels={}
        for kind,ctrl in controllers.items():
            if ctrl is None or not hasattr(ctrl,"panel"):continue
            panel=ElementPresetPanel(kind,ctrl,ctrl.panel);ctrl.panel.layout().insertWidget(1,panel);ctrl._catalog_preset_panel=panel;self.panels[kind]=panel
