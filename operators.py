import os

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy_extras.io_utils import ExportHelper

from . import scale_check, textures


class EXPORT_SCENE_OT_fbx_bundle(bpy.types.Operator, ExportHelper):
    """Export FBX with textures bundled in a companion folder"""

    bl_idname = "export_scene.fbx_bundle"
    bl_label = "FBX Bundle Export"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".fbx"

    filter_glob: StringProperty(
        default="*.fbx",
        options={"HIDDEN"},
        maxlen=255,
    )

    # --- Texture Bundling Options ---

    export_textures: BoolProperty(
        name="Export Textures",
        description="Copy textures used by exported objects into a companion folder",
        default=True,
    )

    texture_folder_name: StringProperty(
        name="Texture Folder",
        description="Name of the folder to copy textures into (relative to FBX location)",
        default="textures",
    )

    preserve_texture_structure: BoolProperty(
        name="Preserve Folder Structure",
        description="Keep relative folder hierarchy for textures instead of flattening into one folder",
        default=False,
    )

    # --- Texture Processing ---

    convert_textures: BoolProperty(
        name="Convert Textures",
        description="Convert textures to a different format when copying",
        default=False,
    )

    convert_format: EnumProperty(
        name="Format",
        description="Target format for texture conversion",
        items=[
            ("ORIGINAL", "Keep Original", "Don't convert, keep original format"),
            ("PNG", "PNG", "Convert to PNG (lossless, supports alpha)"),
            ("JPEG", "JPEG", "Convert to JPEG (lossy, smaller, no alpha)"),
            ("TARGA", "TGA", "Convert to Targa"),
            ("WEBP", "WebP", "Convert to WebP (modern, small)"),
        ],
        default="ORIGINAL",
    )

    max_texture_resolution: IntProperty(
        name="Max Resolution",
        description="Maximum texture dimension in pixels (0 = no limit)",
        min=0,
        max=16384,
        default=0,
    )

    jpeg_quality: IntProperty(
        name="JPEG Quality",
        description="Quality for JPEG conversion (1-100)",
        min=1,
        max=100,
        default=90,
    )

    # --- Scale Check ---

    verify_scale: BoolProperty(
        name="Verify Scale",
        description="Check for common scale issues before export and show warnings",
        default=True,
    )

    # --- Preset Selection ---

    preset_enum: EnumProperty(
        name="Preset",
        description="Apply export preset for a target application",
        items=[
            ("CUSTOM", "Custom", "Use current settings"),
            ("UNITY", "Unity", "Settings optimized for Unity"),
            ("UNREAL", "Unreal Engine", "Settings optimized for Unreal Engine"),
            ("GODOT", "Godot", "Settings optimized for Godot Engine"),
            ("BLENDER", "Blender", "Settings for re-importing into Blender"),
        ],
        default="CUSTOM",
        update=lambda self, ctx: self._apply_preset(),
    )

    # --- Include ---

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected objects only",
        default=False,
    )

    use_visible: BoolProperty(
        name="Visible Objects",
        description="Export visible objects only",
        default=False,
    )

    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects in the active collection",
        default=False,
    )

    object_types: EnumProperty(
        name="Object Types",
        description="Which object types to export",
        items=[
            ("EMPTY", "Empty", ""),
            ("CAMERA", "Camera", ""),
            ("LIGHT", "Lamp", ""),
            ("ARMATURE", "Armature", ""),
            ("MESH", "Mesh", ""),
            ("OTHER", "Other", ""),
        ],
        options={"ENUM_FLAG"},
        default={"EMPTY", "CAMERA", "LIGHT", "ARMATURE", "MESH", "OTHER"},
    )

    # --- Transform ---

    global_scale: FloatProperty(
        name="Scale",
        description="Global scale factor for export",
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=1000.0,
        default=1.0,
    )

    apply_scale_options: EnumProperty(
        name="Apply Scalings",
        description="How to apply custom and unit scalings in generated FBX file",
        items=[
            (
                "FBX_SCALE_NONE",
                "All Local",
                "Apply custom scaling and target unit scaling to each object transformation",
            ),
            (
                "FBX_SCALE_UNITS",
                "FBX Units Scale",
                "Apply custom scaling to FBX scale, and target unit scaling to each object",
            ),
            (
                "FBX_SCALE_CUSTOM",
                "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and unit scaling to each object",
            ),
            (
                "FBX_SCALE_ALL",
                "FBX All",
                "Apply custom scaling and unit scaling to FBX scale",
            ),
        ],
        default="FBX_SCALE_NONE",
    )

    axis_forward: EnumProperty(
        name="Forward Axis",
        description="Forward axis for export",
        items=[
            ("X", "X Forward", ""),
            ("Y", "Y Forward", ""),
            ("Z", "Z Forward", ""),
            ("-X", "-X Forward", ""),
            ("-Y", "-Y Forward", ""),
            ("-Z", "-Z Forward", ""),
        ],
        default="-Z",
    )

    axis_up: EnumProperty(
        name="Up Axis",
        description="Up axis for export",
        items=[
            ("X", "X Up", ""),
            ("Y", "Y Up", ""),
            ("Z", "Z Up", ""),
            ("-X", "-X Up", ""),
            ("-Y", "-Y Up", ""),
            ("-Z", "-Z Up", ""),
        ],
        default="Y",
    )

    apply_unit_scale: BoolProperty(
        name="Apply Unit",
        description="Apply unit scale to exported data",
        default=True,
    )

    use_space_transform: BoolProperty(
        name="Use Space Transform",
        description="Apply global space transform to the exported data",
        default=True,
    )

    # --- Geometry ---

    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        description="Export smoothing information",
        items=[
            ("OFF", "Normals Only", "Export normals without smoothing groups"),
            ("FACE", "Face", "Write face smoothing"),
            ("EDGE", "Edge", "Write edge smoothing"),
        ],
        default="OFF",
    )

    use_subsurf: BoolProperty(
        name="Export Subdivision Surface",
        description="Export the last subdivision modifier as FBX subdivision",
        default=False,
    )

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects (except armature ones)",
        default=True,
    )

    use_mesh_edges: BoolProperty(
        name="Loose Edges",
        description="Export loose edges (as two-vertices polygons)",
        default=False,
    )

    use_triangles: BoolProperty(
        name="Triangulate Faces",
        description="Convert all faces to triangles",
        default=False,
    )

    use_tspace: BoolProperty(
        name="Tangent Space",
        description="Add binormal and tangent vectors (needed for normal mapping)",
        default=False,
    )

    colors_type: EnumProperty(
        name="Vertex Colors",
        description="Export vertex color attributes",
        items=[
            ("NONE", "None", "Do not export color attributes"),
            ("SRGB", "sRGB", "Export colors in sRGB color space"),
            ("LINEAR", "Linear", "Export colors in linear color space"),
        ],
        default="SRGB",
    )

    # --- Armature ---

    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=[
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ],
        default="Y",
    )

    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=[
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ],
        default="X",
    )

    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only export deforming bones (and non-deforming ones connected to them)",
        default=False,
    )

    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain to define last bone length",
        default=True,
    )

    # --- Animation ---

    bake_anim: BoolProperty(
        name="Baked Animation",
        description="Export baked keyframe animation",
        default=True,
    )

    bake_anim_use_all_bones: BoolProperty(
        name="Key All Bones",
        description="Force exporting at least one key of animation for all bones",
        default=True,
    )

    bake_anim_use_nla_strips: BoolProperty(
        name="NLA Strips",
        description="Export each NLA strip as a separate FBX AnimStack",
        default=True,
    )

    bake_anim_use_all_actions: BoolProperty(
        name="All Actions",
        description="Export each action as a separate FBX AnimStack",
        default=True,
    )

    bake_anim_force_startend_keying: BoolProperty(
        name="Force Start/End Keying",
        description="Always add a keyframe at start and end of actions",
        default=True,
    )

    bake_anim_step: FloatProperty(
        name="Sampling Rate",
        description="How often to evaluate animated values (in frames)",
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
        default=1.0,
    )

    bake_anim_simplify_factor: FloatProperty(
        name="Simplify",
        description="How much to simplify baked values (0 = disabled)",
        min=0.0,
        max=100.0,
        soft_min=0.0,
        soft_max=10.0,
        default=1.0,
    )

    # --- Path Mode ---

    path_mode: EnumProperty(
        name="Path Mode",
        description="Method for referencing paths",
        items=[
            ("AUTO", "Auto", "Use relative paths with subdirectories only"),
            ("ABSOLUTE", "Absolute", "Always write absolute paths"),
            ("RELATIVE", "Relative", "Always write relative paths"),
            ("MATCH", "Match", "Match absolute/relative setting with input path"),
            ("STRIP", "Strip Path", "Filename only"),
            (
                "COPY",
                "Copy",
                "Copy textures to same directory (not needed with Bundle Export)",
            ),
        ],
        default="AUTO",
    )

    embed_textures: BoolProperty(
        name="Embed Textures",
        description="Embed textures inside the FBX file (not recommended when bundling)",
        default=False,
    )

    batch_mode: EnumProperty(
        name="Batch Mode",
        description="Export in batch mode",
        items=[
            ("OFF", "Off", "Active scene to file"),
            ("SCENE", "Scene", "Each scene as a file"),
            ("COLLECTION", "Collection", "Each scene collection as a file"),
            (
                "SCENE_COLLECTION",
                "Scene Collections",
                "Each collection of each scene as a file",
            ),
            (
                "ACTIVE_SCENE_COLLECTION",
                "Active Scene Collections",
                "Each collection of the active scene as a file",
            ),
        ],
        default="OFF",
    )

    use_batch_own_dir: BoolProperty(
        name="Batch Own Dir",
        description="Create a directory for each exported file in batch mode",
        default=True,
    )

    def _apply_preset(self):
        """Apply settings from the selected preset."""
        from . import presets

        preset_func = presets.PRESETS.get(self.preset_enum)
        if preset_func:
            preset_func(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # Preset selector at top
        layout.prop(self, "preset_enum")
        layout.separator()

        # Texture bundling
        box = layout.box()
        box.label(text="Texture Bundling", icon="TEXTURE")
        box.prop(self, "export_textures")
        if self.export_textures:
            box.prop(self, "texture_folder_name")
            box.prop(self, "preserve_texture_structure")
            box.separator()
            box.prop(self, "convert_textures")
            if self.convert_textures:
                box.prop(self, "convert_format")
                box.prop(self, "max_texture_resolution")
                if self.convert_format == "JPEG":
                    box.prop(self, "jpeg_quality")

        # Scale verification
        box = layout.box()
        box.label(text="Validation", icon="CHECKMARK")
        box.prop(self, "verify_scale")

        layout.separator()

        # Include
        box = layout.box()
        box.label(text="Include", icon="OUTLINER")
        box.prop(self, "use_selection")
        box.prop(self, "use_visible")
        box.prop(self, "use_active_collection")
        col = box.column()
        col.prop(self, "object_types")

        # Transform
        box = layout.box()
        box.label(text="Transform", icon="ORIENTATION_GLOBAL")
        box.prop(self, "global_scale")
        box.prop(self, "apply_scale_options")
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")
        box.prop(self, "apply_unit_scale")
        box.prop(self, "use_space_transform")

        # Geometry
        box = layout.box()
        box.label(text="Geometry", icon="MESH_DATA")
        box.prop(self, "mesh_smooth_type")
        box.prop(self, "use_subsurf")
        box.prop(self, "use_mesh_modifiers")
        box.prop(self, "use_mesh_edges")
        box.prop(self, "use_triangles")
        box.prop(self, "use_tspace")
        box.prop(self, "colors_type")

        # Armature
        box = layout.box()
        box.label(text="Armature", icon="ARMATURE_DATA")
        box.prop(self, "primary_bone_axis")
        box.prop(self, "secondary_bone_axis")
        box.prop(self, "use_armature_deform_only")
        box.prop(self, "add_leaf_bones")

        # Animation
        box = layout.box()
        box.label(text="Animation", icon="ACTION")
        box.prop(self, "bake_anim")
        if self.bake_anim:
            box.prop(self, "bake_anim_use_all_bones")
            box.prop(self, "bake_anim_use_nla_strips")
            box.prop(self, "bake_anim_use_all_actions")
            box.prop(self, "bake_anim_force_startend_keying")
            box.prop(self, "bake_anim_step")
            box.prop(self, "bake_anim_simplify_factor")

        # Path
        box = layout.box()
        box.label(text="Path", icon="FILE_FOLDER")
        box.prop(self, "path_mode")
        box.prop(self, "embed_textures")
        box.prop(self, "batch_mode")
        if self.batch_mode != "OFF":
            box.prop(self, "use_batch_own_dir")

    def execute(self, context):
        filepath = self.filepath
        export_dir = os.path.dirname(filepath)

        objects = self._get_export_objects(context)

        # Scale verification
        if self.verify_scale:
            scale_check.check_scale(objects, self.global_scale, self.report)

        # When bundling textures, remap image paths to the texture folder
        # before export so the FBX contains correct relative references
        original_paths = {}
        if self.export_textures:
            tex_dir = os.path.join(export_dir, self.texture_folder_name)
            original_paths = textures.remap_image_paths(
                objects, tex_dir, self.preserve_texture_structure
            )

        # Use relative path mode when bundling so the FBX stores
        # paths like "textures/albedo.png"
        path_mode = "RELATIVE" if self.export_textures else self.path_mode

        # Build kwargs for the built-in FBX exporter
        kwargs = {
            "filepath": filepath,
            "use_selection": self.use_selection,
            "use_visible": self.use_visible,
            "use_active_collection": self.use_active_collection,
            "object_types": self.object_types,
            "global_scale": self.global_scale,
            "apply_scale_options": self.apply_scale_options,
            "axis_forward": self.axis_forward,
            "axis_up": self.axis_up,
            "apply_unit_scale": self.apply_unit_scale,
            "use_space_transform": self.use_space_transform,
            "mesh_smooth_type": self.mesh_smooth_type,
            "use_subsurf": self.use_subsurf,
            "use_mesh_modifiers": self.use_mesh_modifiers,
            "use_mesh_edges": self.use_mesh_edges,
            "use_triangles": self.use_triangles,
            "use_tspace": self.use_tspace,
            "colors_type": self.colors_type,
            "primary_bone_axis": self.primary_bone_axis,
            "secondary_bone_axis": self.secondary_bone_axis,
            "use_armature_deform_only": self.use_armature_deform_only,
            "add_leaf_bones": self.add_leaf_bones,
            "bake_anim": self.bake_anim,
            "bake_anim_use_all_bones": self.bake_anim_use_all_bones,
            "bake_anim_use_nla_strips": self.bake_anim_use_nla_strips,
            "bake_anim_use_all_actions": self.bake_anim_use_all_actions,
            "bake_anim_force_startend_keying": self.bake_anim_force_startend_keying,
            "bake_anim_step": self.bake_anim_step,
            "bake_anim_simplify_factor": self.bake_anim_simplify_factor,
            "path_mode": path_mode,
            "embed_textures": self.embed_textures,
            "batch_mode": self.batch_mode,
            "use_batch_own_dir": self.use_batch_own_dir,
        }

        # Run the built-in FBX export
        result = bpy.ops.export_scene.fbx(**kwargs)

        # Restore original image paths regardless of export result
        if original_paths:
            textures.restore_image_paths(original_paths)

        if "FINISHED" not in result:
            self.report({"ERROR"}, "FBX export failed")
            return {"CANCELLED"}

        self.report({"INFO"}, f"FBX exported: {filepath}")

        # Copy textures to the companion folder
        if self.export_textures:
            tex_dir = os.path.join(export_dir, self.texture_folder_name)

            # Build processing settings
            processing = None
            if self.convert_textures:
                processing = {
                    "convert_format": self.convert_format,
                    "max_resolution": self.max_texture_resolution,
                    "jpeg_quality": self.jpeg_quality,
                }

            copied = textures.collect_and_copy_textures(
                objects, tex_dir, self.preserve_texture_structure, processing
            )
            if copied > 0:
                self.report({"INFO"}, f"Copied {copied} texture(s) to: {tex_dir}")
            else:
                self.report({"WARNING"}, "No textures found to copy")

        return {"FINISHED"}

    def _get_export_objects(self, context):
        """Determine which objects were exported based on current filter settings."""
        if self.use_selection:
            objects = context.selected_objects
        elif self.use_active_collection:
            objects = context.collection.all_objects
        elif self.use_visible:
            objects = [o for o in context.scene.objects if o.visible_get()]
        else:
            objects = context.scene.objects

        # Filter by object type
        type_map = {
            "EMPTY": {"EMPTY"},
            "CAMERA": {"CAMERA"},
            "LIGHT": {"LIGHT"},
            "ARMATURE": {"ARMATURE"},
            "MESH": {"MESH"},
            "OTHER": {"CURVE", "SURFACE", "FONT", "META", "GPENCIL", "LATTICE"},
        }
        allowed_types = set()
        for key in self.object_types:
            allowed_types.update(type_map.get(key, set()))

        return [o for o in objects if o.type in allowed_types]

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
