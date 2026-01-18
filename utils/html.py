"""HTML manipulation utilities."""

import base64
import mimetypes
from pathlib import Path

from utils.logging import get_logger


logger = get_logger(__name__)


def data_uri_for_local_image(template_dir: Path, rel_path: str) -> str | None:
    """Convert local image to data URI."""
    logger.debug(f"[IMAGE] Converting to data URI | path={rel_path}")

    rel = rel_path.lstrip("./")
    img_path = template_dir / rel

    if not img_path.exists():
        try:
            root_templates = template_dir.parent.parent
            alt_path = root_templates / "assets" / rel
            if alt_path.exists():
                img_path = alt_path
            else:
                logger.warning(f"[IMAGE] Image not found | path={rel_path}")
                return None
        except Exception:
            logger.warning(f"[IMAGE] Image not found | path={rel_path}")
            return None

    try:
        data = img_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(img_path))
        if not mime:
            mime = "image/jpeg"
        b64 = base64.b64encode(data).decode("ascii")
        logger.debug(f"[IMAGE] Data URI created | size={len(data)} bytes")
        return f"data:{mime};base64,{b64}"
    except Exception:
        logger.error(
            f"[IMAGE] Failed to convert image | path={rel_path}", exc_info=True
        )
        return None


def inline_local_images(html: str, template_dir: Path) -> str:
    """Inline all local images in HTML as data URIs."""
    logger.debug(f"[INLINE] Starting image inlining | template_dir={template_dir}")

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

            q1 = html.find('"', idx)
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

    logger.debug("[INLINE] Image inlining completed")
    return html
