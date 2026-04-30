import os

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper

from . import presets, textures


class EXPORT_SCENE_OT_fbx_bundle_batch(bpy.types.Operator, ExportHelper):
    """Export each selected object or collection as a separate FBX with textures"""

    bl_idname = "export_scene.fbx_bundle_batch"
    bl_label = "FBX Bundle Batch Export"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ""

    filter_glob: StringProperty(
        default="*",
        options={"HIDDEN"},
    )

    # Override filepath to act as directory picker
    directory: StringProperty(
        name="Output Directory",
        description="Directory to export all FBX files into",
        subtype="DIR_PATH",
    )

    batch_by: EnumProperty(
        name="Batch By",
        description="How to split objects into separate FBX files",
        items=[
            ("OBJECT", "Each Object", "Export each selected object as its own FBX"),
            ("COLLECTION", "Each Collection", "Export each collection as its own FBX"),
            (
                "TOP_PARENT",
                "Each Top-Level Parent",
                "Export each root parent hierarchy as its own FBX",
            ),
        ],
        default="OBJECT",
    )

    # --- Texture Options ---

    export_textures: BoolProperty(
        name="Export Textures",
        description="Copy textures for each exported FBX",
        default=True,
    )

    texture_folder_name: StringProperty(
        name="Texture Folder",
        description="Name of the texture subfolder for each export",
        default="textures",
    )

    preserve_texture_structure: BoolProperty(
        name="Preserve Folder Structure",
        description="Keep relative folder hierarchy for textures instead of flattening",
        default=False,
    )

    # --- Naming ---

    naming_convention: EnumProperty(
        name="Naming",
        description="How to name the exported FBX files",
        items=[
            ("ORIGINAL", "Original Name", "Use the object/collection name as-is"),
            ("PASCAL", "PascalCase", "Convert to PascalCase"),
            ("SNAKE", "snake_case", "Convert to snake_case"),
            ("KEBAB", "kebab-case", "Convert to kebab-case"),
        ],
        default="ORIGINAL",
    )

    # --- Preset ---

    preset_enum: EnumProperty(
        name="Preset",
        description="Export preset for target application",
        items=[
            ("CUSTOM", "Custom", "Use current settings"),
            ("UNITY", "Unity", "Unity-optimized settings"),
            ("UNREAL", "Unreal Engine", "Unreal-optimized settings"),
            ("GODOT", "Godot", "Godot-optimized settings"),
        ],
        default="CUSTOM",
    )

    # --- Common FBX Settings ---

    global_scale: bpy.props.FloatProperty(
        name="Scale",
        default=1.0,
        min=0.001,
        max=1000.0,
    )

    apply_scale_options: EnumProperty(
        name="Apply Scalings",
        items=[
            ("FBX_SCALE_NONE", "All Local", ""),
            ("FBX_SCALE_UNITS", "FBX Units Scale", ""),
            ("FBX_SCALE_CUSTOM", "FBX Custom Scale", ""),
            ("FBX_SCALE_ALL", "FBX All", ""),
        ],
        default="FBX_SCALE_NONE",
    )

    axis_forward: EnumProperty(
        name="Forward",
        items=[
            ("X", "X", ""),
            ("Y", "Y", ""),
            ("Z", "Z", ""),
            ("-X", "-X", ""),
            ("-Y", "-Y", ""),
            ("-Z", "-Z", ""),
        ],
        default="-Z",
    )

    axis_up: EnumProperty(
        name="Up",
        items=[
            ("X", "X", ""),
            ("Y", "Y", ""),
            ("Z", "Z", ""),
            ("-X", "-X", ""),
            ("-Y", "-Y", ""),
            ("-Z", "-Z", ""),
        ],
        default="Y",
    )

    use_mesh_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    use_triangles: BoolProperty(name="Triangulate", default=False)
    add_leaf_bones: BoolProperty(name="Add Leaf Bones", default=False)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "preset_enum")
        layout.separator()

        box = layout.box()
        box.label(text="Batch Settings", icon="FILE_REFRESH")
        box.prop(self, "batch_by")
        box.prop(self, "naming_convention")

        box = layout.box()
        box.label(text="Textures", icon="TEXTURE")
        box.prop(self, "export_textures")
        if self.export_textures:
            box.prop(self, "texture_folder_name")
            box.prop(self, "preserve_texture_structure")

        box = layout.box()
        box.label(text="Transform", icon="ORIENTATION_GLOBAL")
        box.prop(self, "global_scale")
        box.prop(self, "apply_scale_options")
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")

        box = layout.box()
        box.label(text="Geometry", icon="MESH_DATA")
        box.prop(self, "use_mesh_modifiers")
        box.prop(self, "use_triangles")
        box.prop(self, "add_leaf_bones")

    def execute(self, context):
        from . import naming

        output_dir = (
            self.directory if self.directory else os.path.dirname(self.filepath)
        )

        if not output_dir or not os.path.isdir(output_dir):
            self.report({"ERROR"}, "Invalid output directory")
            return {"CANCELLED"}

        # Get export groups based on batch mode
        groups = self._get_batch_groups(context)

        if not groups:
            self.report({"ERROR"}, "Nothing to export")
            return {"CANCELLED"}

        # Apply preset if selected
        if self.preset_enum != "CUSTOM":
            preset_func = presets.PRESETS.get(self.preset_enum)
            if preset_func:
                preset_func(self)

        exported = 0
        for group_name, objects in groups.items():
            # Apply naming convention
            file_name = naming.apply_convention(group_name, self.naming_convention)
            filepath = os.path.join(output_dir, f"{file_name}.fbx")
            tex_dir = os.path.join(output_dir, self.texture_folder_name)

            # Select only this group's objects
            bpy.ops.object.select_all(action="DESELECT")
            for obj in objects:
                obj.select_set(True)

            # Remap textures if bundling
            original_paths = {}
            if self.export_textures:
                original_paths = textures.remap_image_paths(
                    objects, tex_dir, self.preserve_texture_structure
                )

            # Export FBX
            kwargs = {
                "filepath": filepath,
                "use_selection": True,
                "global_scale": self.global_scale,
                "apply_scale_options": self.apply_scale_options,
                "axis_forward": self.axis_forward,
                "axis_up": self.axis_up,
                "apply_unit_scale": True,
                "use_space_transform": True,
                "use_mesh_modifiers": self.use_mesh_modifiers,
                "use_triangles": self.use_triangles,
                "add_leaf_bones": self.add_leaf_bones,
                "path_mode": "RELATIVE" if self.export_textures else "AUTO",
                "embed_textures": False,
                "batch_mode": "OFF",
            }

            result = bpy.ops.export_scene.fbx(**kwargs)

            # Restore paths
            if original_paths:
                textures.restore_image_paths(original_paths)

            if "FINISHED" in result:
                exported += 1

                # Copy textures
                if self.export_textures:
                    textures.collect_and_copy_textures(
                        objects, tex_dir, self.preserve_texture_structure
                    )

        self.report({"INFO"}, f"Batch exported {exported} FBX file(s) to: {output_dir}")
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def _get_batch_groups(self, context):
        """Split selected objects into named groups for batch export."""
        selected = context.selected_objects
        if not selected:
            return {}

        groups = {}

        if self.batch_by == "OBJECT":
            for obj in selected:
                if obj.type == "MESH" or obj.type == "ARMATURE":
                    groups[obj.name] = [obj]
                    # Include armature's children
                    if obj.type == "ARMATURE":
                        groups[obj.name].extend(
                            [
                                c
                                for c in obj.children
                                if c in selected or not self.use_selection_only
                            ]
                        )

        elif self.batch_by == "COLLECTION":
            for col in bpy.data.collections:
                col_objects = [o for o in selected if o.name in col.objects]
                if col_objects:
                    groups[col.name] = col_objects

        elif self.batch_by == "TOP_PARENT":
            for obj in selected:
                root = obj
                while root.parent and root.parent in selected:
                    root = root.parent
                if root.name not in groups:
                    groups[root.name] = []
                if obj not in groups[root.name]:
                    groups[root.name].append(obj)

        return groups


def register():
    bpy.utils.register_class(EXPORT_SCENE_OT_fbx_bundle_batch)


def unregister():
    bpy.utils.unregister_class(EXPORT_SCENE_OT_fbx_bundle_batch)
