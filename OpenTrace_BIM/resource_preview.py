# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, lazy 2D preview of a resource *definition*, not a mesh renderer."""
from pathlib import Path
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtCore import QPointF, QRectF, Qt


def _pen(p,color='#455968',width=2):
    p.setPen(QPen(QColor(color),width))


def preview_resource(record, *, scene=None, size=(280,190)):
    width,height=size
    pix=QPixmap(width,height);pix.fill(QColor('#e9edf0'))
    p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing,True)
    kind=record.get('kind',''); data=record.get('data') or {}
    cfg=data.get('config',data)
    if not isinstance(cfg,dict):cfg={}
    margin=26
    try:
        if kind=='material':
            recipe=cfg
            if scene is not None and not (('color' in cfg) or ('texture' in cfg)):
                from .materials import material_catalog
                recipe=material_catalog(scene).get(record.get('name'),cfg)
            texture=recipe.get('texture') if isinstance(recipe,dict) else None
            image=Path(str(texture.get('path',''))) if isinstance(texture,dict) else None
            if image is not None and image.is_file():
                thumb=QPixmap(str(image))
                if not thumb.isNull():
                    thumb=thumb.scaled(width-2*margin,height-2*margin,Qt.KeepAspectRatio,Qt.SmoothTransformation)
                    p.drawPixmap((width-thumb.width())//2,(height-thumb.height())//2,thumb)
                    return pix
            color=recipe.get('color') if isinstance(recipe,dict) else None
            if isinstance(color,(list,tuple)) and len(color)>=3:
                v=[float(x) for x in color[:3]]
                rgb=[int(max(0,min(255,x*255 if x<=1 else x))) for x in v]
                brush=QColor(*rgb)
            else:brush=QColor('#bdc4ca')
            p.setBrush(brush);_pen(p)
            p.drawRoundedRect(QRectF(margin,margin,width-2*margin,height-2*margin),8,8)
        elif kind=='profile' and isinstance(cfg.get('loops'),list):
            loops=cfg['loops'];points=[]
            for loop in loops:
                if isinstance(loop,dict):points.extend(loop.get('points',[]))
            if points:
                xs=[float(v[0]) for v in points];ys=[float(v[1]) for v in points]
                dx=max(max(xs)-min(xs),.001);dy=max(max(ys)-min(ys),.001)
                sc=min((width-2*margin)/dx,(height-2*margin)/dy)
                for loop in loops:
                    if not isinstance(loop,dict):continue
                    poly=QPolygonF([QPointF(width/2+(float(pt[0])-(min(xs)+max(xs))/2)*sc,
                                             height/2-(float(pt[1])-(min(ys)+max(ys))/2)*sc)
                                     for pt in loop.get('points',[])])
                    _pen(p);p.setBrush(QColor('#b4ccd3') if not loop.get('hole') else QColor('#e9edf0'))
                    p.drawPolygon(poly)
        elif kind=='wall':
            from .wall_visuals import paint_isometric_wall
            paint_isometric_wall(p,record,scene,width,height)
        elif kind=='slab':
            layers=cfg.get('layers') if isinstance(cfg.get('layers'),list) else []
            _pen(p);p.setBrush(QColor('#adbdca'))
            p.drawRect(QRectF(margin,margin,width-2*margin,height-2*margin))
            if layers:
                thicknesses=[max(0,float(l.get('thickness',0))) for l in layers if isinstance(l,dict)]
                total=sum(thicknesses) or 1
                pos=margin;length=(height-2*margin if kind=='wall' else width-2*margin)
                palette=['#d0ac86','#c9d5dc','#aeada7','#ede0b7','#a5c2c6']
                for i,t in enumerate(thicknesses):
                    seg=length*t/total;p.setBrush(QColor(palette[i%len(palette)]))
                    if kind=='wall':p.drawRect(QRectF(margin,pos,width-2*margin,seg))
                    else:p.drawRect(QRectF(pos,margin,seg,height-2*margin))
                    pos+=seg
        elif kind in ('beam','column'):
            w=float(cfg.get('width',.2) or .2);h=float(cfg.get('height',cfg.get('depth',.4)) or .4)
            ratio=min((width-2*margin)/max(w,.001),(height-2*margin)/max(h,.001))
            rect=QRectF((width-w*ratio)/2,(height-h*ratio)/2,w*ratio,h*ratio)
            p.setBrush(QColor('#b1bbc3'));_pen(p);p.drawRect(rect)
            p.drawLine(QPointF(width/2,margin//2),QPointF(width/2,height-margin//2))
        elif kind in ('door','window'):
            _pen(p,'#4c686d',3);p.setBrush(QColor('#dcebf1' if kind=='window' else '#c6b39a'))
            box=QRectF(width*.24,height*.13,width*.52,height*.75)
            p.drawRect(box)
            if kind=='door':
                _pen(p,'#52697a',2);p.drawEllipse(QPointF(width*.69,height*.53),3,3)
                if cfg.get('leaf_variant')=='grid':
                    p.drawLine(QPointF(width*.5,box.top()),QPointF(width*.5,box.bottom()))
                    p.drawLine(QPointF(box.left(),height*.5),QPointF(box.right(),height*.5))
            else:
                p.drawLine(QPointF(width*.5,box.top()),QPointF(width*.5,box.bottom()))
        else:
            _pen(p);p.drawText(pix.rect(),Qt.AlignCenter,'Preview unavailable')
    except (TypeError,ValueError,OverflowError,KeyError):
        _pen(p);p.drawText(pix.rect(),Qt.AlignCenter,'Unrecognized geometry')
    finally:
        p.end()
    return pix
