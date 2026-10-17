# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable favourites for parametric door/window descriptions.

Only geometry-independent properties are kept; host and opening identity,
location and IFC GUID are never copied to a new object.
"""
from __future__ import annotations
import copy
import json
import uuid
from PySide6.QtCore import QSettings
KEY='opentrace/door_window_favourites_v1'
_EXCLUDE={'id','host_id','opening_id','ifc_guid','global_id','position',
          'source_id','wall_id','uuid','cut_id','material_id'}

def _read():
    try:
        result=json.loads(str(QSettings().value(KEY,'{}') or '{}'))
    except (ValueError,TypeError):
        result={}
    return result if isinstance(result,dict) else {}

def favourites(kind=None):
    result=_read()
    return copy.deepcopy(result.get(kind,[])) if kind else copy.deepcopy(result)

def save_favourite(kind, configuration, *, name):
    if kind not in ('door','window') or not isinstance(configuration,dict):
        raise ValueError('Invalid door/window favorite.')
    config={k:copy.deepcopy(v) for k,v in configuration.items() if k not in _EXCLUDE}
    config['kind']=kind
    if len(json.dumps(config,ensure_ascii=False))>500000:
        raise ValueError('Esquadria excede limite do favorito.')
    saved=_read();entries=saved.setdefault(kind,[])
    record={'id':uuid.uuid4().hex,'name':str(name or 'Esquadria')[:180],
            'kind':kind,'config':config,'group':'Favoritos'}
    entries.append(record)
    QSettings().setValue(KEY,json.dumps(saved,ensure_ascii=False))
    return copy.deepcopy(record)
