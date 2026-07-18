import os
import shutil

import bpy
import numpy as np

# Keywords used to identify ambient occlusion textures by name/filepath
_AO_NAME_KEYWORDS = frozenset({"_ao", "_ambient", "_occlusion", "_occ"})


def _get_input_image(node, socket_name):
    """Return the Image datablock directly linked to a node socket, or None."""
    if socket_name not in node.inputs:
        return None
    socket = node.inputs[socket_name]
    if not socket.is_linked:
        return None
    from_node = socket.links[0].from_node
    if from_node.type == "TEX_IMAGE":
        return from_node.image
    return None


def _find_ao_image(node_tree, exclude_images):
    """
    Search a node tree for an AO texture by name convention.
    Checks for _ao, _ambient, _occlusion, or _occ substrings in the image
    name or filepath. Images in exclude_images are skipped.
    """
    for node in node_tree.nodes:
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        if node.image in exclude_images:
            continue
        name_lower = node.image.name.lower()
        path_lower = node.image.filepath.lower()
        for kw in _AO_NAME_KEYWORDS:
            if kw in name_lower or kw in path_lower:
                return node.image
    return None


def _image_red_channel(img, width, height, default):
    """
    Extract the red channel of img as a flat float32 array of size width*height.
    Returns an array filled with default if img is None.
    Copies and scales img if its dimensions do not match width x height.
    """
    if img is None:
        return np.full(width * height, default, dtype=np.float32)
    if img.size[0] != width or img.size[1] != height:
        tmp = img.copy()
        tmp.scale(width, height)
        pixels = np.array(tmp.pixels[:], dtype=np.float32)
        bpy.data.images.remove(tmp)
    else:
        pixels = np.array(img.pixels[:], dtype=np.float32)
    # RGBA interleaved layout: red is at stride 4 starting at index 0
    return pixels[0::4]


def pack_unity_mask_map(material, output_dir):
    """
    Generate a Unity mask map PNG for a material's Principled BSDF:
      R = Metallic, G = Occlusion (AO), B = 0 (unused), A = Smoothness (1 - Roughness)

    Metallic and Roughness textures are read from the direct inputs of the
    Principled BSDF node. An AO texture is detected by name convention
    (_ao, _occ, _ambient, _occlusion).

    Returns (consumed_images, output_path) where consumed_images is the set of
    bpy.types.Image objects that contributed to the pack. Returns (set(), None)
    if no Principled BSDF or no metallic/roughness textures were found.
    """
    if not material.use_nodes or not material.node_tree:
        return set(), None

    principled = next(
        (n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
        None,
    )
    if principled is None:
        return set(), None

    metallic_img = _get_input_image(principled, "Metallic")
    roughness_img = _get_input_image(principled, "Roughness")
    if not metallic_img and not roughness_img:
        return set(), None

    # Collect the PBR source images; find AO among remaining nodes by name
    consumed = {img for img in (metallic_img, roughness_img) if img is not None}
    ao_img = _find_ao_image(material.node_tree, consumed)
    if ao_img is not None:
        consumed.add(ao_img)

    # Use the first available source image as the size reference
    ref = metallic_img or roughness_img
    w, h = ref.size

    r = _image_red_channel(metallic_img, w, h, default=0.0)
    g = _image_red_channel(ao_img, w, h, default=1.0)  # white = no occlusion
    b = np.zeros(w * h, dtype=np.float32)
    a = 1.0 - _image_red_channel(roughness_img, w, h, default=0.0)  # invert roughness

    packed = np.empty(w * h * 4, dtype=np.float32)
    packed[0::4] = r
    packed[1::4] = g
    packed[2::4] = b
    packed[3::4] = a

    os.makedirs(output_dir, exist_ok=True)
    safe_name = bpy.path.clean_name(material.name)
    out_path = os.path.join(output_dir, f"{safe_name}_MaskMap.png")

    out_img = bpy.data.images.new("__mask_map_temp__", width=w, height=h, alpha=True)
    out_img.colorspace_settings.name = "Non-Color"
    out_img.pixels.foreach_set(packed)
    out_img.filepath_raw = out_path
    out_img.file_format = "PNG"
    try:
        out_img.save()
    finally:
        bpy.data.images.remove(out_img)

    return consumed, out_path


def process_textures(src_path, dst_path, settings):
    """
    Copy a texture from src to dst, applying format conversion and resizing
    based on the provided settings dict.

    Settings keys:
        convert_format: str or None - target format ('PNG', 'JPEG', 'TARGA', 'WEBP', None for no conversion)
        max_resolution: int or 0 - max dimension in pixels (0 = no resize)
        jpeg_quality: int - quality for JPEG output (1-100)

    Returns the final destination path (extension may change if format converted).
    """
    convert_format = settings.get("convert_format", None)
    max_resolution = settings.get("max_resolution", 0)
    jpeg_quality = settings.get("jpeg_quality", 90)

    needs_processing = (
        convert_format and convert_format != "ORIGINAL"
    ) or max_resolution > 0

    if not needs_processing:
        # Straight copy, no processing needed
        shutil.copy2(src_path, dst_path)
        return dst_path

    # Load image into Blender's image system for processing
    temp_img = bpy.data.images.load(src_path, check_existing=False)

    try:
        # Resize if needed
        if max_resolution > 0:
            w, h = temp_img.size
            if w > max_resolution or h > max_resolution:
                scale = max_resolution / max(w, h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                temp_img.scale(new_w, new_h)

        # Determine output format and extension
        out_format = _output_format(src_path, settings)
        final_dst = os.path.splitext(dst_path)[0] + output_extension(src_path, settings)

        # Configure render settings for save
        scene = bpy.context.scene
        old_format = scene.render.image_settings.file_format
        old_quality = scene.render.image_settings.quality
        old_color_mode = scene.render.image_settings.color_mode

        scene.render.image_settings.file_format = out_format
        if out_format == "JPEG":
            scene.render.image_settings.quality = jpeg_quality
            scene.render.image_settings.color_mode = "RGB"
        elif out_format == "PNG":
            scene.render.image_settings.color_mode = "RGBA"
        elif out_format == "TARGA":
            scene.render.image_settings.color_mode = "RGBA"

        # Save
        temp_img.save_render(filepath=final_dst, scene=scene)

        # Restore render settings
        scene.render.image_settings.file_format = old_format
        scene.render.image_settings.quality = old_quality
        scene.render.image_settings.color_mode = old_color_mode

        return final_dst

    finally:
        bpy.data.images.remove(temp_img)


def _detect_format(filepath):
    """Detect image format from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    return EXTENSION_FORMATS.get(ext, "PNG")


def _needs_processing(settings):
    """Whether the given settings change the file (convert and/or resize)."""
    if not settings:
        return False
    convert_format = settings.get("convert_format")
    max_resolution = settings.get("max_resolution", 0)
    return (convert_format and convert_format != "ORIGINAL") or max_resolution > 0


def _output_format(source_path, settings):
    """Blender image format the source will be written as."""
    convert_format = settings.get("convert_format") if settings else None
    if convert_format and convert_format != "ORIGINAL":
        return convert_format
    return _detect_format(source_path)


def output_extension(source_path, settings):
    """
    Final file extension a bundled texture ends up with after process_textures.
    Returns the source extension unchanged when no processing alters it. This is
    the single authority both the copy step and the FBX path remap rely on so
    the written files and the FBX references cannot drift apart.
    """
    if not _needs_processing(settings):
        return os.path.splitext(source_path)[1]
    out_format = _output_format(source_path, settings)
    return FORMAT_EXTENSIONS.get(out_format, os.path.splitext(source_path)[1])


FORMAT_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "TARGA": ".tga",
    "TARGA_RAW": ".tga",
    "BMP": ".bmp",
    "TIFF": ".tiff",
    "OPEN_EXR": ".exr",
    "HDR": ".hdr",
    "WEBP": ".webp",
    "DDS": ".dds",
}

EXTENSION_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".tga": "TARGA",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
    ".exr": "OPEN_EXR",
    ".hdr": "HDR",
    ".webp": "WEBP",
    ".dds": "PNG",  # DDS not writable, convert to PNG
}
