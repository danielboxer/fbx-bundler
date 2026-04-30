import bpy

from . import operators, presets


def menu_func_export(self, context):
    self.layout.operator(
        operators.EXPORT_SCENE_OT_fbx_bundle.bl_idname, text="FBX Bundle (.fbx)"
    )


def register():
    bpy.utils.register_class(operators.EXPORT_SCENE_OT_fbx_bundle)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    presets.register()


def unregister():
    presets.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(operators.EXPORT_SCENE_OT_fbx_bundle)
