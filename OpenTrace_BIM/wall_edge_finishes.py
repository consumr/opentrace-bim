# SPDX-License-Identifier: GPL-3.0-or-later
"""Cosmetic wall end/top/bottom face materials; no extra mesh or junctions.

Only the generated external faces tagged by the parametric wall motor are
painted.  Internal layers, IFC identity, dimensions and junction geometry do
not change.  Overrides are optional and remain backwards compatible.
"""
from __future__ import annotations
import copy

EDGE_FACES = ("start", "end", "top", "bottom")


class WallEdgeMaterialError(ValueError):
    """A selected material cannot be resolved to a native host material."""


def invalidate_wall_face_appearance(group):
    """Tell the IngeTrazo VBO/cache that face *attributes* changed.

    Merely incrementing scene.version is insufficient: the viewport reuses a
    group's cached chunk if mesh._mut_serial did not change and
    mesh._attrs_dirty is false. Edge painting changes no topology, therefore
    neither flag was set by the mesh's own mutation primitives. Without this,
    the material is stored on Face.attrs but remains invisible in the host.

    Do not increment _mut_serial or change geometry: marking _attrs_dirty and
    _chunk_dirty requests a single visual rebake on the next viewport update.
    """
    changed = 0
    for child in getattr(group, "children", ()) or ():
        mesh = getattr(child, "mesh", None)
        if mesh is not None:
            mesh._attrs_dirty = True
            mesh._chunk_dirty = True
            changed += 1
    return changed


def normalize_edge_finishes(raw):
    """Ignore invalid/obsolete face names and empty material choices."""
    if not isinstance(raw, dict):
        return {}
    return {key: str(raw[key]).strip() for key in EDGE_FACES
            if isinstance(raw.get(key), str) and raw[key].strip()}


def face_material_assignments(group, values):
    """Yield (face, override name, layer fallback) for external wall faces only.

    Composite children are kept separate for a reliable default fallback.
    No geometric changes are made, even when a wall is skewed or intersected.
    """
    finishes = normalize_edge_finishes(values.get("edge_materials"))
    structure = values.get("structure")
    layers = values.get("layers") or () if structure == "composite" else ()
    for index, child in enumerate(getattr(group, "children", ()) or ()):
        fallback = (layers[index].get("material_name")
                    if index < len(layers) and isinstance(layers[index], dict)
                    else values.get("material_name"))
        for face in getattr(getattr(child, "mesh", None), "faces", ()) or ():
            key = (getattr(face, "attrs", None) or {}).get("ap_wall_side")
            if key in EDGE_FACES:
                yield face, finishes.get(key), fallback


def validate_edge_materials(scene, finishes):
    """Fail before a history command mutates project metadata or face paint."""
    from .materials import material_face_attrs
    recipes = {}
    for name in set(normalize_edge_finishes(finishes).values()):
        attrs = material_face_attrs(scene, name)
        if attrs is None:
            raise WallEdgeMaterialError(
                f"Material not available for wall edge finish: {name}")
        recipes[name] = attrs
    return recipes


def stamp_wall_edge_finishes(group, scene, values, *, restore_defaults=False):
    """Paint requested native material attrs and invalidate the host VBO.

    All requested override materials are resolved before changing any face:
    a missing material must never silently erase the former coating. The
    fallback is only used when an explicit override is removed.
    """
    finishes = normalize_edge_finishes(values.get("edge_materials"))
    if not finishes and not restore_defaults:
        return 0
    from .materials import material_face_attrs, _MATERIAL_KEYS

    # Resolve/validate before touching a face, including in the create path.
    recipes = validate_edge_materials(scene, finishes)

    changed = 0
    for face, override, fallback in face_material_assignments(group, values):
        if not override and not restore_defaults:
            continue
        name = override if override else fallback
        attrs = recipes[name] if override else (material_face_attrs(scene, name) if name else None)
        old = getattr(face, "attrs", None)
        if old is None:
            continue
        for key in _MATERIAL_KEYS:
            old.pop(key, None)
        if attrs is not None:
            old.update(copy.deepcopy(attrs))
        changed += 1
    if changed:
        invalidate_wall_face_appearance(group)
    elif finishes:
        raise WallEdgeMaterialError(
            "No generated wall edge faces were found. Cannot apply the selected material.")
    return changed
