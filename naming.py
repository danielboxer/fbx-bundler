import re


def apply_convention(name, convention):
    """
    Convert a name string to the specified naming convention.

    Args:
        name: Original name (e.g., "My Cool Object.001")
        convention: One of 'ORIGINAL', 'PASCAL', 'SNAKE', 'KEBAB'

    Returns the converted name string, safe for filenames.
    """
    if convention == "ORIGINAL":
        return _sanitize_filename(name)

    # Split into words: handles spaces, underscores, hyphens, dots, camelCase
    words = _split_into_words(name)

    if not words:
        return _sanitize_filename(name)

    if convention == "PASCAL":
        return "".join(w.capitalize() for w in words)
    elif convention == "SNAKE":
        return "_".join(w.lower() for w in words)
    elif convention == "KEBAB":
        return "-".join(w.lower() for w in words)

    return _sanitize_filename(name)


def _split_into_words(name):
    """Split a name into component words, handling various formats."""
    # Remove Blender's .001 suffixes
    name = re.sub(r"\.\d{3}$", "", name)

    # Split on common delimiters
    parts = re.split(r"[\s_\-\.]+", name)

    # Further split camelCase/PascalCase within each part
    words = []
    for part in parts:
        if not part:
            continue
        # Split on camelCase boundaries
        sub_words = re.sub(r"([a-z])([A-Z])", r"\1 \2", part)
        sub_words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", sub_words)
        words.extend(sub_words.split())

    return [w for w in words if w]


def _sanitize_filename(name):
    """Remove characters that are invalid in filenames."""
    # Remove Blender's .001 suffixes
    name = re.sub(r"\.\d{3}$", "", name)
    # Replace invalid filename characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Collapse multiple underscores/spaces
    name = re.sub(r"[_\s]+", "_", name)
    return name.strip("_")
