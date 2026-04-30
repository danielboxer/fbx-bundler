import os
import shutil

import bpy

from . import texture_processing


def remap_image_paths(objects, tex_dir, preserve_structure=False):
    """
    Temporarily remap image filepaths so the FBX exporter writes paths
    pointing to the texture folder. Returns a dict of {image: original_filepath}
    for restoration after export.
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
        original_paths[img] = img.filepath_raw

        if img.packed_file:
            ext = _get_image_extension(img)
            safe_name = bpy.path.clean_name(img.name)
            img.filepath_raw = os.path.join(tex_dir, f"{safe_name}{ext}")
        elif img.filepath:
            abs_path = bpy.path.abspath(img.filepath)
            if preserve_structure:
                rel = _get_relative_texture_path(abs_path)
                img.filepath_raw = os.path.join(tex_dir, rel)
            else:
                filename = os.path.basename(abs_path)
                img.filepath_raw = os.path.join(tex_dir, filename)

    return original_paths


def restore_image_paths(original_paths):
    """Restore image filepaths after export."""
    for img, path in original_paths.items():
        img.filepath_raw = path


def collect_and_copy_textures(
    objects, destination_dir, preserve_structure=False, processing_settings=None
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

    Returns the number of textures copied.
    """
    image_data = _gather_image_data(objects)

    if not image_data:
        return 0

    os.makedirs(destination_dir, exist_ok=True)

    copied = 0
    for src_path, is_packed in image_data:
        if not os.path.isfile(src_path):
            continue

        # Determine destination path
        if preserve_structure and not is_packed:
            rel_path = _get_relative_texture_path(src_path)
            dst_path = os.path.join(destination_dir, rel_path)
        else:
            dst_path = os.path.join(destination_dir, os.path.basename(src_path))

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

        # Apply texture processing or straight copy
        if processing_settings:
            texture_processing.process_textures(src_path, dst_path, processing_settings)
        else:
            shutil.copy2(src_path, dst_path)

        copied += 1

    return copied


def _get_relative_texture_path(abs_path):
    """
    Get a relative path for preserving folder structure.
    Uses the blend file location as the base, or falls back to filename only.
    """
    blend_path = bpy.data.filepath
    if blend_path:
        blend_dir = os.path.dirname(blend_path)
        try:
            rel = os.path.relpath(abs_path, blend_dir)
            # Only use relative path if it doesn't go too far up
            if not rel.startswith("..\\..\\..") and not rel.startswith("../../../"):
                return rel
        except ValueError:
            pass

    return os.path.basename(abs_path)


def _gather_image_data(objects):
    """
    Walk all materials on the given objects and collect (absolute_path, is_packed)
    tuples for all image textures used in shader node trees.
    """
    images = set()

    for obj in objects:
        if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
            continue

        for mat in obj.data.materials:
            if mat is None:
                continue
            _collect_images_from_material(mat, images)

    results = set()
    for img in images:
        if img.packed_file:
            path = _save_packed_image(img)
            if path:
                results.add((path, True))
        elif img.filepath:
            abs_path = bpy.path.abspath(img.filepath)
            if abs_path and os.path.isfile(abs_path):
                results.add((abs_path, False))

    return results


def _collect_images_from_material(material, images):
    """Collect Image datablocks from a material's node tree."""
    if not material.use_nodes or not material.node_tree:
        return

    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image:
            images.add(node.image)
        # Handle node groups recursively
        elif node.type == "GROUP" and node.node_tree:
            _collect_images_from_node_tree(node.node_tree, images)


def _collect_images_from_node_tree(node_tree, images):
    """Recursively collect images from a node tree (for node groups)."""
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
