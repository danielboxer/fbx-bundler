from mathutils import Vector


def _world_bounds(objects):
    """
    Combined world-space bounding box of all mesh objects as (min, max) Vectors.
    Returns (None, None) when there are no mesh objects.
    """
    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))
    has_mesh = False

    for obj in objects:
        if obj.type != "MESH" or not obj.data:
            continue
        has_mesh = True
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            min_corner.x = min(min_corner.x, world_corner.x)
            min_corner.y = min(min_corner.y, world_corner.y)
            min_corner.z = min(min_corner.z, world_corner.z)
            max_corner.x = max(max_corner.x, world_corner.x)
            max_corner.y = max(max_corner.y, world_corner.y)
            max_corner.z = max(max_corner.z, world_corner.z)

    if not has_mesh:
        return None, None
    return min_corner, max_corner


def check_scale(objects, global_scale=1.0, report_func=None):
    """
    Verify the scale of objects being exported and warn about potential issues.

    Args:
        objects: List of Blender objects to check
        global_scale: The export global scale factor
        report_func: Callable(type_set, message) for reporting warnings

    Returns a list of warning strings (empty if no issues).
    """
    warnings = []

    if not objects:
        return warnings

    min_corner, max_corner = _world_bounds(objects)
    if min_corner is None:
        return warnings

    dimensions = max_corner - min_corner
    # Apply global scale to get final exported dimensions
    final_dims = dimensions * global_scale

    max_dim = max(final_dims.x, final_dims.y, final_dims.z)

    # Check for common scale issues
    if max_dim < 0.001:
        warnings.append(
            f"Very small: largest dimension is {max_dim:.6f}m. "
            "Objects may be invisible in engine"
        )
    elif max_dim < 0.01:
        warnings.append(
            f"Small: largest dimension is {max_dim:.4f}m. "
            "This might be unintentionally tiny"
        )
    elif max_dim > 1000:
        warnings.append(
            f"Very large: largest dimension is {max_dim:.1f}m. "
            "This might be unintentionally huge"
        )
    elif max_dim > 100:
        warnings.append(
            f"Large: largest dimension is {max_dim:.1f}m. Verify this is intended"
        )

    # Check for non-uniform scale on objects
    for obj in objects:
        if obj.type != "MESH":
            continue
        s = obj.scale
        if abs(s.x - s.y) > 0.001 or abs(s.y - s.z) > 0.001 or abs(s.x - s.z) > 0.001:
            warnings.append(
                f"'{obj.name}' has non-uniform scale ({s.x:.3f}, {s.y:.3f}, {s.z:.3f}). "
                "Apply scale (Ctrl+A) before export"
            )
        elif abs(s.x - 1.0) > 0.001:
            warnings.append(
                f"'{obj.name}' has unapplied scale ({s.x:.3f}). "
                "Consider applying scale (Ctrl+A)"
            )

    # Check for objects not at origin (common mistake for single-asset export)
    if len(objects) == 1:
        obj = objects[0]
        loc = obj.location
        if loc.length > 0.01:
            warnings.append(
                f"'{obj.name}' is not at origin (offset: {loc.length:.3f}m). "
                "This may cause pivot issues in engine"
            )

    # Report warnings if callback provided
    if report_func and warnings:
        for w in warnings:
            report_func({"WARNING"}, f"Scale check: {w}")

    return warnings


def get_dimensions_string(objects, global_scale=1.0):
    """Get a formatted string showing the export dimensions."""
    if not objects:
        return "No objects"

    min_corner, max_corner = _world_bounds(objects)
    if min_corner is None:
        return "No mesh objects"

    dims = (max_corner - min_corner) * global_scale
    return f"{dims.x:.3f} x {dims.y:.3f} x {dims.z:.3f}m"
