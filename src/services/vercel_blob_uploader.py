import logging
from pathlib import Path
from typing import Optional
import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class VercelBlobUploader:
    """Upload PDFs to Vercel Blob Storage and return public URL for Notion.

    When running on Vercel, the platform automatically injects BLOB_READ_WRITE_TOKEN.
    For local testing, you can set it manually or use a different upload method.

    The Vercel Blob API returns a public URL that Notion can access directly.
    """

    @staticmethod
    async def upload_file(file_path: str) -> Optional[str]:
        """Upload file to Vercel Blob and return public URL.

        Args:
            file_path: Local path to the PDF file

        Returns:
            Public URL of the uploaded file, or None if upload fails
        """
        # Vercel automatically injects this token when you connect a Blob store to your project
        token = settings.blob_read_write_token
        if not token:
            logger.info("Vercel Blob upload skipped: BLOB_READ_WRITE_TOKEN not set")
            return None

        # If user provided store_XXX format, that's the store ID, not the token
        # Vercel will inject the actual token automatically in production
        if token.startswith("store_"):
            logger.info(
                "BLOB_READ_WRITE_TOKEN looks like a store ID. "
                "On Vercel, the platform will inject the real token automatically. "
                "For local testing, get the actual token from the Vercel dashboard."
            )
            # Continue anyway in case Vercel injected the real token via other env var
            # or this is running in production where the platform handles it

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(
                    "Vercel Blob upload skipped: file not found %s", file_path
                )
                return None

            filename = path.name

            # Read file content
            file_content = path.read_bytes()

            # Vercel Blob upload endpoint (new API format)
            # https://vercel.com/docs/storage/vercel-blob/using-blob-sdk
            upload_url = "https://blob.vercel-storage.com"

            headers = {
                "Authorization": f"Bearer {token}",
                "x-content-type": "application/pdf",
            }

            # Use PUT with filename in query param
            params = {"filename": filename}

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.put(
                    upload_url,
                    params=params,
                    headers=headers,
                    content=file_content,
                )

                if response.status_code not in (200, 201):
                    logger.error(
                        f"Vercel Blob upload failed: {response.status_code} {response.text[:500]}"
                    )
                    return None

                result = response.json()
                public_url = result.get("url")

                if public_url:
                    logger.info(f"Uploaded PDF to Vercel Blob: {public_url}")
                    return public_url
                else:
                    logger.warning(
                        f"Vercel Blob response missing 'url' field: {result}"
                    )
                    return None

        except Exception as e:
            logger.exception(f"Vercel Blob upload failed: {e}")
            return None
