import bpy
from bpy.types import Menu

# Preset definitions: each function configures the operator properties
# for optimal export to the target application.


def apply_unity(op):
    """Unity preset: FBX All scaling, no leaf bones, Y-up, -Z forward."""
    op.apply_scale_options = "FBX_SCALE_ALL"
    op.global_scale = 1.0
    op.axis_forward = "-Z"
    op.axis_up = "Y"
    op.apply_unit_scale = True
    op.use_space_transform = True
    op.mesh_smooth_type = "FACE"
    op.use_subsurf = False
    op.use_mesh_modifiers = True
    op.use_tspace = True
    op.primary_bone_axis = "Y"
    op.secondary_bone_axis = "X"
    op.use_armature_deform_only = False
    op.add_leaf_bones = False
    op.bake_anim = True
    op.bake_anim_use_all_bones = True
    op.bake_anim_use_nla_strips = True
    op.bake_anim_use_all_actions = True
    op.bake_anim_force_startend_keying = True
    op.bake_anim_step = 1.0
    op.bake_anim_simplify_factor = 1.0
    op.path_mode = "AUTO"
    op.embed_textures = False
    op.batch_mode = "OFF"


def apply_unreal(op):
    """Unreal Engine preset: FBX Units scaling, no leaf bones, X forward, Z up."""
    op.apply_scale_options = "FBX_SCALE_UNITS"
    op.global_scale = 1.0
    op.axis_forward = "X"
    op.axis_up = "Z"
    op.apply_unit_scale = True
    op.use_space_transform = True
    op.mesh_smooth_type = "FACE"
    op.use_subsurf = False
    op.use_mesh_modifiers = True
    op.use_tspace = True
    op.primary_bone_axis = "Y"
    op.secondary_bone_axis = "X"
    op.use_armature_deform_only = False
    op.add_leaf_bones = False
    op.bake_anim = True
    op.bake_anim_use_all_bones = True
    op.bake_anim_use_nla_strips = True
    op.bake_anim_use_all_actions = True
    op.bake_anim_force_startend_keying = True
    op.bake_anim_step = 1.0
    op.bake_anim_simplify_factor = 1.0
    op.path_mode = "AUTO"
    op.embed_textures = False
    op.batch_mode = "OFF"


def apply_godot(op):
    """Godot preset: FBX Units scaling, Y-up, -Z forward, apply modifiers."""
    op.apply_scale_options = "FBX_SCALE_UNITS"
    op.global_scale = 1.0
    op.axis_forward = "-Z"
    op.axis_up = "Y"
    op.apply_unit_scale = True
    op.use_space_transform = True
    op.mesh_smooth_type = "FACE"
    op.use_subsurf = False
    op.use_mesh_modifiers = True
    op.use_tspace = False
    op.primary_bone_axis = "Y"
    op.secondary_bone_axis = "X"
    op.use_armature_deform_only = False
    op.add_leaf_bones = False
    op.bake_anim = True
    op.bake_anim_use_all_bones = True
    op.bake_anim_use_nla_strips = True
    op.bake_anim_use_all_actions = True
    op.bake_anim_force_startend_keying = True
    op.bake_anim_step = 1.0
    op.bake_anim_simplify_factor = 1.0
    op.path_mode = "AUTO"
    op.embed_textures = False
    op.batch_mode = "OFF"


def apply_blender(op):
    """Blender preset: settings for clean round-trip back into Blender."""
    op.apply_scale_options = "FBX_SCALE_NONE"
    op.global_scale = 1.0
    op.axis_forward = "-Z"
    op.axis_up = "Y"
    op.apply_unit_scale = True
    op.use_space_transform = True
    op.mesh_smooth_type = "OFF"
    op.use_subsurf = False
    op.use_mesh_modifiers = True
    op.use_tspace = False
    op.primary_bone_axis = "Y"
    op.secondary_bone_axis = "X"
    op.use_armature_deform_only = False
    op.add_leaf_bones = False
    op.bake_anim = True
    op.bake_anim_use_all_bones = True
    op.bake_anim_use_nla_strips = True
    op.bake_anim_use_all_actions = True
    op.bake_anim_force_startend_keying = True
    op.bake_anim_step = 1.0
    op.bake_anim_simplify_factor = 0.0
    op.path_mode = "AUTO"
    op.embed_textures = False
    op.batch_mode = "OFF"


# Map preset enum values to functions
PRESETS = {
    "UNITY": apply_unity,
    "UNREAL": apply_unreal,
    "GODOT": apply_godot,
    "BLENDER": apply_blender,
}


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
