import os
import shutil

import bpy


def collect_and_copy_textures(objects, destination_dir):
    """
    Collect all texture image files from materials on the given objects
    and copy them to the destination directory.

    Returns the number of textures copied.
    """
    image_paths = _gather_image_paths(objects)

    if not image_paths:
        return 0

    os.makedirs(destination_dir, exist_ok=True)

    copied = 0
    for src_path in image_paths:
        if not os.path.isfile(src_path):
            continue

        filename = os.path.basename(src_path)
        dst_path = os.path.join(destination_dir, filename)

        # Skip if source and destination are the same file
        try:
            if os.path.isfile(dst_path) and os.path.samefile(src_path, dst_path):
                copied += 1
                continue
        except (OSError, ValueError):
            pass

        shutil.copy2(src_path, dst_path)
        copied += 1

    return copied


def _gather_image_paths(objects):
    """
    Walk all materials on the given objects and collect absolute paths
    to all image textures used in shader node trees.
    """
    images = set()

    for obj in objects:
        if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
            continue

        for mat in obj.data.materials:
            if mat is None:
                continue
            _collect_images_from_material(mat, images)

    # Resolve to absolute paths, skip packed/generated images
    paths = set()
    for img in images:
        if img.packed_file:
            # Save packed image to a temp location so it can be copied
            path = _save_packed_image(img)
            if path:
                paths.add(path)
        elif img.filepath:
            abs_path = bpy.path.abspath(img.filepath)
            if abs_path and os.path.isfile(abs_path):
                paths.add(abs_path)

    return paths


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
