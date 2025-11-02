"""Client for Vercel PDF generation service."""

import logging

import httpx

from core.config import settings


logger = logging.getLogger(__name__)


class VercelPDFClient:
    """Client for Vercel Node.js PDF service."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.public_base_url
        self.endpoint = f"{self.base_url}/api/generate-pdf"

    async def generate_pdf(
        self,
        html_content: str,
        format: str = "A3",
        landscape: bool = False,
        print_background: bool = True,
        margin: dict[str, str] | None = None,
        timeout: float = 60.0,
        # novos parâmetros de otimização
        optimize_images: bool = True,
        max_image_width: int = 1000,
        jpeg_quality: float = 0.5,
    ) -> bytes:
        """
        Generate PDF from HTML using Vercel Node.js function.

        Args:
            html_content: HTML string
            format: Page format (A3, A4, Letter, etc.)
            landscape: Landscape orientation
            print_background: Print background graphics
            margin: Page margins (top, right, bottom, left)
            timeout: Request timeout in seconds

        Returns:
            PDF as bytes

        Raises:
            HTTPError: If PDF generation fails
        """
        try:
            logger.info(f"Generating PDF via Vercel service: {self.endpoint}")
            logger.debug(f"HTML length: {len(html_content)} chars")

            # Prepare payload
            payload = {
                "html": html_content,
                "options": {
                    "format": format,
                    "landscape": landscape,
                    "printBackground": print_background,
                    "preferCSSPageSize": True,
                    # passa flags ao Node
                    "optimizeImages": optimize_images,
                    "maxImageWidth": max_image_width,
                    "jpegQuality": jpeg_quality,
                },
            }

            if margin:
                payload["options"]["margin"] = margin

            # Call PDF service
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                    },
                )

                response.raise_for_status()

            pdf_bytes = response.content

            # Log metrics
            generation_time = response.headers.get("X-Generation-Time", "unknown")
            pdf_size = len(pdf_bytes)
            pdf_size_mb = pdf_size / 1024 / 1024

            logger.info(
                f"PDF generated successfully: "
                f"size={pdf_size_mb:.2f}MB, "
                f"time={generation_time}ms"
            )

            return pdf_bytes

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error generating PDF: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise

        except httpx.TimeoutException:
            logger.error(f"Timeout generating PDF (timeout={timeout}s)")
            raise

        except Exception as e:
            logger.error(f"Unexpected error generating PDF: {e}", exc_info=True)
            raise


# Singleton instance
_pdf_client: VercelPDFClient | None = None


def get_pdf_client() -> VercelPDFClient:
    """Get or create PDF client singleton."""
    global _pdf_client
    if _pdf_client is None:
        _pdf_client = VercelPDFClient()
    return _pdf_client
