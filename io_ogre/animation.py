"""Blender 5 action slots used by the blender2ogre import/export paths.

Distributed with blender2ogre under the GNU LGPL 2.1 or later.
"""
from bpy_extras import anim_utils


def action_slot(action, owner=None, slot=None, create=False):
    if slot is not None and slot in action.slots[:]:
        return slot
    anim = getattr(owner, 'animation_data', None)
    if anim and anim.action == action and anim.action_slot:
        return anim.action_slot
    compatible = [s for s in action.slots if owner is None or s.target_id_type == owner.id_type]
    if owner is not None:
        for candidate in compatible:
            if candidate.name_display == owner.name:
                return candidate
    if len(compatible) == 1 and not create:
        return compatible[0]
    if create:
        return action.slots.new(id_type=owner.id_type, name=owner.name)
    if len(compatible) > 1:
        raise ValueError('Choose an action slot for: ' + action.name)
    return compatible[0] if compatible else None


def channelbag(action, owner=None, slot=None, create=False):
    slot = action_slot(action, owner, slot, create)
    if slot is None:
        return None
    if create:
        return anim_utils.action_ensure_channelbag_for_slot(action, slot)
    return anim_utils.action_get_channelbag_for_slot(action, slot)


def fcurves(action, owner=None, slot=None):
    bag = channelbag(action, owner, slot)
    return bag.fcurves if bag else ()


def new_fcurve(action, owner, data_path, index=0, group_name=''):
    bag = channelbag(action, owner, create=True)
    existing = bag.fcurves.find(data_path, index=index)
    return existing or bag.fcurves.new(data_path, index=index, group_name=group_name)


def assign_action(owner, action, slot=None):
    anim = owner.animation_data_create()
    selected = action_slot(action, owner, slot)
    anim.action = action
    if selected:
        anim.action_slot = selected
    return selected
