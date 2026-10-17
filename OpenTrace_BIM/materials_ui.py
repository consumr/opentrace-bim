# SPDX-License-Identifier: GPL-3.0-or-later
"""Searchable native material picker: virtual groups + lazy thumbnail preview."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox,QDialog,QVBoxLayout,QHBoxLayout,
    QLineEdit,QLabel,QTreeWidget,QTreeWidgetItem,QDialogButtonBox,QSplitter,QWidget)
from .resource_collections import material_folders
from .library_display import folder_label
from .resource_preview import preview_resource


class MaterialPickerCombo(QComboBox):
    """Keeps existing currentData/currentIndex and activated contracts."""
    def showPopup(self):
        if self.count()<=2:
            super().showPopup();return
        dialog=QDialog(self)
        dialog.setWindowTitle('Materials · search by name or category')
        dialog.resize(820,580)
        lay=QVBoxLayout(dialog)
        lay.addWidget(QLabel('Choose an existing material. Its preview is loaded only when selected; '
                             'browsing does not insert the material into the scene.'))
        search=QLineEdit(dialog)
        search.setPlaceholderText('Search concrete, brick, tile, metal, paint, stone, pattern…')
        search.setClearButtonEnabled(True);lay.addWidget(search)
        splitter=QSplitter(Qt.Horizontal,dialog)
        tree=QTreeWidget(splitter)
        tree.setHeaderLabels(['Categories and materials'])
        tree.setRootIsDecorated(True);tree.setUniformRowHeights(True)
        panel=QWidget(splitter);side=QVBoxLayout(panel)
        preview=QLabel(panel);preview.setFixedSize(270,190);preview.setAlignment(Qt.AlignCenter)
        side.addWidget(preview,alignment=Qt.AlignCenter)
        description=QLabel('Select a material to preview its texture or color.')
        description.setWordWrap(True);side.addWidget(description);side.addStretch(1)
        splitter.addWidget(tree);splitter.addWidget(panel);splitter.setSizes([500,320]);lay.addWidget(splitter,1)
        items=[(str(self.itemText(i)),self.itemData(i)) for i in range(self.count())]
        from .materials import material_catalog
        # Read the host's existing material definitions, if available. This
        # does not register materials or load all textures into the viewport.
        win=self.window()
        viewport=getattr(win,'viewport',None)
        scene=getattr(viewport,'scene',None)
        catalog=material_catalog(scene)
        folders=material_folders([label for label,val in items if val],catalog=catalog)
        indices={str(value):i for i,(_label,value) in enumerate(items) if value}
        for i,(label,value) in enumerate(items):
            if value is None:
                leaf=QTreeWidgetItem([label]);leaf.setData(0,Qt.UserRole,i)
                tree.addTopLevelItem(leaf)
        for folder,names in sorted(folders.items()):
            group=QTreeWidgetItem([folder_label(folder)]);tree.addTopLevelItem(group)
            for name in names:
                i=indices.get(name)
                if i is None:continue
                leaf=QTreeWidgetItem([name]);leaf.setData(0,Qt.UserRole,i)
                group.addChild(leaf)
        def filter_tree(value):
            needle=str(value).casefold().strip()
            def visit(node):
                own=needle in node.text(0).casefold()
                child_match=False
                for i in range(node.childCount()):
                    child_match=visit(node.child(i)) or child_match
                show=own or child_match
                node.setHidden(not show)
                if needle and child_match:node.setExpanded(True)
                return show
            for n in range(tree.topLevelItemCount()):visit(tree.topLevelItem(n))
        search.textChanged.connect(filter_tree)
        def change(item,*_):
            if item is None:return
            idx=item.data(0,Qt.UserRole)
            if not isinstance(idx,int):return
            name=items[idx][0]
            recipe=catalog.get(name,{})
            preview.setPixmap(preview_resource({'kind':'material','name':name,'data':recipe},size=(265,185)))
            description.setText(name+'\n'+('Texture available' if recipe.get('texture') else
                                         'Color / project material'))
        tree.currentItemChanged.connect(change)
        def accept_selection(*_):
            item=tree.currentItem()
            idx=item.data(0,Qt.UserRole) if item else None
            if isinstance(idx,int):dialog.done(idx+1000)
        tree.itemDoubleClicked.connect(lambda *_:accept_selection())
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,dialog)
        buttons.accepted.connect(accept_selection);buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)
        search.setFocus()
        result=dialog.exec()
        if result>=1000:
            index=result-1000
            if 0<=index<self.count():
                self.setCurrentIndex(index)
                self.activated.emit(index)
