# SPDX-License-Identifier: GPL-3.0-or-later
"""The architecture tools inside a viewport-owned floating frame.

All actions are the existing host-registered QActions. The child toolbar is
never registered with QMainWindow and retains Qt's native overflow chevron.
"""
from __future__ import annotations

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMenu, QSizePolicy, QToolBar, QToolButton

from .icons import icon
from .i18n import t
from .style import SIZES, qss, theme_font
from .viewport_overlay import OverlayFrame

COMPACT_KEY = "OpenTrace_BIM/tool_row_compact"
NORMAL_ICON = SIZES["icon-24"]
COMPACT_ICON = SIZES["icon-16"]


class ToolRow(OverlayFrame):
    def __init__(self, parent, wall, slab, column, beam, profile):
        super().__init__(parent)
        self.setObjectName("opentrace_tools_row")
        self.setMinimumWidth(0)
        self.setFocusPolicy(Qt.NoFocus)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SIZES["panel-inset"], 3, SIZES["panel-inset"], 3)
        layout.setSpacing(SIZES["space-2"])
        self.brand = QLabel("OpenTrace BIM", self)
        self.brand.setObjectName("opentrace_tool_brand")
        self.logo_slot = QLabel(self)
        self.logo_slot.setObjectName("opentrace_logo_slot")
        self.logo_slot.setFixedSize(NORMAL_ICON, NORMAL_ICON)
        layout.addWidget(self.logo_slot)
        layout.addWidget(self.brand)
        self.toolbar = QToolBar(t("OpenTrace BIM · Ferramentas"), self)
        self.toolbar.setObjectName("opentrace_tool_strip")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setMinimumWidth(0)
        self.toolbar.setFocusPolicy(Qt.NoFocus)
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.toolbar, 1)

        self._icon_cache = {}
        self._buttons = [wall.wall_menu_button]
        self._icon_entries = [(wall.wall_menu_button, wall.wall_menu_button.defaultAction(), "wall")]
        wall.wall_menu_button.setFocusPolicy(Qt.NoFocus)
        self.toolbar.addWidget(wall.wall_menu_button)
        for controller, name in ((slab, "slab"), (column, "column"), (beam, "beam")):
            if controller is not None:
                self._add(controller.action, name)
        self.toolbar.addSeparator()
        for action, name in zip(wall.openings.tool_actions, ("opening", "door", "window")):
            self._add(action, name)
            if name == "door":
                self._door_button = self.toolbar.widgetForAction(action)
        self._install_door_choices(wall.openings)
        self.toolbar.addSeparator()
        if profile is not None:
            self._add(profile.action, "profile")
        for _button, action, _name in self._icon_entries:
            if action is not None:
                action.toggled.connect(self.apply_theme)

        # Header and controls stay visible when the internal toolbar overflows.
        self.help_button = QToolButton(self)
        self.help_button.setObjectName("opentrace_tool_help")
        self.help_button.setText("?")
        self.help_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.help_button.setFocusPolicy(Qt.NoFocus)
        self.help_button.setToolTip(t("Ajuda da ferramenta ativa"))
        self.help_button.setAccessibleName(t("Ajuda contextual"))
        self.help_button.setFixedSize(28, 28)
        layout.addWidget(self.help_button)
        self.compact_button = QToolButton(self)
        self.compact_button.setFocusPolicy(Qt.NoFocus)
        self.compact_button.clicked.connect(self.toggle_compact)
        layout.addWidget(self.compact_button)
        self.set_compact(self.saved_compact())
        self.apply_theme()

    @staticmethod
    def saved_compact():
        return QSettings().value(COMPACT_KEY, False, type=bool)

    def _add(self, action, name):
        self.toolbar.addAction(action)
        button = self.toolbar.widgetForAction(action)
        button.setFocusPolicy(Qt.NoFocus)
        self._buttons.append(button)
        self._icon_entries.append((button, action, name))

    def _install_door_choices(self, openings):
        """Expose both insertion types directly on the Door's split button.

        Main click keeps the original registered Door QAction; the small menu
        changes only the flag of its existing placement engine. No new tool.
        """
        menu = QMenu(self._door_button)
        menu.setObjectName("opentrace_door_insertion_menu")
        door = menu.addAction("Porta completa")
        void = menu.addAction("Vão de porta (sem folha e batente)")
        door.setObjectName("opentrace_door_full_action")
        void.setObjectName("opentrace_door_void_action")
        for action in (door, void):
            action.setCheckable(True)
        menu.aboutToShow.connect(lambda: (
            door.setChecked(not openings.door_tool.door_as_opening),
            void.setChecked(openings.door_tool.door_as_opening)))
        def choose(as_opening):
            openings.door_tool.door_as_opening = as_opening
            # Existing host registration, action, Undo and placement path.
            from .wall_opening_ui import DOOR_TOOL_KEY
            openings._start(DOOR_TOOL_KEY)
            openings.notify_door_settings()
        door.triggered.connect(lambda _checked=False: choose(False))
        void.triggered.connect(lambda _checked=False: choose(True))
        from .door_style_catalog import DOOR_INSTALLATIONS
        family_menu=menu.addMenu('Sistema de abertura')
        family_actions={}
        for family,title in DOOR_INSTALLATIONS:
            action=family_menu.addAction(title)
            action.setCheckable(True)
            family_actions[family]=action
            def select_family(_=False,k=family):
                openings.choose_door_family(k, activate=True)
            action.triggered.connect(select_family)
        direction_menu=menu.addMenu('Correr para')
        for side,text in (('left','Esquerda'),('right','Direita')):
            action=direction_menu.addAction(text)
            def choose_side(_=False,k=side):
                openings.door_tool.door_slide_side=k
                openings.notify_door_settings()
            action.triggered.connect(choose_side)
        # Style buttons in the split popup caused unexpected re-activation
        # during a modelling session. The sidebar/contextual combos own the
        # *only* style selector; popup keeps only insertion/family/direction.
        def sync_gallery():
            tool=openings.door_tool
            for k,action in family_actions.items():
                action.setChecked(tool.door_family_key==k)
        menu.aboutToShow.connect(sync_gallery)
        self._door_button.setMenu(menu)
        self._door_button.setPopupMode(QToolButton.MenuButtonPopup)
        self._door_button.setToolTip("Click: insert door; arrow: select door or empty opening")

    def set_compact(self, compact):
        self.compact = bool(compact)
        size = QSize(COMPACT_ICON, COMPACT_ICON) if self.compact else QSize(NORMAL_ICON, NORMAL_ICON)
        style = Qt.ToolButtonIconOnly if self.compact else Qt.ToolButtonTextBesideIcon
        self.toolbar.setIconSize(size)
        self.toolbar.setToolButtonStyle(style)
        for button in self._buttons:
            button.setIconSize(size)
            button.setToolButtonStyle(style)
        self.compact_button.setText("▾" if self.compact else "▴")
        self.compact_button.setToolTip(
            t("Expandir a fileira de ferramentas") if self.compact
            else t("Recolher a fileira de ferramentas"))
        self.help_button.setIcon(icon("help", COMPACT_ICON, palette=QApplication.palette()))
        self.compact_button.setIcon(icon("expand" if self.compact else "collapse", COMPACT_ICON,
                                         palette=QApplication.palette()))
        self.compact_button.setText("")
        self.apply_theme()
        self.updateGeometry()

    def _design_icon(self, palette, name, size, state="normal"):
        key = (palette.cacheKey(), name, size, state)
        if key not in self._icon_cache:
            self._icon_cache[key] = icon(name, size, state=state, palette=palette)
        return self._icon_cache[key]

    def apply_theme(self):
        # Keep the inherited panel shadow in sync with light/dark palette
        # changes as well as this row's tools and brand.
        super().apply_theme()
        palette = QApplication.palette()
        height = SIZES["tool-height-compact" if self.compact else "tool-height"]
        self.brand.setFont(theme_font(QApplication.font(), "brand"))
        self.brand.setStyleSheet(qss("QLabel { color: {text}; padding: 0 4px; }", palette))
        self.logo_slot.setStyleSheet(qss("QLabel { background: {panel-raised}; "
                                         "border: 1px solid {panel-edge}; border-radius: 4px; }",
                                         palette))
        self.toolbar.setStyleSheet(qss(
            "QToolBar { background: {panel}; color: {text}; border: 0; spacing: 2px; }"
            "QToolButton { color: {text}; background: transparent; border: 1px solid transparent;"
            " border-radius: 4px; padding: 4px; font-size: 12px; font-weight: 500; }"
            "QToolButton:hover:!checked { background: {hover-wash}; }"
            "QToolButton:checked { background: {petrol}; border: 1px solid {petrol-edge};"
            " color: {on-petrol}; }"
            "QToolButton:disabled { color: {text-disabled}; background: transparent; }"
            "QToolButton:focus { border: 2px solid {focus-ring}; }", palette))
        for button, action, name in self._icon_entries:
            button.setMinimumHeight(height)
            button.setMaximumHeight(height)
            button.setIcon(self._design_icon(
                palette, name, COMPACT_ICON if self.compact else NORMAL_ICON,
                state="active" if action is not None and action.isChecked() else "normal"))
            button.setIconSize(QSize(COMPACT_ICON, COMPACT_ICON) if self.compact else
                               QSize(NORMAL_ICON, NORMAL_ICON))
        for button, name in ((self.help_button, "help"),
                             (self.compact_button, "expand" if self.compact else "collapse")):
            button.setIcon(self._design_icon(palette, name, COMPACT_ICON))
            button.setStyleSheet(qss(
                "QToolButton { background: transparent; color: {text}; border: 0; }"
                "QToolButton:hover { background: {hover-wash}; }", palette))

    def toggle_compact(self):
        self.set_compact(not self.compact)
        QSettings().setValue(COMPACT_KEY, self.compact)
