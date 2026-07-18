import bpy
from bpy.types import Menu

# Operator property values applied by every preset. Per-preset overrides in
# PRESETS are merged on top of these.
_COMMON = {
    "global_scale": 1.0,
    "apply_unit_scale": True,
    "use_space_transform": True,
    "use_subsurf": False,
    "use_mesh_modifiers": True,
    "primary_bone_axis": "Y",
    "secondary_bone_axis": "X",
    "use_armature_deform_only": False,
    "add_leaf_bones": False,
    "bake_anim": True,
    "bake_anim_use_all_bones": True,
    "bake_anim_use_nla_strips": True,
    "bake_anim_use_all_actions": True,
    "bake_anim_force_startend_keying": True,
    "bake_anim_step": 1.0,
    "path_mode": "AUTO",
    "embed_textures": False,
}

# Per-preset overrides for exporting to a target application.
PRESETS = {
    "UNITY": {
        "apply_scale_options": "FBX_SCALE_ALL",
        "axis_forward": "-Z",
        "axis_up": "Y",
        "mesh_smooth_type": "FACE",
        "use_triangles": True,
        "use_tspace": True,
        "bake_anim_simplify_factor": 1.0,
        "pack_unity_mask_map": True,
        "exclude_packed_pbr_sources": True,
    },
    "UNREAL": {
        "apply_scale_options": "FBX_SCALE_UNITS",
        "axis_forward": "X",
        "axis_up": "Z",
        "mesh_smooth_type": "FACE",
        "use_triangles": True,
        "use_tspace": True,
        "bake_anim_simplify_factor": 1.0,
    },
    "GODOT": {
        "apply_scale_options": "FBX_SCALE_UNITS",
        "axis_forward": "-Z",
        "axis_up": "Y",
        "mesh_smooth_type": "FACE",
        "use_triangles": True,
        "use_tspace": False,
        "bake_anim_simplify_factor": 1.0,
    },
    "BLENDER": {
        "apply_scale_options": "FBX_SCALE_NONE",
        "axis_forward": "-Z",
        "axis_up": "Y",
        "mesh_smooth_type": "OFF",
        "use_triangles": False,
        "use_tspace": False,
        "bake_anim_simplify_factor": 0.0,
    },
}


def apply_preset(op, name):
    """Apply a named preset's settings to the operator. Unknown names are ignored."""
    overrides = PRESETS.get(name)
    if overrides is None:
        return
    for field, value in {**_COMMON, **overrides}.items():
        setattr(op, field, value)


# Blender preset menu (allows saving/loading custom presets via the preset system)
class EXPORT_MT_fbx_bundle_presets(Menu):
    bl_label = "FBX Bundle Export Presets"
    preset_subdir = "operator/fbx_bundle_export"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


def register():
    bpy.utils.register_class(EXPORT_MT_fbx_bundle_presets)


def unregister():
    bpy.utils.unregister_class(EXPORT_MT_fbx_bundle_presets)
