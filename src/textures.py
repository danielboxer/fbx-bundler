import os
import shutil

import bpy

from . import texture_processing


def bundled_relative_path(img, preserve_structure, texture_root, processing_settings):
    """
    Path, relative to the texture folder, where this image is bundled. Shared by
    the FBX path remap and the copy step so the FBX references and the files on
    disk are always named the same, including any extension change from
    conversion or resize.
    """
    if img.packed_file:
        rel = bpy.path.clean_name(img.name) + _get_image_extension(img)
    else:
        abs_path = bpy.path.abspath(img.filepath)
        if preserve_structure:
            rel = _get_relative_texture_path(abs_path, texture_root)
        else:
            rel = os.path.basename(abs_path)

    ext = texture_processing.output_extension(rel, processing_settings)
    return os.path.splitext(rel)[0] + ext


def remap_image_paths(
    objects, tex_dir, preserve_structure=False, texture_root="", processing_settings=None
):
    """
    Temporarily remap image filepaths so the FBX exporter writes paths
    pointing to the texture folder. Returns a dict of {image: original_filepath}
    for restoration after export.

    processing_settings must match what collect_and_copy_textures receives so the
    FBX references land on the same filenames the bundled files get.
    """
    images = set()
    for obj in objects:
        if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
            continue
        for mat in obj.data.materials:
            if mat is None:
                continue
            _collect_images_from_material(mat, images)

    original_paths = {}
    for img in images:
        if not img.packed_file and not img.filepath:
            continue
        original_paths[img] = img.filepath_raw
        rel = bundled_relative_path(
            img, preserve_structure, texture_root, processing_settings
        )
        img.filepath_raw = os.path.join(tex_dir, rel)

    return original_paths


def restore_image_paths(original_paths):
    """Restore image filepaths after export."""
    for img, path in original_paths.items():
        img.filepath_raw = path


def generate_unity_mask_maps(objects, destination_dir, report_fn=None):
    """
    For each unique material on the given objects, generate a Unity mask map
    (R=Metallic, G=AO, B=0, A=Smoothness) from its Principled BSDF inputs
    and save it to a 'unity_packed' subfolder inside destination_dir.

    Only materials with at least a metallic or roughness texture produce a
    mask map. Returns (count, consumed_images) where count is the number of
    mask maps written and consumed_images is the set of bpy.types.Image objects
    that were packed (useful for excluding them from the normal texture copy).
    """
    import os

    packed_dir = os.path.join(destination_dir, "unity_packed")
    seen = set()
    count = 0
    all_consumed = set()

    for obj in objects:
        if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
            continue
        for mat in obj.data.materials:
            if mat is None or mat.name in seen:
                continue
            seen.add(mat.name)
            consumed, out_path = texture_processing.pack_unity_mask_map(mat, packed_dir)
            if out_path:
                count += 1
                all_consumed.update(consumed)

    return count, all_consumed


def collect_and_copy_textures(
    objects,
    destination_dir,
    preserve_structure=False,
    processing_settings=None,
    report_fn=None,
    texture_root="",
    exclude_images=None,
):
    """
    Collect all texture image files from materials on the given objects
    and copy them to the destination directory.

    Args:
        objects: Blender objects to collect textures from
        destination_dir: Root texture output directory
        preserve_structure: If True, maintain relative folder hierarchy
        processing_settings: Dict with texture processing options (convert_format,
                           max_resolution, jpeg_quality). None for straight copy.
        report_fn: Optional callable matching bpy.types.Operator.report signature,
                   used to emit warnings (e.g. duplicate texture name conflicts).
        texture_root: Root directory to compute relative paths from when
                      preserve_structure is True. Falls back to blend file directory.
        exclude_images: Optional set of bpy.types.Image objects to skip (e.g.
                        images already packed into a mask map).

    Returns the number of textures copied.
    """
    image_data = _gather_image_data(objects, exclude_images=exclude_images)

    if not image_data:
        return 0

    os.makedirs(destination_dir, exist_ok=True)

    copied = 0
    # Track destination -> source to detect name collisions across different source files
    copied_destinations = {}
    for img, src_path in image_data:
        if not os.path.isfile(src_path):
            continue

        rel_path = bundled_relative_path(
            img, preserve_structure, texture_root, processing_settings
        )
        dst_path = os.path.join(destination_dir, rel_path)

        # Create subdirectories if preserving structure
        dst_dir = os.path.dirname(dst_path)
        os.makedirs(dst_dir, exist_ok=True)

        # Skip if source and destination are the same file
        try:
            if os.path.isfile(dst_path) and os.path.samefile(src_path, dst_path):
                copied += 1
                continue
        except (OSError, ValueError):
            pass

        # Warn when two different source files map to the same destination filename
        if (
            dst_path in copied_destinations
            and copied_destinations[dst_path] != src_path
        ):
            if report_fn:
                existing = os.path.basename(copied_destinations[dst_path])
                incoming = os.path.basename(src_path)
                report_fn(
                    {"WARNING"},
                    f"Duplicate texture name '{os.path.basename(dst_path)}': "
                    f"'{existing}' will be overwritten by '{incoming}'",
                )
        copied_destinations[dst_path] = src_path

        # Apply texture processing or straight copy
        if processing_settings:
            texture_processing.process_textures(src_path, dst_path, processing_settings)
        else:
            shutil.copy2(src_path, dst_path)

        copied += 1

    return copied


def _get_relative_texture_path(abs_path, texture_root=""):
    """
    Get a relative path for preserving folder structure.
    Uses texture_root if provided, otherwise falls back to the blend file directory.
    Returns just the filename if the texture is outside the root.
    """
    # Prefer the user-supplied root, then the blend file directory
    root = bpy.path.abspath(texture_root) if texture_root else ""
    if not root or not os.path.isdir(root):
        blend_path = bpy.data.filepath
        root = os.path.dirname(blend_path) if blend_path else ""

    if root:
        try:
            rel = os.path.relpath(abs_path, root)
            # Only keep the relative path if the texture is inside the root
            # (i.e. the path does not escape via ..)
            if not rel.startswith(".."):
                return rel
        except ValueError:
            # Different drive on Windows
            pass

    return os.path.basename(abs_path)


def _gather_image_data(objects, exclude_images=None):
    """
    Walk all materials on the given objects and collect (image, source_path)
    tuples for all image textures used in shader node trees. source_path is the
    file to read bytes from (a temp file for packed images).

    exclude_images: optional set of bpy.types.Image objects to omit.
    """
    images = set()

    for obj in objects:
        if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
            continue

        for mat in obj.data.materials:
            if mat is None:
                continue
            _collect_images_from_material(mat, images)

    # Drop any images that were already handled separately (e.g. packed into a mask map)
    if exclude_images:
        images -= exclude_images

    results = set()
    for img in images:
        if img.packed_file:
            path = _save_packed_image(img)
            if path:
                results.add((img, path))
        elif img.filepath:
            abs_path = bpy.path.abspath(img.filepath)
            if abs_path and os.path.isfile(abs_path):
                results.add((img, abs_path))

    return results


def _collect_images_from_material(material, images):
    """Collect Image datablocks from a material's node tree."""
    if not material.use_nodes or not material.node_tree:
        return
    _collect_images_from_node_tree(material.node_tree, images)


def _collect_images_from_node_tree(node_tree, images):
    """Recursively collect images from a node tree, descending into node groups."""
    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            images.add(node.image)
        elif node.type == "GROUP" and node.node_tree:
            _collect_images_from_node_tree(node.node_tree, images)


def _save_packed_image(image):
    """
    Save a packed image to a temporary file and return the path.
    Returns None if the image cannot be saved.
    """
    import tempfile

    if not image.packed_file:
        return None

    ext = _get_image_extension(image)
    temp_dir = tempfile.gettempdir()
    # Use the image name as filename, sanitized
    safe_name = bpy.path.clean_name(image.name)
    temp_path = os.path.join(temp_dir, f"{safe_name}{ext}")

    try:
        original_path = image.filepath_raw
        image.filepath_raw = temp_path
        image.save()
        image.filepath_raw = original_path
        return temp_path
    except Exception:
        return None


def _get_image_extension(image):
    """Get the appropriate file extension for an image based on its format."""
    format_map = {
        "PNG": ".png",
        "JPEG": ".jpg",
        "JPEG2000": ".jp2",
        "TARGA": ".tga",
        "TARGA_RAW": ".tga",
        "BMP": ".bmp",
        "IRIS": ".rgb",
        "TIFF": ".tiff",
        "OPEN_EXR": ".exr",
        "OPEN_EXR_MULTILAYER": ".exr",
        "HDR": ".hdr",
        "DDS": ".dds",
        "WEBP": ".webp",
    }
    return format_map.get(image.file_format, ".png")
