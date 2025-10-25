import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StorageUploader:
    """Optional S3 uploader to publish PDFs for Notion consumption.

    If environment variables are configured, uploads the file to S3 with a public URL.
    Otherwise, returns None and the caller can skip attaching the PDF in Notion.

    Required env vars:
      - S3_BUCKET_NAME
      - S3_REGION (optional but recommended)
      - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (or an instance profile/role)

    Optional:
      - S3_PUBLIC_BASE_URL: Override the URL root, e.g. https://cdn.example.com
    """

    @staticmethod
    def upload_file(file_path: str, key_prefix: str = "reports/") -> Optional[str]:
        bucket = os.getenv("S3_BUCKET_NAME", "").strip()
        if not bucket:
            logger.info("S3 upload skipped: S3_BUCKET_NAME not set")
            return None

        try:
            import boto3  # type: ignore
            # botocore is an optional dependency via boto3; no direct import needed here
        except Exception:
            logger.warning("S3 upload skipped: boto3 not installed")
            return None

        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning("S3 upload skipped: file not found %s", file_path)
                return None

            filename = path.name
            key = f"{key_prefix}{filename}"

            s3 = boto3.client("s3", region_name=os.getenv("S3_REGION"))

            extra_args = {"ContentType": "application/pdf"}
            # Make public if bucket policy allows; Notion must access it
            if os.getenv("S3_MAKE_PUBLIC", "true").lower() in ("1", "true", "yes"):
                extra_args["ACL"] = "public-read"

            s3.upload_file(str(path), bucket, key, ExtraArgs=extra_args)

            # Build URL
            public_base = os.getenv("S3_PUBLIC_BASE_URL", "").rstrip("/")
            if public_base:
                return f"{public_base}/{key}"

            # Default AWS URL pattern
            region = os.getenv("S3_REGION", "us-east-1")
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

        except Exception as e:
            logger.exception("S3 upload failed: %s", e)
            return None
