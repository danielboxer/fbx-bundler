import os

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Panel

from . import preferences, presets, textures


class EXPORT_SCENE_OT_fbx_unity_quick(bpy.types.Operator):
    """Quick export FBX + textures directly to your Unity project"""

    bl_idname = "export_scene.fbx_unity_quick"
    bl_label = "Quick Export to Unity"
    bl_options = {"REGISTER"}

    def execute(self, context):
        prefs = preferences.get_preferences()
        scene = context.scene

        # Validate paths
        assets_path = bpy.path.abspath(prefs.unity_assets_path)
        if not prefs.unity_assets_path or not os.path.isdir(assets_path):
            self.report(
                {"ERROR"}, "Unity Assets path not set or invalid. Set it in the panel"
            )
            return {"CANCELLED"}

        if not scene.fbx_bundle_unity_subfolder:
            self.report({"ERROR"}, "Subfolder name not set")
            return {"CANCELLED"}

        # Build export directory
        export_dir = os.path.join(assets_path, scene.fbx_bundle_unity_subfolder)
        os.makedirs(export_dir, exist_ok=True)

        # Determine FBX filename
        if scene.fbx_bundle_unity_filename:
            fbx_name = scene.fbx_bundle_unity_filename
        elif context.active_object:
            fbx_name = bpy.path.clean_name(context.active_object.name)
        else:
            fbx_name = "export"

        if not fbx_name.endswith(".fbx"):
            fbx_name += ".fbx"

        filepath = os.path.join(export_dir, fbx_name)
        tex_dir = os.path.join(export_dir, "textures")

        # Get objects to export
        use_selection = scene.fbx_bundle_unity_selection_only
        if use_selection:
            objects = context.selected_objects
        else:
            objects = list(context.scene.objects)

        if not objects:
            self.report({"ERROR"}, "No objects to export")
            return {"CANCELLED"}

        # Remap texture paths before export
        original_paths = textures.remap_image_paths(objects, tex_dir)

        # Build FBX export kwargs with Unity preset
        kwargs = {
            "filepath": filepath,
            "use_selection": use_selection,
            "use_visible": False,
            "use_active_collection": False,
            "global_scale": 1.0,
            "apply_scale_options": "FBX_SCALE_ALL",
            "axis_forward": "-Z",
            "axis_up": "Y",
            "apply_unit_scale": True,
            "use_space_transform": True,
            "mesh_smooth_type": "FACE",
            "use_subsurf": False,
            "use_mesh_modifiers": True,
            "use_mesh_edges": False,
            "use_triangles": False,
            "use_tspace": True,
            "colors_type": "SRGB",
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
            "bake_anim_simplify_factor": 1.0,
            "path_mode": "RELATIVE",
            "embed_textures": False,
            "batch_mode": "OFF",
        }

        result = bpy.ops.export_scene.fbx(**kwargs)

        # Restore image paths
        if original_paths:
            textures.restore_image_paths(original_paths)

        if "FINISHED" not in result:
            self.report({"ERROR"}, "FBX export failed")
            return {"CANCELLED"}

        # Copy textures
        copied = textures.collect_and_copy_textures(objects, tex_dir)

        self.report({"INFO"}, f"Exported to Unity: {filepath} ({copied} texture(s))")
        return {"FINISHED"}


class VIEW3D_PT_fbx_unity_export(Panel):
    """Unity Quick Export panel in the N-panel"""

    bl_label = "FBX Unity Export"
    bl_idname = "VIEW3D_PT_fbx_unity_export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FBX Bundle"

    def draw(self, context):
        layout = self.layout
        prefs = preferences.get_preferences()
        scene = context.scene

        # Unity project path (from addon prefs)
        box = layout.box()
        box.label(text="Unity Project", icon="FILE_FOLDER")
        box.prop(prefs, "unity_assets_path", text="Assets Path")

        # Per-scene export settings
        box = layout.box()
        box.label(text="Export Settings", icon="EXPORT")
        box.prop(scene, "fbx_bundle_unity_subfolder", text="Subfolder")
        box.prop(scene, "fbx_bundle_unity_filename", text="Filename")
        box.prop(scene, "fbx_bundle_unity_selection_only", text="Selected Only")

        # Scale info
        from . import scale_check

        if scene.fbx_bundle_unity_selection_only:
            objects = context.selected_objects
        else:
            objects = list(context.scene.objects)

        if objects:
            dims = scale_check.get_dimensions_string(objects)
            box = layout.box()
            box.label(text=f"Dimensions: {dims}", icon="CUBE")

        # Export button
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(
            EXPORT_SCENE_OT_fbx_unity_quick.bl_idname,
            text="Export to Unity",
            icon="EXPORT",
        )


def register():
    bpy.utils.register_class(EXPORT_SCENE_OT_fbx_unity_quick)
    bpy.utils.register_class(VIEW3D_PT_fbx_unity_export)

    # Scene properties for per-scene export config
    bpy.types.Scene.fbx_bundle_unity_subfolder = StringProperty(
        name="Unity Subfolder",
        description="Subfolder inside Unity Assets to export into",
        default="",
    )
    bpy.types.Scene.fbx_bundle_unity_filename = StringProperty(
        name="FBX Filename",
        description="Filename for the exported FBX (without extension). Blank uses active object name",
        default="",
    )
    bpy.types.Scene.fbx_bundle_unity_selection_only = BoolProperty(
        name="Selected Only",
        description="Export only selected objects",
        default=True,
    )


def unregister():
    del bpy.types.Scene.fbx_bundle_unity_selection_only
    del bpy.types.Scene.fbx_bundle_unity_filename
    del bpy.types.Scene.fbx_bundle_unity_subfolder

    bpy.utils.unregister_class(VIEW3D_PT_fbx_unity_export)
    bpy.utils.unregister_class(EXPORT_SCENE_OT_fbx_unity_quick)
