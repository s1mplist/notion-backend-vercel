"""Image optimization utilities."""

import base64
import io

from PIL import Image

from utils.logging import get_logger


logger = get_logger(__name__)


def optimize_base64_image(
    base64_data: str,
    max_width: int = 2000,
    max_height: int = 2000,
    quality: int = 85,
    format: str = "JPEG",
) -> str:
    """
    Optimize base64 encoded image.

    Args:
        base64_data: Base64 string (without data:image prefix)
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (0-100)
        format: Output format (JPEG, PNG, WEBP)

    Returns:
        Optimized base64 string
    """
    try:
        # Decode base64
        image_bytes = base64.b64decode(base64_data)
        original_size = len(image_bytes)

        # Open image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert RGBA to RGB for JPEG
        if format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background

        # Resize if needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image: {img.size}")

        # Compress
        output = io.BytesIO()
        save_kwargs = {"format": format, "optimize": True}

        if format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["progressive"] = True
        elif format == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6  # Max compression

        img.save(output, **save_kwargs)

        # Encode back to base64
        optimized_bytes = output.getvalue()
        optimized_base64 = base64.b64encode(optimized_bytes).decode("utf-8")

        reduction = (1 - len(optimized_bytes) / original_size) * 100

        logger.info(
            f"Optimized image: {original_size / 1024:.1f}KB → "
            f"{len(optimized_bytes) / 1024:.1f}KB ({reduction:.1f}% reduction)"
        )

        return optimized_base64

    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return base64_data  # Return original on error


def optimize_html_images(html_content: str, quality: int = 60) -> str:
    """
    Optimize all base64 images in HTML content.

    Args:
        html_content: HTML string with base64 images
        quality: JPEG quality (0-100)

    Returns:
        HTML with optimized images
    """
    import re

    pattern = r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)"

    def replace_image(match):
        try:
            base64_data = match.group(1)
            optimized = optimize_base64_image(
                base64_data, max_width=1200, quality=quality
            )
            return f"data:image/jpeg;base64,{optimized}"
        except Exception as e:
            logger.error(f"Error replacing image: {e}")
            return match.group(0)  # Return original on error

    # Count images
    image_count = len(re.findall(pattern, html_content))
    logger.info(f"Optimizing {image_count} images in HTML...")

    # Replace all images
    optimized_html = re.sub(pattern, replace_image, html_content)

    # Calculate size reduction
    original_size = len(html_content)
    optimized_size = len(optimized_html)
    reduction = (1 - optimized_size / original_size) * 100

    logger.info(
        f"HTML optimized: {original_size / 1024:.1f}KB → "
        f"{optimized_size / 1024:.1f}KB ({reduction:.1f}% reduction)"
    )

    return optimized_html
