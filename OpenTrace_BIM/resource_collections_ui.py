# SPDX-License-Identifier: GPL-3.0-or-later
"""OpenTrace native hierarchical library manager; no external AI assistant."""
from __future__ import annotations
import copy
import uuid
from pathlib import Path
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QDialogButtonBox,
    QSplitter, QWidget, QInputDialog, QComboBox, QCheckBox,
)
from .resource_collections import (
    sample_collections, read_collection, write_collection, capture_personal_resources,
    make_collection, validate_collection, material_folders,
)
from .resource_exchange import (
    KIND_LABELS, export_resource, import_resource_file, collection_of_resources,
    add_to_personal_library,
)
from .resource_preview import preview_resource
from .library_display import library_label, resource_label, folder_label

SETTINGS_KEY='opentrace/resource_collection_paths_v1'
FOLDERS_KEY='opentrace/resource_collection_folders_v1'


def builtin_starter_collections():
    from .preset_catalog import builtins
    from .profile_library import builtin_profiles
    from .resource_collections import make_collection
    presets = builtins()
    profiles = builtin_profiles()
    packs = sample_collections(presets,profiles)
    full = []
    names = {'wall':'Walls','slab':'Slabs','beam':'Beams','column':'Columns'}
    for kind, entries in presets.items():
        for item in entries:
            full.append({'kind':kind,'id':item['id'],'name':item['name'],
                         'folder':'Objects / '+names.get(kind,kind)+' / '+str(item.get('group') or 'Other'),
                         'data':copy.deepcopy(item),'source':'opentrace:bundled'})
    for item in profiles:
        full.append({'kind':'profile','id':item['id'],'name':item['name'],
                     'folder':'Complex profiles / '+str(item.get('folder') or 'Other'),
                     'data':copy.deepcopy(item),'source':'opentrace:bundled'})
    packs.append(make_collection('Architecture · Complete',full,
                  ident='ot:arq:completa',folder='Architecture / Complete'))
    return packs


def _stored_paths(key):
    paths=QSettings().value(key,[]) or []
    return [paths] if isinstance(paths,str) else list(paths)


def available_collections():
    packs=builtin_starter_collections()
    discovered=_stored_paths(SETTINGS_KEY)[:100]
    for folder in _stored_paths(FOLDERS_KEY)[:20]:
        root=Path(folder)
        if not root.is_dir():continue
        count=0
        for file in root.rglob('*.otlib'):
            if len(file.relative_to(root).parts)>8:continue
            discovered.append(str(file));count+=1
            if count>=80:break
    seen={p['id'] for p in packs}
    for path in discovered[:240]:
        try:
            if Path(path).stat().st_size>25*1024*1024:continue
            pack=read_collection(path)
            if pack['id'] not in seen:
                packs.append(pack);seen.add(pack['id'])
        except (OSError,ValueError,TypeError):pass
    return packs


def add_collection_file(path):
    pack=read_collection(path)
    file=str(Path(path).resolve())
    saved=_stored_paths(SETTINGS_KEY)
    if file not in saved:QSettings().setValue(SETTINGS_KEY,saved+[file])
    return pack


class LibraryManagerDialog(QDialog):
    """Browse recipes lazily, import individuals, assemble/export complete packs."""
    def __init__(self,app=None,parent=None,*,selected=None,current_kind=None):
        super().__init__(parent)
        self.app=app
        self.packs=available_collections()
        self.current_kind=current_kind
        self._index={}
        self._add_project_packs()
        self.selected_ids=set()
        # Partial selections are persisted as actual recipes, not just a pack ID.
        self.selected_items_by_pack={}
        selections = selected if selected is not None else ('ot:arq:basica',)
        for choice in selections:
            if isinstance(choice,dict):
                pid=str(choice.get('id') or '')
                keys={(r.get('kind'),str(r.get('id'))) for r in choice.get('resources',())}
                original=next((p for p in self.packs if p['id']==pid),None)
                complete={(r['kind'],str(r['id'])) for r in original['resources']} if original else set()
                if keys==complete:self.selected_ids.add(pid)
                else:self.selected_items_by_pack[pid]=keys
            elif choice:self.selected_ids.add(str(choice))
        self.setWindowTitle('OpenTrace BIM · Libraries and Objects')
        self.resize(1040,690)
        root=QVBoxLayout(self)
        root.addWidget(QLabel('Browse the complete collection and import individual resources. Select the libraries for this project; '
                              'nothing is automatically inserted into the viewport.'))
        search_row=QHBoxLayout()
        self.search=QLineEdit(self)
        self.search.setPlaceholderText('Search walls, doors, materials, profiles, folders or codes…')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        search_row.addWidget(self.search,1)
        self.kind_filter=QComboBox(self)
        self.kind_filter.addItem('All types',None)
        for key,label in KIND_LABELS.items():self.kind_filter.addItem(label.capitalize(),key)
        if current_kind:
            idx=self.kind_filter.findData(current_kind)
            if idx>=0:self.kind_filter.setCurrentIndex(idx)
        self.kind_filter.currentIndexChanged.connect(lambda *_:self._filter(self.search.text()))
        search_row.addWidget(self.kind_filter)
        root.addLayout(search_row)
        splitter=QSplitter(Qt.Horizontal,self)
        self.tree=QTreeWidget(splitter)
        self.tree.setHeaderLabels(['Library / Folder / Object', 'Type'])
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.itemChanged.connect(self._checked)
        self.tree.currentItemChanged.connect(self._preview)
        self.tree.itemDoubleClicked.connect(lambda item,_:self._import_one() if self._resource_of(item) else None)
        details=QWidget(splitter);right=QVBoxLayout(details)
        self.preview=QLabel(details)
        self.preview.setFixedSize(300,205)
        self.preview.setAlignment(Qt.AlignCenter)
        right.addWidget(self.preview,alignment=Qt.AlignCenter)
        self.details=QLabel('Select an object to see its preview.')
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        right.addWidget(self.details)
        right.addStretch(1)
        splitter.addWidget(self.tree);splitter.addWidget(details)
        splitter.setSizes([670,350]);root.addWidget(splitter,1)
        controls=QHBoxLayout()
        self.select_all=QCheckBox('Select all / Deselect all',self)
        self.select_all.setToolTip('Check all libraries and objects. Uncheck to clear every selection.')
        self.select_all.stateChanged.connect(self._select_everything)
        self.selection_summary=QLabel('',self)
        controls.addWidget(self.select_all)
        controls.addWidget(self.selection_summary,1)
        root.addLayout(controls)
        row=QHBoxLayout()
        for text,fn in (
            ('Browse full library',self._browse_complete),
            ('Import current object',self._import_one),
            ('Export object…',self._export_one),
            ('Import object file…',self._import_item_file),
        ):
            b=QPushButton(text,self);b.clicked.connect(fn);row.addWidget(b)
        root.addLayout(row)
        row2=QHBoxLayout()
        for text,fn in (
            ('Import library…',self._import),
            ('Export library / folder…',self._export),
            ('Create library from selection…',self._create_from_selection),
            ('Save favorites as library…',self._export_personal),
            ('Add library folder…',self._add_folder),
        ):
            b=QPushButton(text,self);b.clicked.connect(fn);row2.addWidget(b)
        root.addLayout(row2)
        bottom=QHBoxLayout()
        import_selected=QPushButton('Import selected objects to project',self)
        import_selected.clicked.connect(self._import_checked)
        bottom.addWidget(import_selected)
        bottom.addStretch(1)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,self)
        buttons.button(QDialogButtonBox.Ok).setText('Load checked libraries / objects')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        root.addLayout(bottom)
        self._rebuild()

    def _add_project_packs(self):
        if self.app is None:return
        try:
            raw=self.app.document_data(default=None) or {}
            stored=(raw.get('project_setup') or {}).get('resource_libraries') or []
            seen={x['id'] for x in self.packs}
            for record in stored:
                try:pack=validate_collection(record)
                except (TypeError,ValueError):continue
                if pack['id'] not in seen:self.packs.append(pack);seen.add(pack['id'])
        except (ValueError,TypeError,AttributeError):pass

    @staticmethod
    def _resource_key(record):
        return record['kind'], str(record['id'])

    def _leaf_items(self,node):
        if self._resource_of(node) is not None:
            yield node
        for j in range(node.childCount()):
            yield from self._leaf_items(node.child(j))

    def _checked_records(self,pack_index):
        parent=self.tree.topLevelItem(pack_index)
        pack=self.packs[pack_index]
        checked={self._resource_key(self._resource_of(leaf)) for leaf in self._leaf_items(parent)
                 if leaf.checkState(0)==Qt.Checked}
        return [copy.deepcopy(r) for r in pack['resources'] if self._resource_key(r) in checked]

    def selected_collections(self):
        # A complete collection includes EVERY checked recipe; selecting a
        # folder/leaf yields a portable subset that actually populates tools.
        out=[]
        for i,pack in enumerate(self.packs):
            records=self._checked_records(i)
            if not records:continue
            chosen=copy.deepcopy(pack);chosen['resources']=records
            out.append(chosen)
        return out

    def _sync_selection(self):
        self.selected_ids=set()
        self.selected_items_by_pack={}
        total=0;number=0
        for i,pack in enumerate(self.packs):
            node=self.tree.topLevelItem(i)
            keys={self._resource_key(self._resource_of(leaf)) for leaf in self._leaf_items(node)
                  if leaf.checkState(0)==Qt.Checked}
            if not keys:continue
            number+=1;total+=len(keys)
            if len(keys)==len(pack['resources']):self.selected_ids.add(pack['id'])
            else:self.selected_items_by_pack[pack['id']]=keys
        self.selection_summary.setText(f'{number} collections · {total} selected resources')
        all_selected=bool(self.packs) and all(
            self.tree.topLevelItem(i).checkState(0)==Qt.Checked
            for i in range(self.tree.topLevelItemCount()))
        old=self.select_all.blockSignals(True)
        self.select_all.setChecked(all_selected)
        self.select_all.blockSignals(old)

    def _set_descendants(self,item,state):
        for i in range(item.childCount()):
            child=item.child(i)
            child.setCheckState(0,state)
            self._set_descendants(child,state)

    def _update_ancestors(self,item):
        while item is not None:
            states=[item.child(j).checkState(0) for j in range(item.childCount())]
            if states:
                state=(Qt.Checked if all(x==Qt.Checked for x in states) else
                       Qt.Unchecked if all(x==Qt.Unchecked for x in states) else Qt.PartiallyChecked)
                item.setCheckState(0,state)
            item=item.parent()

    def _checked(self,item,column):
        if column!=0:return
        state=item.checkState(0)
        if state==Qt.PartiallyChecked:return
        self.tree.blockSignals(True)
        try:
            self._set_descendants(item,state)
            self._update_ancestors(item.parent())
        finally:self.tree.blockSignals(False)
        self._sync_selection()

    def _select_everything(self,state):
        checked=Qt.Checked if state==Qt.Checked else Qt.Unchecked
        self.tree.blockSignals(True)
        try:
            for i in range(self.tree.topLevelItemCount()):
                parent=self.tree.topLevelItem(i)
                parent.setCheckState(0,checked)
                self._set_descendants(parent,checked)
        finally:self.tree.blockSignals(False)
        self._sync_selection()

    def _checked_leaves(self):
        for i in range(self.tree.topLevelItemCount()):
            for leaf in self._leaf_items(self.tree.topLevelItem(i)):
                if leaf.checkState(0)==Qt.Checked:
                    yield self._resource_of(leaf)

    def _import_checked(self):
        from .resource_exchange import add_to_personal_library
        # Explicit import from the index creates portable personal presets,
        # never places or modifies geometry in the scene.
        unique={self._resource_key(rec):rec for rec in self._checked_leaves()}
        if not unique:
            QMessageBox.information(self,'Import resources','Check one or more objects first.')
            return
        if len(unique)>25 and QMessageBox.question(self,'Import resources',
                f'Import {len(unique)} selected objects into your personal resources?',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        imported=[];errors=[]
        for rec in unique.values():
            try:imported.append(add_to_personal_library(rec,existing=getattr(self.app,'scene',None)))
            except (OSError,ValueError,TypeError) as exc:errors.append(f"{resource_label(rec)}: {exc}")
        message=f'{len(imported)} objects imported into personal resources.'
        if errors:message+='\nErrors (first 5):\n'+'\n'.join(errors[:5])
        QMessageBox.information(self,'Import selected resources',message)

    def accept(self):
        full=[i for i in range(self.tree.topLevelItemCount())
              if self.tree.topLevelItem(i).checkState(0)==Qt.Checked]
        partial=[i for i in range(self.tree.topLevelItemCount())
                 if self.tree.topLevelItem(i).checkState(0)==Qt.PartiallyChecked]
        if full and partial:
            if QMessageBox.question(self,'Mixed selection',
                'You checked complete libraries and individual objects or folders.\n'
                'Both selections will be loaded. Continue?',
                QMessageBox.Yes|QMessageBox.No,QMessageBox.Yes)!=QMessageBox.Yes:return
        super().accept()

    def _resource_of(self,item):
        raw=item.data(0,Qt.UserRole) if item else None
        return raw if isinstance(raw,dict) and 'kind' in raw else None

    def _rebuild(self):
        # Preserve the user's checked leaf-level selection across rebuilds.
        self.tree.blockSignals(True);self.tree.clear();self._index={}
        for pack in self.packs:
            pid=pack['id']
            header=QTreeWidgetItem([library_label(pack),str(len(pack['resources']))+' items'])
            header.setData(0,Qt.UserRole,pid)
            header.setFlags(header.flags()|Qt.ItemIsUserCheckable)
            self.tree.addTopLevelItem(header)
            folders={}
            full=pid in self.selected_ids
            subsets=self.selected_items_by_pack.get(pid,set())
            for rec in pack['resources']:
                parent=header;prefix=''
                for bit in (x.strip() for x in rec.get('folder','').split('/') if x.strip()):
                    prefix+='/'+bit
                    if prefix not in folders:
                        sub=QTreeWidgetItem([folder_label(bit),'Folder'])
                        sub.setFlags(sub.flags()|Qt.ItemIsUserCheckable)
                        parent.addChild(sub);folders[prefix]=sub
                    parent=folders[prefix]
                leaf=QTreeWidgetItem([resource_label(rec),KIND_LABELS.get(rec['kind'],rec['kind'])])
                leaf.setData(0,Qt.UserRole,rec)
                leaf.setFlags(leaf.flags()|Qt.ItemIsUserCheckable)
                leaf.setCheckState(0,Qt.Checked if full or self._resource_key(rec) in subsets else Qt.Unchecked)
                parent.addChild(leaf)
            for folder in sorted(folders.values(),key=lambda x:len(x.text(0)),reverse=True):
                self._update_ancestors(folder)
            self._update_ancestors(header)
            if not pack['resources']:
                header.setCheckState(0,Qt.Unchecked)
        self.tree.blockSignals(False)
        self._sync_selection()
        self._filter(self.search.text())

    def _filter(self,value):
        needle=str(value).casefold().strip();kind=self.kind_filter.currentData()
        def visit(item):
            rec=self._resource_of(item)
            matched=((not kind or (rec is not None and rec['kind']==kind)) and
                     (not needle or needle in (item.text(0)+' '+item.text(1)+' '+
                      (str(rec.get('id')) if rec else '')).casefold())) if rec else False
            child_visible=False
            for j in range(item.childCount()):child_visible=visit(item.child(j)) or child_visible
            visible=matched or child_visible
            # Pack and folder nodes show only when at least one descendant matches.
            item.setHidden(not visible)
            if (needle or kind) and child_visible:item.setExpanded(True)
            return visible
        for i in range(self.tree.topLevelItemCount()):visit(self.tree.topLevelItem(i))

    def _preview(self,current,*_):
        rec=self._resource_of(current)
        if rec is None:
            self.preview.clear()
            self.details.setText('Select an object in the folder to preview its dimensions, materials and source.\n'
                                 'You can import individual items or export complete folders.')
            return
        scene=getattr(self.app,'scene',None) if self.app is not None else None
        self.preview.setPixmap(preview_resource(rec,scene=scene,size=(290,190)))
        cfg=(rec.get('data') or {}).get('config') or rec.get('data') or {}
        meta=', '.join(f'{k}: {v}' for k,v in cfg.items()
                       if k in ('thickness','width','height','depth','structure','section_type'))
        self.details.setText(f"{resource_label(rec)}\nType: {KIND_LABELS.get(rec['kind'],rec['kind'])}"
                             f"\nSource: {rec.get('source') or 'Personal library'}"
                             + ('\n'+meta if meta else '') +
                             '\nSchematic preview; not a replacement for the 3D object view.')

    def _selected_pack(self):
        item=self.tree.currentItem()
        if item is None:return None,None
        while item.parent():item=item.parent()
        ident=item.data(0,Qt.UserRole)
        return next((p for p in self.packs if p['id']==ident),None),self.tree.currentItem()

    def _selection_resources(self):
        pack,node=self._selected_pack()
        if not pack:return []
        if node.parent() is None:return copy.deepcopy(pack['resources'])
        gathered=[]
        def walk(item):
            rec=self._resource_of(item)
            if rec is not None:gathered.append(copy.deepcopy(rec))
            for i in range(item.childCount()):walk(item.child(i))
        walk(node)
        return gathered

    def _add_pack(self,pack,*,select=True):
        if all(p['id']!=pack['id'] for p in self.packs):self.packs.append(pack)
        if select:self.selected_ids.add(pack['id'])
        self._rebuild()

    def _import(self):
        path,_=QFileDialog.getOpenFileName(self,'Import OpenTrace object library','',
                                           'OpenTrace library (*.otlib *.json)')
        if not path:return
        try:self._add_pack(add_collection_file(path))
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Import library',str(exc))

    def _import_item_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Import OpenTrace object file','',
                                           'OpenTrace object (*.otitem *.apreset *.json)')
        if not path:return
        try:
            rec=import_resource_file(path)
            pack=collection_of_resources('Imported objects · '+Path(path).stem,[rec])
            self._add_pack(pack,select=False)
            # Select the item for preview before making it a personal preset.
            QMessageBox.information(self,'Object available',
                'Object added to the library browser. Select it and click '
                '“Import object to project” to confirm.')
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Import object',str(exc))

    def _import_one(self):
        rec=self._resource_of(self.tree.currentItem())
        if rec is None:
            QMessageBox.information(self,'Import object','Select an object, not a library folder.')
            return
        try:
            kind,ident=add_to_personal_library(rec,existing=getattr(self.app,'scene',None))
            note='Imported into your personal resources; now available in the tool list.'
            if kind in ('door','window'):
                note=('Door/window favorite saved to your personal library. Applying it directly through the '
                      'door/window tools still needs integration; existing geometry was not changed.')
            QMessageBox.information(self,'Object imported',resource_label(rec)+'\n'+note)
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Import object',str(exc))

    def _export_one(self):
        rec=self._resource_of(self.tree.currentItem())
        if rec is None:
            QMessageBox.information(self,'Export object','Select an object to export.')
            return
        kind=KIND_LABELS.get(rec['kind'],rec['kind'])
        path,_=QFileDialog.getSaveFileName(self,'Export '+kind,
                     rec['name'].replace('/','-')+'.otitem','OpenTrace object (*.otitem)')
        if not path:return
        if not path.lower().endswith('.otitem'):path+='.otitem'
        try:export_resource(rec,path)
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Export object',str(exc))

    def _export_pack(self,pack):
        path,_=QFileDialog.getSaveFileName(self,'Export library / folder',
                    pack['name'].replace('/','-')+'.otlib','OpenTrace library (*.otlib)')
        if not path:return
        if not path.lower().endswith('.otlib'):path+='.otlib'
        try:write_collection(pack,path)
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Export library',str(exc))

    def _export(self):
        pack,node=self._selected_pack()
        if pack is None:
            QMessageBox.information(self,'Export library','Select a library or folder.')
            return
        if node.parent() is not None:
            records=self._selection_resources()
            if not records:return
            pack=collection_of_resources(node.text(0),records,folder=pack['name'])
        self._export_pack(pack)

    def _create_from_selection(self):
        records=self._selection_resources()
        if not records:
            QMessageBox.information(self,'New library','First select a folder or object containing resources.')
            return
        name,ok=QInputDialog.getText(self,'New library','Library name:')
        if not ok or not name.strip():return
        pack=collection_of_resources(name.strip(),records)
        self._add_pack(pack)
        QMessageBox.information(self,'New library',
            'Collection created for this session. Use “Export library / folder” '
            'to save an .otlib file for sharing. You can also link this library to the project.')

    def _export_personal(self):
        from .resource_favourites import favourites
        pack=capture_personal_resources()
        records=list(pack['resources'])
        for kind,items in favourites().items():
            for item in items:
                records.append({'kind':kind,'id':item['id'],'name':item['name'],
                                'folder':'Openings / '+KIND_LABELS.get(kind,kind),
                                'data':item,'source':'user:favourites'})
        if not records:
            QMessageBox.information(self,'Favorites','There are no personal resources to export yet.')
            return
        self._export_pack(collection_of_resources('My favorites',records))

    def _add_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Folder containing .otlib libraries and subfolders')
        if not folder:return
        paths=_stored_paths(FOLDERS_KEY);normalized=str(Path(folder).resolve())
        if normalized not in paths:QSettings().setValue(FOLDERS_KEY,paths+[normalized])
        selections=self.selected_ids.copy()
        self.packs=available_collections();self._add_project_packs()
        self.selected_ids=selections;self._rebuild()

    def _browse_complete(self):
        from .preset_catalog import builtins,load_personal
        from .profile_library import load_profiles
        records=[]
        labels={'wall':'Walls','slab':'Slabs','beam':'Beams','column':'Columns'}
        for kind,items in builtins().items():
            for item in items:
                records.append({'kind':kind,'id':item['id'],'name':item['name'],
                     'folder':'Objects / '+labels.get(kind,kind)+' / '+str(item.get('group') or 'Other'),
                     'data':item,'source':'builtin'})
        for kind,items in load_personal().items():
            for item in items:
                records.append({'kind':kind,'id':str(item['id']),'name':item['name'],
                     'folder':'Objects / '+labels.get(kind,kind)+' / My presets',
                     'data':item,'source':'personal'})
        for item in load_profiles():
            records.append({'kind':'profile','id':item['id'],'name':item['name'],
                  'folder':'Complex profiles / '+str(item.get('folder') or 'Miscellaneous'),
                  'data':item,'source':'personal' if not item.get('builtin') else 'builtin'})
        # Optional reusable door/window favourites are independent of hosts/openings.
        from .resource_favourites import favourites
        for kind,items in favourites().items():
            for item in items:
                records.append({'kind':kind,'id':item['id'],'name':item['name'],
                     'folder':'Openings / '+KIND_LABELS.get(kind,kind).capitalize(),
                     'data':item,'source':'personal'})
        if self.app is not None:
            from .materials import material_catalog
            catalog=material_catalog(self.app.scene)
            for folder,names in material_folders(catalog,catalog=catalog).items():
                for name in names:
                    records.append({'kind':'material','id':'material:'+name,'name':name,
                            'folder':'Materials / '+folder_label(folder),
                            'data':copy.deepcopy(catalog[name]),'source':'host'})
        full=make_collection('Full library · available to load',records,
                             ident='ot:consulta:completa',folder='Full library')
        self.packs=[p for p in self.packs if p['id']!='ot:consulta:completa']+[full]
        self._rebuild();self.tree.expandToDepth(1)
