"""
Service for managing farm, consultant and plot metadata from Notion databases.

This service allows you to store and retrieve complementary data that is not
in the main report page, such as farm details, consultant info, and plot specifications.

Setup:
1. Create databases in Notion:
   - "Fazendas" database with properties: Nome, Proprietário, Cidade, etc.
   - "Consultores" database with properties: Nome, Email, Telefone, etc.
   - "Talhões" database with properties: Nome, Área, Variedade, Fazenda (relation), etc.

2. Add database IDs to your .env:
   NOTION_FARMS_DATABASE_ID=xxx
   NOTION_CONSULTANTS_DATABASE_ID=xxx
   NOTION_PLOTS_DATABASE_ID=xxx

3. Use this service to fetch metadata:
   metadata_service = MetadataService()
   farm_data = await metadata_service.get_farm_by_name("Fazenda São José")
"""

import logging
from typing import Dict, Optional, Any
from notion_client import AsyncClient

from core.config import settings
from utils.notion_utils import extract_text

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for fetching farm, consultant, and plot metadata from Notion databases."""

    def __init__(self):
        self.token = settings.notion_token
        self.farms_db_id = getattr(settings, "notion_farms_database_id", None)
        self.consultants_db_id = getattr(
            settings, "notion_consultants_database_id", None
        )
        self.plots_db_id = getattr(settings, "notion_plots_database_id", None)

    async def get_farm_by_name(self, farm_name: str) -> Optional[Dict[str, Any]]:
        """
        Get farm metadata by name.

        Args:
            farm_name: Name of the farm to search for

        Returns:
            Dictionary with farm data: {
                'id': str,
                'name': str,
                'owner': str,
                'city': str,
                'consultant': str,
                'harvest_period': str,
                ...
            }
        """
        if not self.farms_db_id:
            logger.warning("NOTION_FARMS_DATABASE_ID not configured")
            return None

        try:
            async with AsyncClient(auth=self.token) as notion:
                # Query database filtering by farm name
                response = await notion.databases.query(
                    database_id=self.farms_db_id,
                    filter={
                        "property": "Nome",  # Adjust to your property name
                        "title": {"equals": farm_name},
                    },
                )

                results = response.get("results", [])
                if not results:
                    logger.warning(f"Farm not found: {farm_name}")
                    return None

                # Get first result
                page = results[0]
                props = page.get("properties", {})

                return self._parse_farm_properties(props)

        except Exception as e:
            logger.error(f"Error fetching farm '{farm_name}': {str(e)}")
            return None

    async def get_consultant_by_name(
        self, consultant_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get consultant metadata by name.

        Args:
            consultant_name: Name of the consultant

        Returns:
            Dictionary with consultant data
        """
        if not self.consultants_db_id:
            logger.warning("NOTION_CONSULTANTS_DATABASE_ID not configured")
            return None

        try:
            async with AsyncClient(auth=self.token) as notion:
                response = await notion.databases.query(
                    database_id=self.consultants_db_id,
                    filter={
                        "property": "Nome",
                        "title": {"equals": consultant_name},
                    },
                )

                results = response.get("results", [])
                if not results:
                    logger.warning(f"Consultant not found: {consultant_name}")
                    return None

                page = results[0]
                props = page.get("properties", {})

                return self._parse_consultant_properties(props)

        except Exception as e:
            logger.error(f"Error fetching consultant '{consultant_name}': {str(e)}")
            return None

    async def get_plot_metadata(
        self, plot_name: str, farm_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get plot metadata by name and optionally farm.

        Args:
            plot_name: Name of the plot (e.g., "Talhão 01", "Pivô 3")
            farm_name: Optional farm name to narrow search

        Returns:
            Dictionary with plot data: {
                'name': str,
                'area': float,
                'variety': str,
                'crop': str,
                ...
            }
        """
        if not self.plots_db_id:
            logger.warning("NOTION_PLOTS_DATABASE_ID not configured")
            return None

        try:
            async with AsyncClient(auth=self.token) as notion:
                # Build filter
                filter_config: Dict[str, Any] = {
                    "property": "Nome",
                    "title": {
                        "contains": plot_name
                    },  # Use 'contains' for partial match
                }

                response = await notion.databases.query(
                    database_id=self.plots_db_id,
                    filter=filter_config,
                )

                results = response.get("results", [])
                if not results:
                    logger.warning(f"Plot not found: {plot_name}")
                    return None

                # If multiple results and farm_name provided, filter by farm
                if len(results) > 1 and farm_name:
                    for page in results:
                        props = page.get("properties", {})
                        # Check if this plot belongs to the specified farm
                        # This assumes you have a "Fazenda" relation property
                        farm_relation = props.get("Fazenda", {}).get("relation", [])
                        if farm_relation:
                            # You would need to fetch the related farm page to check name
                            # For now, use the first result
                            pass

                # Get first result
                page = results[0]
                props = page.get("properties", {})

                return self._parse_plot_properties(props)

        except Exception as e:
            logger.error(f"Error fetching plot '{plot_name}': {str(e)}")
            return None

    async def enrich_report_with_metadata(self, report_data, farm_name: str = None):
        """
        Enrich report data with metadata from Notion databases.

        Args:
            report_data: Report object to enrich
            farm_name: Farm name to use for lookup (if not in report)

        Returns:
            Enriched report data
        """
        # Use farm_name from report if available
        farm_lookup = farm_name or getattr(report_data, "farm_name", None)

        if not farm_lookup:
            logger.warning("No farm name provided for metadata enrichment")
            return report_data

        # Get farm metadata
        farm_data = await self.get_farm_by_name(farm_lookup)
        if farm_data:
            report_data.farm_name = farm_data.get("name", farm_lookup)
            report_data.owner_name = farm_data.get("owner", "")
            report_data.farm_city = farm_data.get("city", "")
            report_data.consultant_name = farm_data.get("consultant", "")
            report_data.harvest_period = farm_data.get("harvest_period", "2025/2026")

        # Enrich plots with metadata
        for plot in getattr(report_data, "plots", []):
            plot_name = getattr(plot, "crop", "") or getattr(plot, "id", "")
            if plot_name:
                plot_meta = await self.get_plot_metadata(plot_name, farm_lookup)
                if plot_meta:
                    plot.area = plot_meta.get("area", 0.0)
                    plot.variety = plot_meta.get("variety", "")
                    plot.crop = plot_meta.get("crop", plot.crop)

        return report_data

    def _parse_farm_properties(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Notion farm properties into a clean dictionary."""
        return {
            "id": props.get("id"),
            "name": extract_text(props.get("Nome", {}).get("title", [])),
            "owner": extract_text(props.get("Proprietário", {}).get("rich_text", [])),
            "city": extract_text(props.get("Cidade", {}).get("rich_text", [])),
            "consultant": extract_text(props.get("Consultor", {}).get("rich_text", [])),
            "harvest_period": extract_text(props.get("Safra", {}).get("rich_text", [])),
            # Add more fields as needed
        }

    def _parse_consultant_properties(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Notion consultant properties into a clean dictionary."""
        return {
            "id": props.get("id"),
            "name": extract_text(props.get("Nome", {}).get("title", [])),
            "email": extract_text(props.get("Email", {}).get("rich_text", [])),
            "phone": extract_text(props.get("Telefone", {}).get("rich_text", [])),
        }

    def _parse_plot_properties(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Notion plot properties into a clean dictionary."""
        # Get area (can be number or rich_text)
        area = 0.0
        area_prop = props.get("Área", {})
        if area_prop.get("type") == "number":
            area = area_prop.get("number", 0.0) or 0.0
        else:
            area_text = extract_text(area_prop.get("rich_text", []))
            try:
                area = float(area_text) if area_text else 0.0
            except ValueError:
                area = 0.0

        return {
            "name": extract_text(props.get("Nome", {}).get("title", [])),
            "area": area,
            "variety": extract_text(props.get("Variedade", {}).get("rich_text", [])),
            "crop": extract_text(props.get("Cultura", {}).get("rich_text", [])),
        }
