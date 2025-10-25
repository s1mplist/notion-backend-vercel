import os
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import base64
import mimetypes
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    from PIL import Image
except ImportError:
    HTML = None
    CSS = None
    FontConfiguration = None
    Image = None

from src.models.report import Report

logger = logging.getLogger(__name__)


class PDFGeneratorWeasyPrint:
    """
    Otimized PDF generator using WeasyPrint with async image processing.

    Features:
    - Async image downloading and optimization
    - High-resolution image support with optimization
    - Template caching and optimization
    - Thread-safe PDF generation
    - Professional layout with optimized templates
    """

    def __init__(self):
        if HTML is None:
            raise ImportError(
                "WeasyPrint not installed. Install with: pip install weasyprint"
            )

        repo_root = Path(__file__).resolve().parents[2]
        self.template_dir = repo_root / "template"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            enable_async=True,
            auto_reload=False,  # Optimize for production
            cache_size=100,
        )

        # Use original templates (working version)
        self.report_template = self.env.get_template("report_template.html")

        # Read and cache CSS
        self._styles = self._read_styles()

        # Font configuration for better typography
        self.font_config = FontConfiguration()

        # Thread pool for sync operations
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Cache for processed images
        self._image_cache = {}
        self._cache_lock = threading.Lock()

    def _read_styles(self) -> str:
        """Read the original CSS file and return its contents."""
        # Use original styles (working version)
        css_path = self.template_dir / "styles.css"

        try:
            return css_path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("CSS file not found; continuing without styles")
            return ""

    async def _download_and_optimize_image(
        self, url: str, max_width: int = 1920, quality: int = 85
    ) -> Optional[str]:
        """
        Async download and optimize image for high-resolution PDF output.

        Args:
            url: Image URL to download
            max_width: Maximum width for optimization (default: 1920px for high-res)
            quality: JPEG quality (default: 85 for good quality)

        Returns:
            Base64 data URI or None if failed
        """
        if not url or not url.startswith(("http://", "https://")):
            return None

        # Check cache first
        cache_key = f"{url}_{max_width}_{quality}"
        with self._cache_lock:
            if cache_key in self._image_cache:
                return self._image_cache[cache_key]

        try:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to download image: {url} (status: {response.status})"
                        )
                        return None

                    # Check content type
                    content_type = response.headers.get("content-type", "")
                    if not content_type.startswith("image/"):
                        logger.warning(
                            f"URL is not an image: {url} (type: {content_type})"
                        )
                        return None

                    # Download and process in executor
                    image_data = await response.read()

                    # Optimize in thread pool
                    loop = asyncio.get_event_loop()
                    optimized_data = await loop.run_in_executor(
                        self._executor,
                        self._optimize_image_sync,
                        image_data,
                        max_width,
                        quality,
                    )

                    if optimized_data:
                        # Cache the result
                        with self._cache_lock:
                            self._image_cache[cache_key] = optimized_data

                        return optimized_data

        except Exception as e:
            logger.exception(f"Error downloading/optimizing image {url}: {e}")

        return None

    def _optimize_image_sync(
        self, image_data: bytes, max_width: int, quality: int
    ) -> Optional[str]:
        """Synchronously optimize image data using Pillow."""
        if not Image:
            # If Pillow not available, return base64 of original
            try:
                b64 = base64.b64encode(image_data).decode("ascii")
                return f"data:image/jpeg;base64,{b64}"
            except Exception:
                return None

        try:
            from io import BytesIO

            # Open and process image
            with Image.open(BytesIO(image_data)) as img:
                # Handle EXIF orientation
                try:
                    if hasattr(img, "_getexif") and img._getexif():
                        exif = img._getexif()
                        orientation_key = 274
                        if orientation_key in exif:
                            orientation = exif[orientation_key]
                            if orientation == 3:
                                img = img.rotate(180, expand=True)
                            elif orientation == 6:
                                img = img.rotate(270, expand=True)
                            elif orientation == 8:
                                img = img.rotate(90, expand=True)
                except Exception:
                    pass  # Continue without EXIF processing

                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img, mask=img.split()[1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize if needed (maintain aspect ratio)
                if img.width > max_width:
                    aspect_ratio = img.height / img.width
                    new_height = int(max_width * aspect_ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                # Save to bytes
                output = BytesIO()
                img.save(output, format="JPEG", quality=quality, optimize=True)
                output.seek(0)

                # Convert to base64
                b64 = base64.b64encode(output.getvalue()).decode("ascii")
                return f"data:image/jpeg;base64,{b64}"

        except Exception as e:
            logger.exception(f"Error optimizing image: {e}")

        return None

    def _data_uri_for_local_image(self, rel_path: str) -> Optional[str]:
        """Convert local image to data URI for embedding in HTML."""
        # Support ./images/... or images/...
        rel = rel_path.lstrip("./")
        img_path = self.template_dir / rel
        if not img_path.exists():
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

    def _inline_assets(self, html: str) -> str:
        """Inline CSS and local images into the HTML."""
        # Inline styles.css
        if 'href="styles.css"' in html:
            style_tag = f"<style>\n{self._styles}\n</style>"
            html = html.replace('<link rel="stylesheet" href="styles.css">', style_tag)
            # Try variations
            html = html.replace(
                '<link rel="stylesheet" href="./styles.css">', style_tag
            )

        # Inline local images used by templates (header logos, etc.)
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
                q1 = html.find('"', idx + len('src="'))
                q2 = html.find('"', q1 + 1)
                if q1 == -1 or q2 == -1:
                    break
                path_val = html[q1 + 1 : q2]
                data_uri = self._data_uri_for_local_image(path_val)
                if data_uri:
                    html = html[: q1 + 1] + data_uri + html[q2:]
                start = q2 + 1
        return html

    async def _process_report_images(self, report_data: Report) -> Report:
        """Process all images in the report asynchronously."""
        if not hasattr(report_data, "plots") or not report_data.plots:
            return report_data

        # Collect all image URLs
        image_tasks = []
        for plot in report_data.plots:
            if hasattr(plot, "images") and plot.images:
                for image in plot.images:
                    if hasattr(image, "url") and image.url:
                        image_tasks.append(self._download_and_optimize_image(image.url))

        # Download all images concurrently
        if image_tasks:
            logger.info(f"Processing {len(image_tasks)} images for high-resolution PDF")
            optimized_images = await asyncio.gather(
                *image_tasks, return_exceptions=True
            )

            # Update image URLs with optimized data URIs
            image_index = 0
            for plot in report_data.plots:
                if hasattr(plot, "images") and plot.images:
                    for image in plot.images:
                        if (
                            hasattr(image, "url")
                            and image.url
                            and image_index < len(optimized_images)
                        ):
                            result = optimized_images[image_index]
                            if isinstance(result, str) and result:
                                image.url = result  # Replace with data URI
                            image_index += 1

        return report_data

    async def _render_full_html(self, report_data: Report) -> str:
        """Render the complete HTML for the report with processed images."""
        next_visit = getattr(report_data, "next_visit_date", None)
        current_visit = getattr(report_data, "current_visit_date", None)

        context = {
            "farm_name": getattr(report_data, "farm_name", ""),
            "consultant_name": getattr(report_data, "consultant_name", ""),
            "report_month": getattr(report_data, "report_month", ""),
            "owner_name": getattr(report_data, "owner_name", ""),
            "farm_city": getattr(report_data, "farm_city", ""),
            "harvest_period": getattr(report_data, "harvest_period", ""),
            "general_info": getattr(report_data, "general_info", ""),
            "next_visit_date": next_visit.strftime("%d/%m/%Y") if next_visit else "",
            "current_visit_date": current_visit.strftime("%d/%m/%Y")
            if current_visit
            else "",
            "operations_schedule": getattr(report_data, "operations_schedule", ""),
            "plots": getattr(report_data, "plots", []) or [],
        }

        # Use async template rendering
        html = await self.report_template.render_async(**context)
        return self._inline_assets(html)

    async def generate_pdf(self, report_data: Report, output_path: str) -> str:
        """
        Generate high-quality PDF using WeasyPrint with async image processing.

        Args:
            report_data: Report model with data
            output_path: Directory to save the PDF

        Returns:
            Path to the generated PDF file
        """
        os.makedirs(output_path, exist_ok=True)

        logger.info("Starting PDF generation with async image processing")

        try:
            # Step 1: Process all images asynchronously
            processed_report = await self._process_report_images(report_data)

            # Step 2: Render HTML with processed images
            html_content = await self._render_full_html(processed_report)

            # Step 3: Generate PDF filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_pdf = os.path.join(output_path, f"report_{timestamp}.pdf")

            # Step 4: Generate PDF in thread pool (WeasyPrint is sync)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, self._generate_pdf_sync, html_content, final_pdf
            )

            logger.info("PDF (WeasyPrint) generated successfully at %s", final_pdf)
            return final_pdf

        except Exception as e:
            logger.exception("Failed to generate PDF: %s", e)
            raise RuntimeError(f"PDF generation failed: {e}")

    def _generate_pdf_sync(self, html_content: str, final_pdf: str) -> None:
        """Generate PDF synchronously in thread pool."""
        try:
            # Create HTML document
            html_doc = HTML(
                string=html_content, base_url=str(self.template_dir), encoding="utf-8"
            )

            # Create CSS document
            css_docs = []
            if self._styles:
                css_docs.append(CSS(string=self._styles, font_config=self.font_config))

            # Generate PDF with optimized settings
            html_doc.write_pdf(
                final_pdf,
                stylesheets=css_docs,
                font_config=self.font_config,
                presentational_hints=True,  # Better CSS support
            )

        except Exception as e:
            logger.exception("Sync PDF generation failed: %s", e)
            raise

    def generate_pdf_sync(self, report_data: Report, output_path: str) -> str:
        """Synchronous version of generate_pdf for compatibility."""
        return asyncio.run(self.generate_pdf(report_data, output_path))
