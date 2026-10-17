# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only wall visualizations; never modify host geometry or material data."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QPixmap, QTransform
from PySide6.QtWidgets import QWidget


def layer_appearance(layer):
    """A conservative visual swatch for a layer; not a material assignment."""
    name=(str(layer.get('material_name') or '')+' '+str(layer.get('name') or '')).casefold()
    if 'clay' in name or 'brick' in name: return QColor('#b86e52')
    if 'concrete block' in name: return QColor('#a8a5a0')
    if 'steel' in name or 'stud' in name: return QColor('#82939d')
    if 'insulation' in name: return QColor('#d8bd71')
    if 'tile' in name or 'ceramic' in name: return QColor('#e6d8bc')
    if 'gypsum' in name: return QColor('#f0e9e1')
    if 'render' in name or 'plaster' in name: return QColor('#d9d1bd')
    if 'adhesive' in name or 'mortar' in name: return QColor('#bab6a8')
    return QColor('#abb7bd')


def stack_segments(layers):
    """Pure model: normalized band boundaries from exterior to interior."""
    good=[layer for layer in (layers or ()) if isinstance(layer,dict)]
    weights=[max(0.,float(layer.get('thickness',0) or 0)) for layer in good]
    total=sum(weights)
    if not total:return []
    out=[];pos=0.
    for layer,weight in zip(good,weights):
        nxt=pos+weight/total
        out.append((pos,min(1.,nxt),layer))
        pos=nxt
    return out


class LayerStackPreview(QWidget):
    """Section of the exact current physical layers for Layer Composer."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self._layers=[]
        self.setMinimumHeight(112)
        self.setMaximumHeight(134)
        self.setToolTip('Preview: exterior → interior. Thicknesses reflect the current composition.')

    def set_layers(self,layers):
        self._layers=list(layers or ())
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing,True)
        r=self.rect()
        p.setPen(QColor('#9ba3aa'))
        p.drawText(10,14,'EXTERIOR')
        right='INTERIOR'
        p.drawText(max(10,r.width()-p.fontMetrics().horizontalAdvance(right)-10),14,right)
        bands=stack_segments(self._layers)
        if not bands:
            p.drawText(r,Qt.AlignCenter,'No physical layers')
            p.end();return
        x0=10;y0=23;wide=max(50,r.width()-20);high=62
        # Draw exact relative widths. One-pixel bands remain detectable.
        for i,(start,end,layer) in enumerate(bands):
            x=x0+round(start*wide);xr=x0+round(end*wide)
            if xr<=x:xr=x+1
            box=QRectF(x,y0,xr-x,high)
            p.fillRect(box,layer_appearance(layer))
            p.setPen(QColor('#647078'));p.drawRect(box)
            if xr-x>38:
                p.setPen(QColor('#182026'))
                text=str(i+1)
                p.drawText(box,Qt.AlignCenter,text)
        p.setPen(QColor('#b1b4ba'))
        names='  ·  '.join(f"{i+1} {layer.get('name','Layer')}" for i,(_,_,layer) in enumerate(bands))
        metrics=p.fontMetrics()
        names=metrics.elidedText(names,Qt.ElideRight,max(50,r.width()-20))
        p.drawText(10,min(r.height()-6,y0+high+18),names)
        p.end()


def _quad(points):
    return QPolygonF([QPointF(*pt) for pt in points])


def _surface_texture(layer,scene=None):
    name=layer.get('material_name') if isinstance(layer,dict) else None
    if not name:return None
    try:
        from .materials import _opentrace_default_catalog
        definition=_opentrace_default_catalog().get(str(name))
        if definition is None and scene is not None:
            obj=getattr(scene,'materials',{}).get(name)
            definition={'texture':getattr(obj,'texture',None)} if obj else None
        tex=(definition or {}).get('texture') or {}
        path=Path(str(tex.get('path') or ''))
        if path.is_file():
            pix=QPixmap(str(path))
            if not pix.isNull():return pix
    except (OSError,TypeError,ValueError):pass
    return None


def paint_isometric_wall(p,record,scene,width,height):
    """Compact wall sample: show outer/back faces, top and exposed layer end."""
    cfg=(record.get('data') or {}).get('config') or (record.get('data') or {})
    layers=cfg.get('layers') if isinstance(cfg.get('layers'),list) else []
    if not layers: layers=[{'name':record.get('name','Wall'),
                            'material_name':cfg.get('material_name'),
                            'thickness':cfg.get('thickness',.15)}]
    scale=min(width/290.,height/190.)
    # Front face, direction axis, and depth axis (axonometric projection).
    front=[(40*scale,55*scale),(218*scale,90*scale),
           (218*scale,168*scale),(40*scale,133*scale)]
    offset=(31*scale,-19*scale)
    back=[(x+offset[0],y+offset[1]) for x,y in front]
    p.setPen(QPen(QColor('#52616b'),1.3))
    p.setBrush(layer_appearance(layers[-1]))
    p.drawPolygon(_quad(back))
    p.setBrush(QColor('#c6bdb1'))
    p.drawPolygon(_quad([back[0],back[1],front[1],front[0]]))
    exterior=layers[0]
    p.setBrush(layer_appearance(exterior))
    polygon=_quad(front)
    p.drawPolygon(polygon)
    texture=_surface_texture(exterior,scene)
    if texture is not None:
        # Project texture along the *wall's plane*, not an axis-aligned
        # rectangle clipped to a sloped polygon (which distorted mortar lines).
        tw = max(1, texture.width())
        th = max(1, texture.height())
        origin = front[0]
        axis_u = front[1]
        axis_v = front[3]
        transform = QTransform(
            (axis_u[0]-origin[0])/tw, (axis_u[1]-origin[1])/tw, 0,
            (axis_v[0]-origin[0])/th, (axis_v[1]-origin[1])/th, 0,
            origin[0], origin[1], 1)
        p.save()
        p.setTransform(transform, combine=True)
        p.drawPixmap(QRectF(0, 0, tw, th), texture, QRectF(texture.rect()))
        p.restore()
        p.setBrush(Qt.NoBrush);p.drawPolygon(polygon)
    # Exposed end shows real layer thickness ordering.
    segments=stack_segments(layers)
    ftop=front[1];fbottom=front[2];btop=back[1];bbottom=back[2]
    for _,(a,b,layer) in enumerate(segments):
        dx0=offset[0]*a;dy0=offset[1]*a
        dx1=offset[0]*b;dy1=offset[1]*b
        stripe=[(ftop[0]+dx0,ftop[1]+dy0), (ftop[0]+dx1,ftop[1]+dy1),
                (fbottom[0]+dx1,fbottom[1]+dy1), (fbottom[0]+dx0,fbottom[1]+dy0)]
        p.setBrush(layer_appearance(layer));p.drawPolygon(_quad(stripe))
    # Mark the exterior and interior for material interpretation.
    p.setPen(QColor('#45515d'))
    p.drawText(QRectF(0,height-17,width/2,16),Qt.AlignCenter,'EXTERIOR')
    p.drawText(QRectF(width/2,height-17,width/2,16),Qt.AlignCenter,'INTERIOR')
