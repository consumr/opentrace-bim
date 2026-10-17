# SPDX-License-Identifier: GPL-3.0-or-later
"""Placing openings, doors and windows on a wall, and drawing free openings.

Like Archicad: choose the tool, hover any wall and the opening slides along it
under the cursor; one click places it and the tool stays ready for the next.
No wall has to be selected first. Sizes come from presets per kind.
"""
from __future__ import annotations

import copy
import math
import uuid

from PySide6.QtGui import QVector3D
from tools.base import Tool

from . import wall_cache
from .bim import new_ifc_guid
from .commands import EditWall
from .door_window_commands import CreateHostedFill
from .door_window_core import (normalize_fill, opening_request,
                               check_hosted_clearance, FillError)
from .model import WallError, path_world, read_wall, wall_opening_intervals, wall_path_kind, wall_record
from .slab_edit import _preview_lines
from .slab_model import SlabError, line_edge
from .wall_face import WallFace
from .wall_opening_edit import ANCHOR_SHIFT, execute, sheet_lines

# Starting sizes per kind, in metres: width (diameter for a circle), height, sill.
PRESETS = {
    "rect": {"width": 1.00, "height": 1.20, "sill": 0.90},
    "square": {"width": 0.60, "height": 0.60, "sill": 1.50},
    "circle": {"width": 0.60, "height": 0.60, "sill": 1.30},
    "door": {"width": 0.80, "height": 2.10, "sill": 0.00},
    "window": {"width": 1.20, "height": 1.20, "sill": 1.00},
}
KIND_NAMES = {"rect": "Abertura", "square": "Abertura quadrada", "circle": "Abertura circular",
              "door": "Porta", "window": "Janela"}
_ARC_45 = 1.0 - math.cos(math.pi / 4.0)


def _fmt(value):
    return f"{value:.2f}".replace(".", ",")


def opening_record(kind, start, size):
    """New wall opening record whose left edge sits at station ``start``."""
    width, height, sill = size["width"], size["height"], size["sill"]
    if kind == "circle":
        r = width / 2.0
        cs, cz = start + r, sill + r
        h = -r * _ARC_45  # negative: bulge outward on a counter-clockwise ring
        return {"id": uuid.uuid4().hex, "kind": "polygon",
                "polygon": [[cs, cz - r], [cs + r, cz], [cs, cz + r], [cs - r, cz]],
                "edges": [{"type": "arc", "sagitta": h} for _ in range(4)],
                "source_id": None, "ifc_global_id": new_ifc_guid()}
    return {"id": uuid.uuid4().hex, "kind": "rect", "position": start + width / 2.0,
            "width": width, "height": height, "sill": sill,
            "source_id": None, "ifc_global_id": new_ifc_guid()}


def _record_outline(item):
    if item["kind"] == "polygon":
        pts = [QVector3D(s, z, 0) for s, z in item["polygon"]]
        return pts, [dict(e) for e in item["edges"]]
    s0 = item["position"] - item["width"] / 2.0
    s1 = s0 + item["width"]
    z0, z1 = item["sill"], item["sill"] + item["height"]
    pts = [QVector3D(s0, z0, 0), QVector3D(s1, z0, 0), QVector3D(s1, z1, 0), QVector3D(s0, z1, 0)]
    return pts, [line_edge() for _ in pts]


def opening_wire(face, pts, specs):
    """Both faces of an outline plus depth lines at the corners."""
    near = sheet_lines(face, _preview_lines(pts, specs), "near")
    far = sheet_lines(face, _preview_lines(pts, specs), "far")
    depth = [(face.world(p, "near"), face.world(p, "far")) for p in pts]
    return near + far + depth


def _face(scene, wall):
    return wall_cache.memo(scene, ("wall_face", wall), lambda: WallFace(wall))


def wall_under_cursor(viewport, ctx, tolerance=0.02):
    """The wall whose face the cursor is on.

    The viewport puts the hovered point on the face under the cursor; find the
    wall that point lies on. Asking the host which group is under the pixel
    returned nothing for walls (their faces live in child groups).
    """
    point = ctx.world
    scene = viewport.scene
    best = None
    for wall in scene.groups:
        if (wall_record(wall) is None or not scene.entity_selectable(wall)
                or not scene.entity_visible(wall)):
            continue
        try:
            if wall_path_kind(wall) not in ("line", "arc"):
                continue
            face = _face(scene, wall)
        except WallError:
            continue
        sheet = face.sheet(point)
        s = sheet.x()
        if not (-tolerance <= s <= face.length + tolerance):
            continue
        near = face.world(QVector3D(s, sheet.y(), 0), "near")
        far = face.world(QVector3D(s, sheet.y(), 0), "far")
        across = far - near
        span = across.length()
        if span <= 1e-9:
            continue
        u = QVector3D.dotProduct(point - near, across) / (span * span)
        if u < -tolerance / span or u > 1 + tolerance / span:
            continue
        off = (point - (near + across * max(0.0, min(1.0, u)))).length()
        if off > tolerance or not -tolerance <= sheet.y() <= face.height_at(s) + tolerance:
            continue
        if best is None or off < best[0]:
            best = (off, wall)
    return None if best is None else best[1]


class _OnAnyWall(Tool):
    uses_snap = True
    wireframe_color = (0.91, 0.55, 0.14, 1.0)

    def __init__(self, controller):
        self.controller = controller
        self.wall = None
        self.face = None
        self._face_key = None

    def _face_for(self, viewport, wall):
        key = (id(wall), viewport.scene.version)
        if key != self._face_key:
            self.face = WallFace(wall)
            self._face_key = key
        self.wall = wall
        return self.face

    def _sheet(self, ctx):
        snap = getattr(ctx, "snap", None)
        world = snap.point if snap is not None and getattr(snap, "point", None) is not None else ctx.world
        return self.face.sheet(world)


class PlaceWallOpeningTool(_OnAnyWall):
    """One click places an opening, door or window on the wall under the cursor."""

    vcb_label = "Posição"

    def __init__(self, controller, kind="rect"):
        super().__init__(controller)
        self.anchor = "center"
        self.host_face = "left"
        self.door_as_opening = False  # Door tool: optional wall cut without leaf/frame.
        self.door_style_key = "plain_solid"
        self.door_family_key = "swing_single"
        self.door_leaf_grid = None
        self.door_variant = 'grid'
        self.door_grooves = {}
        self.door_slide_side = "left"
        self.door_hinge = "left"
        self.door_swing = 1
        self.sizes = copy.deepcopy(PRESETS)
        self.item = None
        self.station = None
        self._prepared_spec = None
        self._candidate_error = None
        self.set_kind(kind)

    def set_kind(self, kind):
        if kind not in PRESETS:
            raise WallError("Tipo de abertura desconhecido.")
        self.kind = kind
        self.name = KIND_NAMES[kind]
        self.description = f"{KIND_NAMES[kind]}: passe sobre a parede e clique."
        self.item = None
        self._prepared_spec = None
        self._candidate_error = None

    def on_activate(self, viewport):
        label = ("Vão de porta" if self.kind == "door" and self.door_as_opening
                 else KIND_NAMES[self.kind])
        self.controller.message(
            f"{label}: passe o mouse sobre uma parede e clique para colocar; "
            "digite a distância do início da parede para posicionar exato. Esc encerra.")

    def on_deactivate(self, viewport):
        self.wall = self.face = self.item = self.station = self._prepared_spec = self._candidate_error = None
        self._face_key = None
        viewport.update()

    def _new_fill_spec(self, station, *, opening_id=None, fill_id=None):
        """Single spec used by preview, validation, typed value and creation."""
        size=self.sizes[self.kind]
        raw={
            "schema":2,"id":fill_id or uuid.uuid4().hex,
            "host_id":str(self.wall.uid),"opening_id":opening_id or uuid.uuid4().hex,
            "kind":"door","anchor":self.anchor,"position":float(station),
            "width":size["width"],"height":size["height"],"sill":size["sill"],
            "family_key":self.door_family_key,"host_face":self.host_face,
            "f01_layout":"physical","leaf_variant":getattr(self,"door_variant","grid"),
            "slide_side":self.door_slide_side,"hinge":self.door_hinge,"swing":self.door_swing,
        }
        if getattr(self,'door_variant','grid') == 'grooved':
            raw.update(getattr(self,'door_grooves',{}))
        if self.door_family_key == "sliding_pocket":
            raw["pocket_layout"]="sleeve"  # New V8 insert only; never migrate old V7 records.
        from .door_leaf_presets import make_leaf_preset
        try:
            from .door_leaf_grid import normalize_leaf_grid
            if self.door_leaf_grid is None: raise ValueError('Use o estilo selecionado')
            raw["leaf_grid"]=normalize_leaf_grid(
                self.door_leaf_grid,size["width"],size["height"],.035)
        except (ValueError,TypeError):
            raw["leaf_grid"]=make_leaf_preset(
                self.door_style_key,size["width"],size["height"],.035)
        return normalize_fill(raw)

    def _candidate(self, station):
        size=self.sizes[self.kind]
        if self.kind == "door" and not self.door_as_opening:
            spec=self._new_fill_spec(station)
            self._prepared_spec=spec
            return opening_request(spec, opening_guid=new_ifc_guid())
        self._prepared_spec=None
        start=station-ANCHOR_SHIFT[self.anchor]*size["width"]
        return opening_record(self.kind,start,size)

    def _check(self, item):
        values=read_wall(self.wall)
        if self._prepared_spec is not None and item.get('source_id') == self._prepared_spec['id']:
            from .model import _path_cumulative
            _points,cumulative=_path_cumulative(path_world(self.wall))
            check_hosted_clearance(self._prepared_spec,cumulative[-1])
        values["openings"]=list(values.get("openings",[]))+[copy.deepcopy(item)]
        wall_opening_intervals(values,path_world(self.wall))
        return values

    def on_hover(self, ctx):
        self._candidate_error = None
        wall = wall_under_cursor(ctx.viewport, ctx)
        if wall is None:
            self.item = None
        else:
            try:
                self._face_for(ctx.viewport, wall)
                local = self._sheet(ctx)
                self.station = local.x()
                # Choose the actual hovered finished face, not a snap
                # reference that may belong to another element.
                point = ctx.world
                near = self.face.world(local, "near")
                far = self.face.world(local, "far")
                self.host_face = ("left" if (point-near).length() <=
                                  (point-far).length() else "right")
                self.item = self._candidate(self.station)
            except (WallError, FillError, ValueError, TypeError) as exc:
                self.item = None
                self._prepared_spec = None
                self._candidate_error = str(exc)
        ctx.viewport.update()

    def _place(self, viewport, item):
        values = self._check(item)
        if self.kind in ("door", "window") and not (self.kind == "door" and self.door_as_opening):
            size = self.sizes[self.kind]
            if self.kind == 'door':
                spec=self._prepared_spec
                if spec is None or spec['id'] != item.get('source_id'):
                    raise FillError('Candidato de porta desatualizado; mova o cursor e tente novamente.')
                command=CreateHostedFill(viewport.scene,self.wall,spec)
                execute(viewport,command)
                self.controller.message('Porta inserida.')
                self.controller.select_opening(self.wall,item['id'])
                self.controller.return_to_select()
                return
            start = item["position"] - item["width"] / 2.0
            raw = {
                "schema": 2 if self.kind == "door" else 1,
                "id": uuid.uuid4().hex, "host_id": str(self.wall.uid), "opening_id": item["id"],
                "kind": self.kind, "anchor": self.anchor,
                "family_key": "swing_single" if self.kind == "door" else None,
                "position": start + ANCHOR_SHIFT[self.anchor] * item["width"],
                "width": size["width"], "height": size["height"], "sill": size["sill"],
            }
            if self.kind == "door":
                from .door_leaf_presets import make_leaf_preset
                raw["host_face"] = self.host_face
                raw["family_key"] = self.door_family_key
                raw["leaf_variant"] = "grid"
                raw["f01_layout"] = "physical"
                # The edit template may have another size. Revalidate against
                # the current insertion dimensions, falling back to its style.
                try:
                    if self.door_leaf_grid is None:
                        raise ValueError("Sem rascunho; usar estilo selecionado.")
                    from .door_leaf_grid import normalize_leaf_grid
                    raw["leaf_grid"] = normalize_leaf_grid(
                        self.door_leaf_grid, size["width"], size["height"], .035)
                except (ValueError, TypeError):
                    raw["leaf_grid"] = make_leaf_preset(
                        self.door_style_key, size["width"], size["height"], .035)
                raw["slide_side"] = self.door_slide_side
                raw["hinge"] = self.door_hinge
                raw["swing"] = self.door_swing
            spec = normalize_fill(raw)
            command = CreateHostedFill(viewport.scene, self.wall, spec)
        else:
            if self.kind == "door" and self.door_as_opening:
                # Wall stores the role across edits and native undo/redo; IFC
                # exports it correctly as an unfilled IfcOpeningElement.
                item["purpose"] = "door"
                values["openings"][-1]["purpose"] = "door"
            command = EditWall(viewport.scene, self.wall, values)
        execute(viewport, command)
        label = "Vão de porta" if self.kind == "door" and self.door_as_opening else KIND_NAMES[self.kind]
        self.controller.message(f"{label} inserido(a).")
        self.controller.select_opening(self.wall, item["id"])
        # A door is a one-click object. Leave the placement tool after a
        # successful insertion so the preview no longer follows the mouse.
        # Other opening/window tools keep their original repeat workflow.
        if self.kind == "door":
            self.controller.return_to_select()

    def on_click(self, ctx):
        try:
            self.on_hover(ctx)
            if self.item is None:
                raise WallError(self._candidate_error or
                                "Não foi possível preparar a abertura nesta parede; confira o estilo e as medidas.")
            self._place(ctx.viewport, self.item)
            ctx.viewport.update()
            return True
        except (WallError, SlabError, ValueError) as exc:
            self.controller.message(str(exc), error=True)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception('Erro ao inserir esquadria hospedada')
            self.controller.message('Erro interno na inserção: '+str(exc), error=True)
        ctx.viewport.update()
        return False

    def on_value(self, viewport, value):
        try:
            if self.wall is None:
                raise WallError("Passe o mouse sobre a parede antes de digitar a posição.")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise WallError("Digite a distância do início da parede.")
            self._place(viewport, self._candidate(float(value)))
            return True
        except (WallError, SlabError, ValueError) as exc:
            self.controller.message(str(exc), error=True)
            return False

    def rubber_band_lines(self):
        if self.item is None or self.face is None:
            return []
        return opening_wire(self.face, *_record_outline(self.item))

    def value_label(self):
        if self.item is None or self.face is None:
            return None
        pts, _specs = _record_outline(self.item)
        s0 = min(p.x() for p in pts)
        s1 = max(p.x() for p in pts)
        bottom = QVector3D((s0 + s1) / 2.0, min(p.y() for p in pts), 0)
        return (f"← {_fmt(s0)}   {_fmt(self.face.length - s1)} →", self.face.world(bottom))

    def on_cancel(self, viewport):
        self.controller.return_to_select()


class DrawWallOpeningTool(_OnAnyWall):
    """Free opening: click its corners on a wall face; click the first to close."""

    name = "Desenhar abertura livre"
    description = "Desenhar uma abertura poligonal na face de uma parede."
    CLOSE_PX = 10.0

    def __init__(self, controller):
        super().__init__(controller)
        self.points = []
        self.hover = None

    def on_activate(self, viewport):
        self.points, self.hover = [], None
        self.controller.message("Clique os cantos da abertura na face da parede; "
                                "clique no primeiro para fechar. Esc cancela.")

    def on_deactivate(self, viewport):
        self.points, self.hover, self.wall, self.face = [], None, None, None
        self._face_key = None
        viewport.update()

    @property
    def start_point(self):
        return self.face.world(self.points[-1]) if self.points and self.face else None

    def drag_plane(self, viewport):
        if not self.points or self.face is None:
            return None
        return self.face.tangent_plane(self.points[-1].x(), self.points[-1].y())

    def on_hover(self, ctx):
        if not self.points:
            wall = wall_under_cursor(ctx.viewport, ctx)
            if wall is None:
                self.hover = None
                ctx.viewport.update()
                return
            self._face_for(ctx.viewport, wall)
        self.hover = self._sheet(ctx)
        ctx.viewport.update()

    def _closes(self, ctx):
        if len(self.points) < 3:
            return False
        first = ctx.viewport._world_to_pixel(self.face.world(self.points[0]))
        return first is not None and math.hypot(ctx.screen.x() - first[0],
                                                ctx.screen.y() - first[1]) <= self.CLOSE_PX

    def on_click(self, ctx):
        try:
            if not self.points:
                wall = wall_under_cursor(ctx.viewport, ctx)
                if wall is None:
                    raise WallError("Comece clicando sobre a face de uma parede.")
                self._face_for(ctx.viewport, wall)
            if self._closes(ctx):
                self._commit(ctx.viewport)
            else:
                self.points.append(self._sheet(ctx))
        except (WallError, SlabError, ValueError) as exc:
            self.controller.message(str(exc), error=True)
        ctx.viewport.update()

    def _commit(self, viewport):
        item = {"id": uuid.uuid4().hex, "kind": "polygon",
                "polygon": [[p.x(), p.y()] for p in self.points],
                "edges": [{"type": "line"} for _ in self.points],
                "source_id": None, "ifc_global_id": new_ifc_guid()}
        values = read_wall(self.wall)
        values["openings"] = list(values.get("openings", [])) + [item]
        execute(viewport, EditWall(viewport.scene, self.wall, values))
        self.controller.message("Abertura livre criada.")
        wall = self.wall
        self.points, self.hover = [], None
        self.controller.select_opening(wall, item["id"])

    def rubber_band_lines(self):
        if self.face is None:
            return []
        chain = self.points + ([self.hover] if self.hover is not None else [])
        lines = list(zip(chain, chain[1:]))
        if len(chain) >= 3:
            lines.append((chain[-1], chain[0]))
        return sheet_lines(self.face, lines)

    def on_cancel(self, viewport):
        if self.points:
            self.points, self.hover = [], None
            viewport.update()
        else:
            self.controller.return_to_select()


SHAPES = ("rect", "square", "circle", "free")


class WallOpeningTool(Tool):
    """The Opening tool: places or draws an opening in the chosen shape.

    The host sees one tool. The shape picks which inner tool does the work, and
    changing it never changes the host tool. The inner tools keep the last sizes
    and anchor of the session; each placed opening keeps its own in its record.
    """

    name = "Abertura"
    description = "Abertura na parede: passe sobre a parede e clique."

    def __init__(self, controller):
        self.shape = "rect"
        self.place = PlaceWallOpeningTool(controller, self.shape)
        self.draw = DrawWallOpeningTool(controller)
        self.viewport = None

    @property
    def current(self):
        return self.draw if self.shape == "free" else self.place

    def set_shape(self, shape):
        if shape not in SHAPES:
            raise WallError("Forma de abertura desconhecida.")
        if shape == self.shape:
            return
        if self.viewport is not None:
            self.current.on_deactivate(self.viewport)
        self.shape = shape
        if shape != "free":
            self.place.set_kind(shape)
        if self.viewport is not None:
            self.current.on_activate(self.viewport)

    def on_activate(self, viewport):
        self.viewport = viewport
        self.current.on_activate(viewport)

    def on_deactivate(self, viewport):
        self.current.on_deactivate(viewport)
        self.viewport = None

    @property
    def uses_snap(self):
        return self.current.uses_snap

    @property
    def wireframe_color(self):
        return self.current.wireframe_color

    @property
    def vcb_label(self):
        return self.current.vcb_label

    @property
    def start_point(self):
        return getattr(self.current, "start_point", None)

    def value_label(self):
        label = getattr(self.current, "value_label", None)
        return None if label is None else label()

    def drag_plane(self, viewport):
        return self.current.drag_plane(viewport)

    def on_click(self, ctx):
        self.current.on_click(ctx)

    def on_hover(self, ctx):
        self.current.on_hover(ctx)

    def on_double_click(self, ctx):
        self.current.on_double_click(ctx)

    def on_triple_click(self, ctx):
        self.current.on_triple_click(ctx)

    def on_box_select(self, viewport, rect, crossing, additive=False, mode=None):
        self.current.on_box_select(viewport, rect, crossing, additive, mode)

    def on_cancel(self, viewport):
        self.current.on_cancel(viewport)

    def on_release(self, viewport):
        self.current.on_release(viewport)

    def on_key(self, viewport, key, modifiers):
        return self.current.on_key(viewport, key, modifiers)

    def on_value(self, viewport, value):
        return self.current.on_value(viewport, value)

    def status_clause(self):
        return self.current.status_clause()

    def rubber_band_lines(self):
        return self.current.rubber_band_lines()

    def guide_preview_lines(self):
        return self.current.guide_preview_lines()

    def inference_guide_lines(self):
        return self.current.inference_guide_lines()

    def preview_faces(self):
        return self.current.preview_faces()
