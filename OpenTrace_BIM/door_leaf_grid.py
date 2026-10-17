# SPDX-License-Identifier: GPL-3.0-or-later
"""Instance-only parametrized door/sash assembly (no Qt or host dependency).

All dimensions are metres.  Top arcs use a polygonal approximation of an
actual circular arch. Cell order is bottom-to-top, then left-to-right.
The old six numeric fields and cell_types contract are preserved.
"""
from __future__ import annotations

import copy
import math

PANEL_KINDS = ("glass", "solid", "louver", "open")
MATERIAL_GROUPS = ("structure", "glass", "solid", "louver")
DEFAULT_GRID = {
    "columns": 2, "rows": 3,
    "stile_width": 0.08, "rail_width": 0.10,
    "mullion_width": 0.045, "transom_width": 0.045,
    "glass_thickness": 0.008, "panel_thickness": 0.018,
    "cell_types": ["solid", "solid", "glass", "glass", "glass", "glass"],
    "stiles_enabled": True, "rails_enabled": True,
    "uniform_external_rails": True, "uniform_internal_transoms": True,
    "member_overrides": {}, "member_materials": {},
    "uniform_structure": False, "structure_width": 0.06,
    "mode": "grid", "top_arc_enabled": False, "top_arc_rise": 0.15,
    "insert": {"width": 0.30, "height": 0.40, "x": 0.5, "z": 0.60,
               "kind": "glass", "frame_enabled": True, "frame_width": 0.025},
    "uniform_materials": {group: True for group in MATERIAL_GROUPS},
    "kind_materials": {}, "part_materials": {},
}


def _numeric(raw, name, default, *, low=0.0):
    value = raw.get(name, default)
    if isinstance(value, bool):
        raise ValueError(f"{name}: valor numérico inválido.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: valor numérico inválido.") from exc
    if not math.isfinite(number) or number <= low:
        raise ValueError(f"{name}: medida deve ser maior que {low}.")
    return number


def member_widths(grid):
    """Legacy four nominal widths, with scoped links instead of a global width."""
    common = grid.get("structure_width", .06) if grid.get("uniform_structure", False) else None
    sections = grid.get("member_profiles", {})
    def size(group, key):
        profile = sections.get(group, {}) if isinstance(sections, dict) else {}
        if common is None and profile.get("shape") == "circle":
            return profile.get("diameter", grid[key])
        return common if common is not None else grid[key]
    return {
        "stile": (size("rail", "rail_width") if member_linked(grid,"rail")
                  else (common if common is not None else grid["stile_width"]))
                 if grid.get("stiles_enabled", True) else 0.0,
        "rail": size("rail", "rail_width") if grid.get("rails_enabled", True) else 0.0,
        "mullion": (size("transom","transom_width") if member_linked(grid,"transom")
                    else (common if common is not None else grid["mullion_width"])),
        "transom": size("transom", "transom_width"),
    }


def member_family(part_id):
    """External: side stiles + head/sill; internal: mullions + transoms.

    No profile is selected when the editor first opens: None is legitimate.
    """
    if not isinstance(part_id, str):
        return None
    if part_id in ("rail_top","rail_bottom","stile_left","stile_right"):
        return "rail"
    if (part_id.startswith("transom_") and part_id[8:].isdigit() or
        part_id.startswith("mullion_") and part_id[8:].isdigit()):
        return "transom"
    return None


def member_linked(grid, family):
    if family not in ("rail", "transom"):
        return False
    return grid.get("uniform_external_rails" if family == "rail" else
                    "uniform_internal_transoms", True)


def resolved_member(grid, part_id, component=None):
    """Resolve any structural part, including vertical members and overrides.

    The historic flags/fields stay JSON compatible, but now group links span
    both directions. Unlink never removes the saved overrides.
    """
    family = member_family(part_id)
    if family is None:
        return None
    linked = member_linked(grid, family)
    vertical = part_id.startswith(("stile_", "mullion_"))
    sizes = member_widths(grid)
    base = sizes[("stile" if family=="rail" else "mullion") if vertical else family]
    profile = copy.deepcopy(grid.get("member_profiles", {}).get(family, {}))
    if vertical and not linked:
        # Vertical sections retain their original rectangular section unless
        # deliberately overridden; they do not inherit the horizontal profile.
        profile = {"shape":"rect","depth":grid.get("leaf_profile_depth",.035),
                   "diameter":base}
    override = (grid.get("member_overrides", {}).get(part_id, {}) if not linked else {})
    if override:
        base = override.get("width", base)
        profile = copy.deepcopy(override.get("profile", profile))
    if profile.get("shape") == "circle" and not grid.get("uniform_structure", False):
        base = profile.get("diameter", base)
    return {"width": base, "profile": profile, "family": family}


def horizontal_and_vertical_sizes(grid):
    """Exact outer/inner dimensions, shared by bounds, preview and mesh."""
    left=(resolved_member(grid,"stile_left")["width"] if grid.get("stiles_enabled",True) else 0.)
    right=(resolved_member(grid,"stile_right")["width"] if grid.get("stiles_enabled",True) else 0.)
    mullions=[resolved_member(grid,f"mullion_{i}")["width"]
              for i in range(1,grid["columns"])]
    return left,right,mullions


def cell_rectangles(grid, width, height):
    """Exact visible cells with individual widths in BOTH axis directions."""
    cols,rows=grid["columns"],grid["rows"]
    left,right,mullions=horizontal_and_vertical_sizes(grid)
    bottom=(resolved_member(grid,"rail_bottom")["width"]
            if grid.get("rails_enabled",True) else 0.)
    top=(resolved_member(grid,"rail_top")["width"]
         if grid.get("rails_enabled",True) else 0.)
    crossbars=[resolved_member(grid,f"transom_{r}")["width"]
               for r in range(1,rows)]
    arch=grid["top_arc_rise"] if grid.get("top_arc_enabled",False) else 0.
    cw=(width-left-right-sum(mullions))/cols
    ch=(height-arch-bottom-top-sum(crossbars))/rows
    z=bottom
    for row in range(rows):
        x=left
        for col in range(cols):
            yield row,col,x,x+cw,z,z+ch
            x += cw+(mullions[col] if col<len(mullions) else 0)
        if row<rows-1:z+=ch+crossbars[row]


def _check_member_profile(section, default_depth, default_width, family):
    """Validate each embedded profile with the same contract as group profiles."""
    if not isinstance(section,dict):
        raise ValueError("Perfil de travessa inválido.")
    shape=section.get("shape","rect")
    if shape not in ("rect","circle","complex"):
        raise ValueError("Seção de travessa desconhecida.")
    item={"shape":shape,
          "depth":_numeric(section,"depth",default_depth),
          "diameter":_numeric(section,"diameter",default_width)}
    if item["depth"]>.5 or item["diameter"]>.5:
        raise ValueError("Profundidade/diâmetro do perfil excessivo.")
    if shape=="complex":
        embedded=section.get("profile_data")
        if not isinstance(embedded,dict) or not isinstance(embedded.get("loops"),list):
            raise ValueError("Selecione um perfil complexo da biblioteca.")
        if not 1<=len(embedded["loops"])<=24:
            raise ValueError("Perfil complexo com quantidade de laços inválida.")
        for loop in embedded["loops"]:
            pts=loop.get("points") if isinstance(loop,dict) else None
            if not isinstance(pts,list) or not 3<=len(pts)<=256:
                raise ValueError("Perfil complexo sem contorno válido.")
            for pt in pts:
                if (not isinstance(pt,(list,tuple)) or len(pt)<2 or
                    not all(isinstance(v,(float,int)) and math.isfinite(v) for v in pt[:2])):
                    raise ValueError("Perfil complexo com coordenadas inválidas.")
        item["profile_data"]=copy.deepcopy(embedded)
        item["profile_ref"]=str(section.get("profile_ref") or embedded.get("id") or "")
    return item


def normalize_leaf_grid(raw, width, height, leaf_thickness):
    """Canonical JSON-safe composition with validated physical bounds."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Composição da folha deve ser um registro.")
    width, height, leaf_thickness = float(width), float(height), float(leaf_thickness)
    if min(width, height, leaf_thickness) <= 0:
        raise ValueError("Dimensões físicas da folha inválidas.")
    result = {"leaf_profile_depth": leaf_thickness}
    for name in ("columns", "rows"):
        value = raw.get(name, DEFAULT_GRID[name])
        if type(value) is not int or not 1 <= value <= 8:
            raise ValueError("Colunas e linhas: valores entre 1 e 8.")
        result[name] = value
    for name in ("stile_width", "rail_width", "mullion_width", "transom_width",
                 "glass_thickness", "panel_thickness", "structure_width", "top_arc_rise"):
        result[name] = _numeric(raw, name, DEFAULT_GRID[name])
    if result["glass_thickness"] >= leaf_thickness:
        raise ValueError("Vidro deve ser mais fino que a folha.")
    if result["panel_thickness"] > leaf_thickness:
        raise ValueError("Painel não pode ser mais espesso que a folha.")
    for key in ("stiles_enabled", "rails_enabled", "uniform_structure", "top_arc_enabled",
                "uniform_external_rails", "uniform_internal_transoms"):
        value = raw.get(key, DEFAULT_GRID[key])
        if type(value) is not bool:
            raise ValueError(f"{key}: escolha inválida.")
        result[key] = value
    result["mode"] = raw.get("mode", "grid")
    if result["mode"] not in ("grid", "inset"):
        raise ValueError("Modo de composição desconhecido.")
    if result["top_arc_enabled"] and (result["top_arc_rise"] >= width / 2 or
                                       result["top_arc_rise"] >= height - .03):
        raise ValueError("Arco: flecha menor que meia largura e que a altura da folha.")

    raw_sections=raw.get("member_profiles", {})
    if not isinstance(raw_sections,dict):
        raise ValueError("Perfis da estrutura inválidos.")
    sections={}
    for group in ("rail", "transom"):
        sections[group]=_check_member_profile(raw_sections.get(group,{}),
                         leaf_thickness,result[group+"_width"],group)
    result["member_profiles"]=sections
    raw_overrides=raw.get("member_overrides", {})
    raw_materials=raw.get("member_materials", {})
    if not isinstance(raw_overrides,dict) or not isinstance(raw_materials,dict):
        raise ValueError("Opções individuais das travessas inválidas.")
    if len(raw_overrides)>32 or any(member_family(key) is None or
            (key.startswith(("transom_","mullion_")) and not 1 <= int(key.split("_")[1]) <= 7)
            for key in raw_overrides):
        raise ValueError("Travessa individual desconhecida.")
    overrides={}
    for key,item in raw_overrides.items():
        if not isinstance(item,dict):raise ValueError("Travessa individual inválida.")
        family=member_family(key)
        width_=_numeric(item,"width",result[("stile_width" if key.startswith("stile_") else
                    "mullion_width" if key.startswith("mullion_") else family+"_width")])
        if width_>.5:raise ValueError("Largura da travessa excessiva.")
        profile=_check_member_profile(item.get("profile",sections[family]),
                                     leaf_thickness,width_,family)
        overrides[key]={"width":width_, "profile":profile}
        if "material" in item:
            if not (item["material"] is None or isinstance(item["material"],dict)):
                raise ValueError("Material individual inválido.")
            overrides[key]["material"]=copy.deepcopy(item["material"])
    result["member_overrides"]=overrides
    if any(key not in ("rail","transom") or
           not (value is None or isinstance(value,dict))
           for key,value in raw_materials.items()):
        raise ValueError("Material de grupo de travessa inválido.")
    result["member_materials"]=copy.deepcopy(raw_materials)
    cols, rows = result["columns"], result["rows"]
    left, right, mullions = horizontal_and_vertical_sizes(result)
    bottom = resolved_member(result,"rail_bottom")["width"] if result["rails_enabled"] else 0.
    top = resolved_member(result,"rail_top")["width"] if result["rails_enabled"] else 0.
    transoms = [resolved_member(result,f"transom_{r}")["width"] for r in range(1,rows)]
    usable_w = width - left - right - sum(mullions)
    usable_h = (height - (result["top_arc_rise"] if result["top_arc_enabled"] else 0)
                - bottom - top - sum(transoms))
    if result["mode"] == "grid" and (usable_w < cols*.02 or usable_h < rows*.02):
        raise ValueError("A estrutura ou o arco excede o espaço disponível.")
    cells = raw.get("cell_types")
    if cells is None:
        cells = (DEFAULT_GRID["cell_types"] if cols == 2 and rows == 3
                 else ["glass"]*(cols*rows))
    if not isinstance(cells, (list, tuple)) or len(cells) != cols*rows:
        raise ValueError("Número de painéis diferente da malha da folha.")
    if any(cell not in PANEL_KINDS for cell in cells):
        raise ValueError("Tipo de painel desconhecido.")
    result["cell_types"] = list(cells)

    insert_raw = raw.get("insert", DEFAULT_GRID["insert"])
    if not isinstance(insert_raw, dict):
        raise ValueError("Visor deslocável inválido.")
    insert = {}
    for key in ("width", "height", "x", "z", "frame_width"):
        insert[key] = _numeric(insert_raw, key, DEFAULT_GRID["insert"][key],
                               low=-1.0 if key in ("x", "z") else 0.0)
    for key in ("x", "z"):
        if not 0 <= insert[key] <= 1:
            raise ValueError("A posição do visor deve ficar entre 0% e 100%.")
    insert["kind"] = insert_raw.get("kind", "glass")
    if insert["kind"] not in PANEL_KINDS:
        raise ValueError("Preenchimento do visor inválido.")
    insert["frame_enabled"] = insert_raw.get("frame_enabled", True)
    if type(insert["frame_enabled"]) is not bool:
        raise ValueError("Exibição da moldura do visor inválida.")
    if result["mode"] == "inset":
        x0 = width*insert["x"] - insert["width"]/2
        z0 = height*insert["z"] - insert["height"]/2
        if (x0 < .015 or x0+insert["width"] > width-.015 or
                z0 < .015 or z0+insert["height"] > height-.015):
            raise ValueError("Visor fora da folha: ajuste X, Z, largura ou altura.")
        if insert["frame_enabled"] and insert["frame_width"]*2 >= min(insert["width"],insert["height"]):
            raise ValueError("A moldura não pode fechar a abertura do visor.")
        if result["top_arc_enabled"]:
            if z0+insert["height"] > min(arc_height(result, width, height, x0),
                                          arc_height(result,width,height,x0+insert["width"])) - .015:
                raise ValueError("Visor ultrapassa o limite do arco superior.")
    result["insert"] = insert

    uniforms = raw.get("uniform_materials", DEFAULT_GRID["uniform_materials"])
    kinds = raw.get("kind_materials", {})
    parts = raw.get("part_materials", {})
    if not isinstance(uniforms, dict) or not isinstance(kinds, dict) or not isinstance(parts, dict):
        raise ValueError("Materiais: configuração inválida.")
    result["uniform_materials"] = {}
    for group in MATERIAL_GROUPS:
        enabled = uniforms.get(group, True)
        if type(enabled) is not bool:
            raise ValueError("Materiais: uniformidade inválida.")
        result["uniform_materials"][group] = enabled
    for mapping in (kinds, parts):
        if len(mapping) > 256 or any(not isinstance(k, str) or len(k)>100
                                     or not (v is None or isinstance(v, dict))
                                     for k,v in mapping.items()):
            raise ValueError("Materiais por peça inválidos.")
    result["kind_materials"] = copy.deepcopy(kinds)
    result["part_materials"] = copy.deepcopy(parts)
    return result


def arc_height(grid, width, height, x):
    if not grid.get("top_arc_enabled", False):
        return height
    rise = grid["top_arc_rise"]
    radius = width*width/(8*rise) + rise/2
    center = height-radius
    return center + math.sqrt(max(0.,radius*radius-(x-width/2)**2))


def _rect(xa, xb, za, zb):
    return ((xa,za), (xb,za), (xb,zb), (xa,zb))


def _cap(poly, grid, width, height, inset=0.0):
    """Clip axis-aligned member polygon under sampled circular upper edge."""
    if not grid.get("top_arc_enabled", False):
        return tuple(poly)
    xa, xb = min(p[0] for p in poly), max(p[0] for p in poly)
    za, zb = min(p[1] for p in poly), max(p[1] for p in poly)
    count = max(2, int(math.ceil(32*(xb-xa)/width)))
    heights = [(xa+(xb-xa)*i/count,
                min(zb, arc_height(grid,width,height,xa+(xb-xa)*i/count)-inset))
               for i in range(count+1)]
    if max(v for _,v in heights) <= za+1e-8:
        return ()
    # For a circular top above the lower edge, the boundary stays one polygon.
    return tuple([(xa,za),(xb,za)] + [(x,max(za,z)) for x,z in reversed(heights)])


def leaf_shapes(grid, width, height):
    """Yield (stable part id, name, type, XZ polygon) shared by preview/mesh.

    Profiles remain separate logical elements for editing and materials.  In
    inset mode the opaque body has an actual opening (four solid regions),
    rather than a transparent decal applied to an uncut slab.
    """
    if grid.get("mode", "grid") == "inset":
        inset = grid["insert"]
        xa = width*inset["x"]-inset["width"]/2
        xb = xa+inset["width"]
        za = height*inset["z"]-inset["height"]/2
        zb = za+inset["height"]
        regions = ((0,xa,0,height), (xb,width,0,height),
                   (xa,xb,0,za), (xa,xb,zb,height))
        for i,(a,b,c,d) in enumerate(regions):
            polygon = _cap(_rect(a,b,c,d),grid,width,height)
            if polygon:
                yield ("body","Corpo liso da folha","leaf_solid",polygon)
        frame = inset["frame_width"] if inset["frame_enabled"] else 0
        if frame:
            bars = (("left",xa,xa+frame,za,zb),
                    ("right",xb-frame,xb,za,zb),
                    ("bottom",xa+frame,xb-frame,za,za+frame),
                    ("top",xa+frame,xb-frame,zb-frame,zb))
            for tag,a,b,c,d in bars:
                yield (f"insert_frame_{tag}","Perfil visor " + tag,
                       "leaf_rail" if tag in ("top","bottom") else "leaf_stile",
                       _rect(a,b,c,d))
        if inset["kind"] != "open":
            yield ("insert", "Painel deslocável", "leaf_"+inset["kind"],
                   _rect(xa+frame,xb-frame,za+frame,zb-frame))
        return

    cols,rows = grid["columns"],grid["rows"]
    sizes = member_widths(grid)
    left,right,mullions=horizontal_and_vertical_sizes(grid)
    bottom = resolved_member(grid,"rail_bottom")["width"] if grid.get("rails_enabled",True) else 0.
    top = resolved_member(grid,"rail_top")["width"] if grid.get("rails_enabled",True) else 0.
    boxes=list(cell_rectangles(grid,width,height))
    if left or right:
        for key,a,b in (("stile_left",0,left),("stile_right",width-right,width)):
            if b<=a:continue
            polygon = _cap(_rect(a,b,0,height),grid,width,height)
            if polygon:yield (key,"Montante lateral","leaf_stile",polygon)
    if bottom:
        yield ("rail_bottom","Travessa inferior","leaf_rail",
               _rect(left,width-right,0,bottom))
    if top:
        if grid.get("top_arc_enabled",False):
            n=40
            curve=[(left+(width-left-right)*i/n,arc_height(grid,width,height,left+(width-left-right)*i/n))
                   for i in range(n+1)]
            poly=tuple(curve+[(x,z-top) for x,z in reversed(curve)])
            yield ("rail_top","Travessa superior em arco","leaf_rail",poly)
        else:
            yield ("rail_top","Travessa superior","leaf_rail",
                   _rect(left,width-right,height-top,height))
    for col in range(1,cols):
        x=boxes[col-1][3]
        m=mullions[col-1]
        polygon=_cap(_rect(x,x+m,bottom,height-top),grid,width,height,
                     inset=top if grid.get("top_arc_enabled",False) else 0.)
        if polygon:yield (f"mullion_{col}",f"Montante {col}","leaf_mullion",polygon)
    for row in range(1,rows):
        previous=boxes[(row-1)*cols]
        height_previous=previous[5]
        thick=resolved_member(grid,f"transom_{row}")["width"]
        yield (f"transom_{row}",f"Travessa {row}","leaf_transom",
               _rect(left,width-right,height_previous,height_previous+thick))
    for row,col,xa,xb,za,zb in boxes:
        kind=grid["cell_types"][row*cols+col]
        if kind=="open":continue
        is_arch=grid.get("top_arc_enabled",False) and row==rows-1
        polygon=_cap(_rect(xa,xb,za,height if is_arch else zb),grid,width,height,
                     inset=top if is_arch else 0.)
        if polygon:
            yield (f"cell_{row}_{col}",f"Painel {row+1}-{col+1} ({kind})",
                   "leaf_"+kind,polygon)


def leaf_grid_parts(grid, width, height):
    """Compatibility contract yielding rectangular bounds for legacy consumers.

    For arcs, callers needing the curved outline must use ``leaf_shapes``.
    """
    for key,name,component,polygon in leaf_shapes(grid,width,height):
        xs=[p[0] for p in polygon];zs=[p[1] for p in polygon]
        yield name,component,min(xs),max(xs),min(zs),max(zs)


def part_group(component):
    if component in ("leaf_stile","leaf_rail","leaf_mullion","leaf_transom"):
        return "structure"
    return component.removeprefix("leaf_") if isinstance(component, str) else None


def grid_material(grid, part_id, component):
    """Recipe resolved by priority: linked rail family, individual part, category.

    A linked rail family overrides stale individual materials, but an unlinked
    rail is individually editable even if other structural elements are uniform.
    """
    family=member_family(part_id)
    if family:
        link=member_linked(grid,family)
        if not link:
            override=grid.get("member_overrides",{}).get(part_id,{})
            if "material" in override:
                return copy.deepcopy(override["material"])
            if part_id in grid.get("part_materials",{}):
                return copy.deepcopy(grid["part_materials"][part_id])
        group_recipe=grid.get("member_materials",{}).get(family)
        if group_recipe is not None:
            return copy.deepcopy(group_recipe)
    group=part_group(component)
    if grid.get("uniform_materials",{}).get(group,True):
        return copy.deepcopy(grid.get("kind_materials",{}).get(group))
    return copy.deepcopy(grid.get("part_materials",{}).get(part_id,
                         grid.get("kind_materials",{}).get(group)))
