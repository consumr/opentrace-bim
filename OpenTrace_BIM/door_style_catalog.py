# SPDX-License-Identifier: GPL-3.0-or-later
"""Local shared door catalogue: only keys, no per-widget mutable state."""
from .door_leaf_presets import LEAF_PRESETS, make_leaf_preset

DOOR_STYLES = tuple((key, name) for key, name, *_ in LEAF_PRESETS)
DOOR_INSTALLATIONS = (
    ("swing_single", "Abrir · uma folha"),
    ("sliding_surface", "Correr · aparente"),
    ("sliding_pocket", "Correr · embutida (ensaio)"),
)
DEFAULT_DOOR_STYLE = "plain_solid"

def prepare_door_style(tool, key):
    """Single canonical placement state shared by dock, bar and top tool menu."""
    if key not in dict(DOOR_STYLES):
        raise ValueError("Estilo de porta desconhecido.")
    size = tool.sizes["door"]
    tool.door_style_key = key
    tool.door_leaf_grid = make_leaf_preset(
        key, size["width"], size["height"], 0.035)
    tool.door_as_opening = False

def selected_style(tool):
    return getattr(tool, "door_style_key", DEFAULT_DOOR_STYLE)

def selected_installation(tool):
    return getattr(tool, "door_family_key", "swing_single")
