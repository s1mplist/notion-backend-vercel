"""
Service for processing webhook data and coordinating report generation.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional

from models import WebhookRequest
from models.generation import GenerationMetadata
from services.notion_service import NotionService
from services.plot_data_extractor import PlotDataExtractor
from services.notion_mapper import NotionDataMapper
from services.notion_writer import NotionWriter

logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Service for processing webhook data and generating reports."""

    def __init__(self):
        self.notion_service = NotionService()
        self.plot_extractor = PlotDataExtractor()
        self.data_mapper = NotionDataMapper()

    async def process_webhook_data(
        self, gen_meta: GenerationMetadata, webhook_data: WebhookRequest
    ) -> Dict:
        """
        Process webhook data from Notion and coordinate report generation.

        Args:
            gen_meta: Generation metadata
            webhook_data: Validated webhook data from Notion

        Returns:
            dict: Processing result with status information
        """
        try:
            logger.info(f"Processing webhook event: {webhook_data.type}")

            # 1. Extract and validate page ID
            page_id = self._extract_page_id(webhook_data)

            # 2. Get data from Notion
            notion_data = await self.notion_service.get_page(page_id)
            notion_id = self._validate_notion_id(notion_data)

            # 3. Get plots data
            plots_data = await self.plot_extractor.extract_plots_data(notion_id)

            # 4. Resolve farm name from database
            farm_name = await self._resolve_farm_name(webhook_data, notion_data)

            # 5. Map data to report model
            report_data = self.data_mapper.map_to_report(notion_data, plots_data)
            self._inject_farm_name(report_data, farm_name)

            # 6. Update generation metadata
            gen_meta.generation_completed_at = datetime.now()
            gen_meta.generation_status = "success"

            # 7. Create Notion record if configured
            notion_record_page_id = await self._create_notion_record(
                webhook_data, gen_meta, report_data, pdf_url=None
            )

            return self._build_success_response(
                pdf_path=None,  # PDF generation disabled
                notion_record_page_id=notion_record_page_id,
                pdf_public_url=None,
            )

        except Exception as e:
            logger.error(f"Error processing webhook data: {str(e)}", exc_info=True)
            await self._handle_error(webhook_data, gen_meta, e)
            raise

    def _extract_page_id(self, webhook_data: WebhookRequest) -> str:
        """Extract and validate page ID from webhook data."""
        page_id = webhook_data.entity.get("id")
        if not isinstance(page_id, str) or not page_id:
            raise ValueError("Invalid or missing Notion page ID in webhook data.")
        return page_id

    def _validate_notion_id(self, notion_data: Dict) -> str:
        """Validate notion ID from page data."""
        notion_id = notion_data.get("id")
        if not isinstance(notion_id, str) or not notion_id:
            raise ValueError("Invalid or missing Notion page ID in Notion data.")
        return notion_id

    async def _resolve_farm_name(
        self, webhook_data: WebhookRequest, notion_data: Dict
    ) -> str:
        """Try to resolve the database title (farm name)."""
        database_id = (
            (webhook_data.data or {}).get("parent", {}).get("id")
            if isinstance(webhook_data.data, dict)
            else None
        ) or notion_data.get("parent", {}).get("database_id")

        farm_name = ""
        if isinstance(database_id, str) and database_id:
            try:
                farm_name = await self.notion_service.get_database_title(database_id)
                logger.debug(
                    f"Resolved farm name from database '{database_id}': {farm_name}"
                )
            except Exception as e:
                logger.warning(
                    f"Could not resolve database title for {database_id}: {e}"
                )

        return farm_name

    def _inject_farm_name(self, report_data, farm_name: str):
        """Inject farm name into report data if available."""
        if farm_name:
            try:
                report_data.farm_name = farm_name
            except Exception:
                pass

    async def _create_notion_record(
        self,
        webhook_data: WebhookRequest,
        gen_meta: GenerationMetadata,
        report_data,
        pdf_url: Optional[str],
    ) -> Optional[str]:
        """Create a record in Notion database if configured."""
        output_db_id = os.getenv("NOTION_OUTPUT_DATABASE_ID", "").strip()
        if not output_db_id:
            return None

        try:
            # Title for the record
            title = f"Relatório - {report_data.farm_name or 'Fazenda'} - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

            # Create record in Notion
            notion_record_page_id = await NotionWriter.create_generation_record(
                database_id=output_db_id,
                title=title,
                payload=webhook_data.dict(),
                metadata=gen_meta,
                pdf_url=pdf_url,
                additional_fields={
                    "Farm": getattr(report_data, "farm_name", "") or "",
                    "Fazenda": getattr(report_data, "farm_name", "") or "",
                    "Report Month": getattr(report_data, "report_month", "") or "",
                },
            )
            logger.info(
                f"Created Notion generation record: {notion_record_page_id} (db: {output_db_id})"
            )
            return notion_record_page_id
        except Exception as e:
            logger.exception(f"Failed to create Notion generation record: {e}")
            return None

    def _build_success_response(
        self,
        pdf_path: Optional[str],
        notion_record_page_id: Optional[str],
        pdf_public_url: Optional[str],
    ) -> Dict:
        """Build success response dictionary."""
        return {
            "status": "success",
            "message": "Report data processed successfully (PDF generation disabled)",
            "pdf_path": pdf_path,  # Will be None until new service is implemented
            "notion_record_page_id": notion_record_page_id,
            "pdf_public_url": pdf_public_url,  # Will be None until new service is implemented
        }

    async def _handle_error(
        self,
        webhook_data: WebhookRequest,
        gen_meta: GenerationMetadata,
        error: Exception,
    ):
        """Handle errors by creating error record in Notion if configured."""
        try:
            # Best-effort: write failed metadata if configured
            output_db_id = os.getenv("NOTION_OUTPUT_DATABASE_ID", "").strip()
            if output_db_id:
                error_meta = GenerationMetadata(
                    webhook_id=webhook_data.id,
                    webhook_timestamp=webhook_data.timestamp,
                    entity_id=webhook_data.entity.get("id"),
                    generation_started_at=None,
                    generation_completed_at=datetime.now(),
                    generation_status="error",
                    generation_error=str(error),
                )
                title = (
                    f"Relatório - ERRO - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                )
                await NotionWriter.create_generation_record(
                    database_id=output_db_id,
                    title=title,
                    payload=webhook_data.dict(),
                    metadata=error_meta,
                    pdf_url=None,
                )
        except Exception:
            # Don't mask original error
            pass
