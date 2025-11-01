import traceback
from typing import Any

from fastapi import HTTPException

from services.notion.notion_service import NotionService


class RelatorioService:
    """Service for orchestrating report generation from Notion data."""

    def __init__(self):
        self.notion = NotionService()

    def gerar_relatorio(self, template: str, page_id: str) -> dict[str, Any]:
        """
        Entry point for report generation.

        Args:
            template: Report template identifier
            page_id: FACT page ID to generate report for

        Note:
            The property name used to extract farm IDs from the FACT item is parameterized as 'farm_property_name'.
            If the FACT schema changes, update this property name accordingly.

        Returns:
            Dictionary with aggregated report data

        Raises:
            HTTPException: If page not found or processing fails
        """
        try:
            # Normalize page_id (remove dashes)
            normalized_page_id = page_id.replace("-", "")

            # 1. Get data source IDs
            fact_ds_id, talhoes_ds_id = self.notion.get_fact_and_talhoes_data_sources()

            # 2. Query FACT by normalized_page_id
            fact_items = self.notion.query_fact_by_page_id(
                fact_ds_id, normalized_page_id
            )

            if not fact_items:
                raise HTTPException(
                    status_code=404, detail=f"FACT page {page_id} não encontrada"
                )

            # 3. Extract farm relation IDs from FACT
            fact_item = fact_items[0]
            # If the FACT schema changes, update 'farm_property_name' accordingly
            farm_property_name = "farm"
            farm_ids = self.notion.extract_farm_ids_from_fact_item(
                fact_item, property_name=farm_property_name
            )

            # 4. Query talhões by farm IDs
            talhoes_items = []
            if farm_ids:
                talhoes_items = self.notion.query_talhoes_by_farm_ids(
                    talhoes_ds_id, farm_ids
                )

            # 5. Aggregate talhões data
            resumo_talhoes = self.notion.summarize_talhoes(talhoes_items)
            # 6. Resolve farm name
            # Only the first farm_id is used to resolve the farm name.
            # If there are multiple farms, only one name will be shown.
            farm_name = None
            if farm_ids:
                farm_name = self.notion.resolve_page_title(farm_ids[0])

            # 7. Build response
            return self._build_response(
                template=template,
                page_id=normalized_page_id,
                fact_items=fact_items,
                farm_ids=farm_ids,
                talhoes_items=talhoes_items,
                resumo_talhoes=resumo_talhoes,
                farm_name=farm_name,
            )

        except Exception as exc:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    def _build_response(
        self,
        template: str,
        page_id: str,
        fact_items: list,
        farm_ids: list,
        talhoes_items: list,
        resumo_talhoes: dict,
        farm_name: str | None,
    ) -> dict[str, Any]:
        """Build the final report response structure."""
        return {
            "template": template,
            "page_id": page_id,
            "fact": {
                "total_itens": len(fact_items),
                "itens": fact_items,
            },
            "talhoes": {
                "farm_ids": farm_ids,
                "itens": talhoes_items,
                "resumo": resumo_talhoes,
                "fazenda_nome": farm_name,
            },
        }
