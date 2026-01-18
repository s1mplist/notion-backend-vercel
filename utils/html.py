"""HTML manipulation utilities."""

import base64
import mimetypes
from pathlib import Path

from utils.logging import get_logger


logger = get_logger(__name__)


def data_uri_for_local_image(template_dir: Path, rel_path: str) -> str | None:
    """Convert local image to data URI for embedding in HTML.

    Args:
        template_dir: Base directory for templates
        rel_path: Relative path to the image (e.g., './images/logo.png')

    Returns:
        Data URI string or None if conversion fails
    """
    # Support ./images/... or images/...
    rel = rel_path.lstrip("./")
    img_path = template_dir / rel

    # Fallback: try templates/assets/<rel> (so ./images/... resolves to templates/assets/images/...)
    if not img_path.exists():
        try:
            root_templates = template_dir.parent.parent  # .../templates
            alt_path = root_templates / "assets" / rel
            if alt_path.exists():
                img_path = alt_path
            else:
                return None
        except Exception:
            return None

    try:
        data = img_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(img_path))
        if not mime:
            mime = "image/jpeg"
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.exception("Failed to inline image %s: %s", img_path, e)
        return None


def inline_local_images(html: str, template_dir: Path) -> str:
    """Inline local images into HTML as data URIs.

    Args:
        html: HTML content
        template_dir: Base directory for templates

    Returns:
        HTML with inlined images
    """
    markers = [
        'src="./images/',
        'src="images/',
    ]

    for marker in markers:
        start = 0
        while True:
            idx = html.find(marker, start)
            if idx == -1:
                break

            # Find the opening and closing quotes of the src attribute
            q1 = html.find('"', idx)  # the first quote after src=
            q2 = html.find('"', q1 + 1)

            if q1 == -1 or q2 == -1:
                break

            path_val = html[q1 + 1 : q2]
            data_uri = data_uri_for_local_image(template_dir, path_val)

            if data_uri:
                html = html[: q1 + 1] + data_uri + html[q2:]
                start = q1 + 1 + len(data_uri)
            else:
                start = q2 + 1

    return html
