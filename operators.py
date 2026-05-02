import os

import bpy
from bpy.props import (
    BoolProperty,
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

    # --- Bundle Batch Export ---

    batch_by: EnumProperty(
        name="Batch By",
        description="Split export into separate FBX files, one per object or collection (OFF exports everything to one file)",
        items=[
            ("OFF", "Off", "Export everything to a single FBX file"),
            (
                "OBJECT",
                "Each Object",
                "Export each selected mesh/armature as its own FBX",
            ),
            ("COLLECTION", "Each Collection", "Export each collection as its own FBX"),
            (
                "TOP_PARENT",
                "Each Top-Level Parent",
                "Export each root parent hierarchy as its own FBX",
            ),
        ],
        default="OFF",
    )

    naming_convention: EnumProperty(
        name="Naming",
        description="How to name exported FBX files in batch mode",
        items=[
            ("ORIGINAL", "Original Name", "Use the object/collection name as-is"),
            ("PASCAL", "PascalCase", "Convert to PascalCase"),
            ("SNAKE", "snake_case", "Convert to snake_case"),
            ("KEBAB", "kebab-case", "Convert to kebab-case"),
        ],
        default="ORIGINAL",
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

        # Preset selector at top (always visible)
        layout.prop(self, "preset_enum")

        # Always-visible selection shortcut (used frequently)
        if self.batch_by == "OFF":
            row = layout.row(align=True)
            row.prop(self, "use_selection", toggle=True)
            row.prop(self, "use_visible", toggle=True)
            row.prop(self, "use_active_collection", toggle=True)

        # Batch export split mode
        header, body = layout.panel(
            "export_scene_fbx_bundle_batch", default_closed=False
        )
        header.label(text="Batch Export")
        if body:
            body.prop(self, "batch_by")
            if self.batch_by != "OFF":
                body.prop(self, "naming_convention")

        # Texture bundling
        header, body = layout.panel(
            "export_scene_fbx_bundle_textures", default_closed=False
        )
        header.label(text="Texture Bundling")
        if body:
            body.prop(self, "export_textures")
            if self.export_textures:
                body.prop(self, "texture_folder_name")
                body.prop(self, "preserve_texture_structure")
                body.separator()
                body.prop(self, "convert_textures")
                if self.convert_textures:
                    body.prop(self, "convert_format")
                    body.prop(self, "max_texture_resolution")
                    if self.convert_format == "JPEG":
                        body.prop(self, "jpeg_quality")

        # Scale verification
        header, body = layout.panel(
            "export_scene_fbx_bundle_validation", default_closed=False
        )
        header.label(text="Validation")
        if body:
            body.prop(self, "verify_scale")

        layout.separator()
        layout.label(text="FBX Settings", icon="FILE")

        # Include: only object_types remains here (selection moved to always-visible row above)
        if self.batch_by == "OFF":
            header, body = layout.panel(
                "export_scene_fbx_bundle_include", default_closed=True
            )
            header.label(text="Include")
            if body:
                col = body.column()
                col.prop(self, "object_types")

        # Transform
        header, body = layout.panel(
            "export_scene_fbx_bundle_transform", default_closed=True
        )
        header.label(text="Transform")
        if body:
            body.prop(self, "global_scale")
            body.prop(self, "apply_scale_options")
            body.prop(self, "axis_forward")
            body.prop(self, "axis_up")
            body.prop(self, "apply_unit_scale")
            body.prop(self, "use_space_transform")

        # Geometry
        header, body = layout.panel(
            "export_scene_fbx_bundle_geometry", default_closed=True
        )
        header.label(text="Geometry")
        if body:
            body.prop(self, "mesh_smooth_type")
            body.prop(self, "use_subsurf")
            body.prop(self, "use_mesh_modifiers")
            body.prop(self, "use_mesh_edges")
            body.prop(self, "use_triangles")
            body.prop(self, "use_tspace")
            body.prop(self, "colors_type")

        # Armature
        header, body = layout.panel(
            "export_scene_fbx_bundle_armature", default_closed=True
        )
        header.label(text="Armature")
        if body:
            body.prop(self, "primary_bone_axis")
            body.prop(self, "secondary_bone_axis")
            body.prop(self, "use_armature_deform_only")
            body.prop(self, "add_leaf_bones")

        # Animation
        header, body = layout.panel(
            "export_scene_fbx_bundle_animation", default_closed=True
        )
        header.label(text="Animation")
        if body:
            body.prop(self, "bake_anim")
            if self.bake_anim:
                body.prop(self, "bake_anim_use_all_bones")
                body.prop(self, "bake_anim_use_nla_strips")
                body.prop(self, "bake_anim_use_all_actions")
                body.prop(self, "bake_anim_force_startend_keying")
                body.prop(self, "bake_anim_step")
                body.prop(self, "bake_anim_simplify_factor")

        # Path (hidden in batch mode, path settings are set automatically)
        if self.batch_by == "OFF":
            header, body = layout.panel(
                "export_scene_fbx_bundle_path", default_closed=True
            )
            header.label(text="Path")
            if body:
                body.prop(self, "path_mode")
                body.prop(self, "embed_textures")

    def execute(self, context):
        if self.batch_by != "OFF":
            return self._execute_batch(context)
        return self._execute_single(context)

    def _execute_single(self, context):
        filepath = self.filepath

        # If the user clicked Export while inside a directory without typing a filename,
        # default to Untitled.fbx in that directory
        if not filepath or os.path.isdir(filepath) or not os.path.basename(filepath):
            filepath = os.path.join(filepath.rstrip("\\/"), "Untitled.fbx")

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
            "batch_mode": "OFF",
            "use_batch_own_dir": False,
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
                objects,
                tex_dir,
                self.preserve_texture_structure,
                processing,
                self.report,
            )
            if copied > 0:
                self.report({"INFO"}, f"Copied {copied} texture(s) to: {tex_dir}")
            else:
                self.report({"WARNING"}, "No textures found to copy")

        return {"FINISHED"}

    def _execute_batch(self, context):
        from . import naming

        # Use the filepath directly as the output directory in batch mode
        output_dir = self.filepath
        if not output_dir or not os.path.isdir(output_dir):
            output_dir = os.path.dirname(self.filepath)

        if not output_dir or not os.path.isdir(output_dir):
            self.report({"ERROR"}, "Invalid output directory")
            return {"CANCELLED"}

        groups = self._get_batch_groups(context)
        if not groups:
            self.report({"ERROR"}, "Nothing to export")
            return {"CANCELLED"}

        # Build processing settings for texture conversion
        processing = None
        if self.convert_textures:
            processing = {
                "convert_format": self.convert_format,
                "max_resolution": self.max_texture_resolution,
                "jpeg_quality": self.jpeg_quality,
            }

        exported = 0
        for group_name, objects in groups.items():
            file_name = naming.apply_convention(group_name, self.naming_convention)
            filepath = os.path.join(output_dir, f"{file_name}.fbx")
            tex_dir = os.path.join(output_dir, self.texture_folder_name)

            # Select only this group's objects for the export
            bpy.ops.object.select_all(action="DESELECT")
            for obj in objects:
                obj.select_set(True)

            # Scale verification per group
            if self.verify_scale:
                scale_check.check_scale(objects, self.global_scale, self.report)

            # Remap image paths to the texture folder before export so the
            # FBX contains correct relative references
            original_paths = {}
            if self.export_textures:
                original_paths = textures.remap_image_paths(
                    objects, tex_dir, self.preserve_texture_structure
                )

            kwargs = {
                "filepath": filepath,
                "use_selection": True,
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
                # Force relative paths for texture bundling, disable native batch mode
                "path_mode": "RELATIVE" if self.export_textures else "AUTO",
                "embed_textures": False,
                "batch_mode": "OFF",
            }

            result = bpy.ops.export_scene.fbx(**kwargs)

            # Always restore original image paths regardless of export result
            if original_paths:
                textures.restore_image_paths(original_paths)

            if "FINISHED" in result:
                exported += 1

                # Copy textures to the companion folder for this group
                if self.export_textures:
                    textures.collect_and_copy_textures(
                        objects,
                        tex_dir,
                        self.preserve_texture_structure,
                        processing,
                        self.report,
                    )

        self.report({"INFO"}, f"Batch exported {exported} FBX file(s) to: {output_dir}")
        return {"FINISHED"}

    def _get_batch_groups(self, context):
        """Split selected objects into named groups for batch export."""
        selected = context.selected_objects
        if not selected:
            return {}

        groups = {}

        if self.batch_by == "OBJECT":
            for obj in selected:
                if obj.type in {"MESH", "ARMATURE"}:
                    groups[obj.name] = [obj]
                    # Include armature's mesh children so the rig exports with its skin
                    if obj.type == "ARMATURE":
                        groups[obj.name].extend(
                            [c for c in obj.children if c.type == "MESH"]
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
        if self.batch_by != "OFF":
            # Switch to directory picker mode for batch export
            self.filename_ext = ""
            if self.filepath and not os.path.isdir(self.filepath):
                self.filepath = os.path.dirname(self.filepath)
        else:
            self.filename_ext = ".fbx"
            # Pre-populate with a default filename if none is set
            if not self.filepath or os.path.isdir(self.filepath):
                blend_filepath = context.blend_data.filepath
                base_dir = os.path.dirname(blend_filepath) if blend_filepath else ""
                self.filepath = os.path.join(base_dir, "Untitled.fbx")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
