# SPDX-License-Identifier: GPL-3.0-or-later
"""Session creation defaults applied inside native creation commands."""
import copy
from core.layers import DEFAULT_LAYER, assign_layer
from .bim import ifc_identity_data

def creation_defaults(scene):
    """Session-only defaults per modelling tool; never a second layer registry."""
    if not hasattr(scene, "_opentrace_creation_properties"):
        scene._opentrace_creation_properties = {}
    return scene._opentrace_creation_properties


def apply_creation_properties(command, scene, groups, kind):
    """Called inside creation commands, once: redo retains original values."""
    if getattr(command, "_properties_initialized", False):
        return
    defaults = creation_defaults(scene).get(kind, {})
    name = defaults.get('layer', getattr(scene, '_opentrace_active_layer', DEFAULT_LAYER))
    if scene.layer(name) is None:
        name = DEFAULT_LAYER
    for group in groups:
        # An explicit template layer wins unless a user selected a destination.
        if "layer" in defaults or not getattr(group, "layer", None):
            assign_layer(group, name)
        meta = ifc_identity_data(group)
        # The selected project classification is independent from the IFC4
        # entity. Use a normative code automatically only when the uploaded
        # catalogue explicitly maps exactly ONE code to the element's IFC class.
        from .catalogue_migration import automatic_for_class_multi
        catalogue = getattr(scene, '_opentrace_catalogue_for_creation', None) or {}
        if not defaults.get('ifc'):
            assigned = automatic_for_class_multi(catalogue, meta.get('class'))
            if assigned:
                preferred = str(catalogue.get('primary_system') or '')
                primary = next((item for item in assigned if item['system'] == preferred), assigned[0])
                meta['classification_system'] = primary['system']
                meta['classification_code'] = primary['code']
                meta['classification_opt_out'] = False
                entries = list(meta.get('classifications') or [])
                for item in assigned:
                    if not any(isinstance(e, dict) and e.get('system') == item['system']
                               and e.get('code') == item['code'] for e in entries):
                        entries.append({'system': item['system'], 'code': item['code'],
                                        'name': item.get('name', ''),
                                        'location': item.get('location', '')})
                meta['classifications'] = entries
        if defaults.get("ifc"):
            meta.update(copy.deepcopy(defaults["ifc"]))
            if meta.get("classification_opt_out"):
                meta["classification_system"] = ""
                meta["classification_code"] = ""
                meta["classifications"] = []
        group.ifc = meta
    command._properties_initialized = True
