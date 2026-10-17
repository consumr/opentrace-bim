# SPDX-License-Identifier: GPL-3.0-or-later
"""Original editable instance templates for leaves and sashes."""
from __future__ import annotations
from .door_leaf_grid import normalize_leaf_grid

# Tuple contract intentionally retained for existing gallery-thumbnail code.
LEAF_PRESETS = (
    ("full_glass", "Vidro inteiro", 1, 1, ("glass",)),
    ("half_glazed", "Meio vidro", 1, 2, ("solid", "glass")),
    ("french", "Francesa 2 × 3", 2, 3, ("glass",)*6),
    ("vertical", "Verticais 3 × 1", 3, 1, ("glass",)*3),
    ("three_panels", "Três painéis", 1, 3, ("solid",)*3),
    ("ventilated", "Veneziana + vidro", 1, 2, ("louver", "glass")),
    ("atelier", "Ateliê 2 × 4", 2, 4, ("solid","solid")+("glass",)*6),
    ("open_upper", "Visor superior", 1, 3, ("solid","solid","glass")),
    ("plain_solid", "Porta lisa", 1, 1, ("solid",)),
    ("movable_vision", "Lisa + visor móvel", 1, 1, ("solid",)),
    ("arch_glazed", "Arco com vidro", 1, 1, ("glass",)),
    ("arch_solid", "Porta lisa em arco", 1, 1, ("solid",)),
)


def make_leaf_preset(key, width, height, thickness, previous=None):
    pattern = next((p for p in LEAF_PRESETS if p[0]==key),None)
    if pattern is None:
        raise ValueError("Estilo de folha desconhecido.")
    _key,_title,cols,rows,types=pattern
    prev=previous or {}
    grid={
        "columns":cols,"rows":rows,"cell_types":list(types),
        "stile_width":min(.075,width*.09),
        "rail_width":min(.085,height*.09),
        "mullion_width":min(.042,width/(cols*8)),
        "transom_width":min(.042,height/(rows*8)),
        "glass_thickness":prev.get("glass_thickness",min(.008,thickness/4)),
        "panel_thickness":prev.get("panel_thickness",min(.018,thickness/2)),
        # New glazed/multi-panel presets always start with a closed frame.
        # Existing manually-authored grids retain their independent toggles.
        "stiles_enabled":True,
        "rails_enabled":True,
        "uniform_structure":prev.get("uniform_structure",False),
        "uniform_external_rails":prev.get("uniform_external_rails",True),
        "uniform_internal_transoms":prev.get("uniform_internal_transoms",True),
        "member_overrides":{},  # Presets change member numbering and location.
        "member_materials":dict(prev.get("member_materials",{})),
        "member_profiles":dict(prev.get("member_profiles",{})),
        "structure_width":prev.get("structure_width",min(.06,width*.07)),
        "mode":"inset" if key=="movable_vision" else "grid",
        "top_arc_enabled":key.startswith("arch_"),
        "top_arc_rise":min(.15,width*.22,height*.12),
        "insert":dict(prev.get("insert",{})),
        "uniform_materials":dict(prev.get("uniform_materials",{})),
        "kind_materials":dict(prev.get("kind_materials",{})),
        "part_materials":{},  # A new style resets piece-specific placements.
    }
    if key=="plain_solid":
        grid["stiles_enabled"]=False
        grid["rails_enabled"]=False
    if key=="movable_vision":
        grid["stiles_enabled"]=False
        grid["rails_enabled"]=False
        grid["insert"]={
            "width":min(.32,width*.55),"height":min(.42,height*.4),
            "x":.5,"z":.62,"kind":"glass","frame_enabled":True,
            "frame_width":min(.025,width*.03),
        }
    if key=="arch_solid":
        grid["stiles_enabled"]=False
        grid["rails_enabled"]=False
    return normalize_leaf_grid(grid,width,height,thickness)
