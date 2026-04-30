import os
import shutil

import bpy


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
        if convert_format and convert_format != "ORIGINAL":
            out_format = convert_format
        else:
            out_format = _detect_format(src_path)

        ext = FORMAT_EXTENSIONS.get(out_format, os.path.splitext(src_path)[1])
        dst_base = os.path.splitext(dst_path)[0]
        final_dst = dst_base + ext

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
