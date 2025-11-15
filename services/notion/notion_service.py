from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List

from notion_client import AsyncClient, Client

from api.config import get_settings
from models.report import Image, Plot
from utils.logging import get_logger
from utils.notion import NotionUtils


settings = get_settings()
logger = get_logger(__name__)


class NotionService:
    """Service for interacting with Notion API and Data Sources."""

    def __init__(self):
        self.client = None
        self.async_client = None
        self.notion_utils = NotionUtils()

        logger.info("NotionService initialized.")

    # -----------------------
    # Page retrieval
    # -----------------------
    def get_page(self, page_id: str) -> dict[str, Any]:
        """Retrieve a single page by ID (sync)."""
        with Client(auth=settings.notion_token) as client:
            return client.pages.retrieve(page_id=page_id)

    async def async_get_page(self, page_id: str) -> dict[str, Any]:
        """Async wrapper to retrieve a Notion page using shared async_client."""
        async with AsyncClient(auth=settings.notion_token) as notion:
            return await notion.pages.retrieve(page_id=page_id)

    def get_pages(self, page_ids: list[str]) -> list[dict[str, Any]]:
        """Retrieve multiple pages by IDs (sync)."""
        pages = [self.get_page(pid) for pid in page_ids]
        logger.info(f"Retrieved {len(pages)} pages.")
        return pages

    async def async_get_pages(self, page_ids: list[str]) -> list[dict[str, Any]]:
        """Retrieve multiple pages by IDs (async)."""
        tasks = [self.async_get_page(pid) for pid in page_ids]
        pages = await asyncio.gather(*tasks, return_exceptions=False)
        logger.info(f"Async retrieved {len(pages)} pages.")
        return pages

    # -----------------------
    # Data Source (query) wrappers
    # -----------------------
    def query_data_source(
        self, data_source_id: str, query: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Sync wrapper to query a Notion data source using shared client."""
        # Use a short-lived Client to guarantee closure after the request.
        with Client(auth=settings.notion_token) as client:
            if query:
                return client.data_sources.query(data_source_id, **query)
            return client.data_sources.query(data_source_id)

    async def async_query_data_source(
        self, data_source_id: str, query: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Async wrapper to query a Notion data source using shared async_client."""
        async with AsyncClient(auth=settings.notion_token) as notion:
            if query:
                return await notion.data_sources.query(data_source_id, **query)
            return await notion.data_sources.query(data_source_id)

    # -----------------------
    # Data source IDs helpers
    # -----------------------
    def get_data_source_id(self, database_id: str) -> str:
        """Get the first data source ID from a database (sync)."""
        with Client(auth=settings.notion_token) as client:
            db = client.databases.retrieve(database_id=database_id)
        ds_list = db.get("data_sources") or []

        logger.info(f"Retrieved data sources for database {database_id}: {ds_list}")

        if not ds_list:
            logger.error(f"Database {database_id} has no data sources.")
            raise RuntimeError(f"Database {database_id} does not have data_sources.")
        return ds_list[0]["id"]

    async def async_get_data_source_id(self, database_id: str) -> str:
        """Get the first data source ID from a database (async)."""
        async with AsyncClient(auth=settings.notion_token) as notion:
            db = await notion.databases.retrieve(database_id=database_id)
        ds_list = db.get("data_sources") or []

        logger.info(
            f"Async retrieved data sources for database {database_id}: {ds_list}"
        )

        if not ds_list:
            logger.error(f"Database {database_id} has no data sources (async).")
            raise RuntimeError(f"Database {database_id} does not have data_sources.")
        return ds_list[0]["id"]

    def get_fact_and_talhoes_data_sources(self) -> tuple[str, str]:
        """Get data source IDs for FACT and Talhões databases (sync)."""
        logger.info("Getting data source IDs for FACT and Talhões databases (sync).")
        fact_ds_id = self.get_data_source_id(settings.notion_fact_database_id)
        talhoes_ds_id = self.get_data_source_id(settings.notion_talhoes_database_id)
        return fact_ds_id, talhoes_ds_id

    async def async_get_fact_and_talhoes_data_sources(self) -> tuple[str, str]:
        """Asynchronously get data source IDs for FACT and Talhões databases (async)."""
        fact_ds_id = await self.async_get_data_source_id(
            settings.notion_fact_database_id
        )
        talhoes_ds_id = await self.async_get_data_source_id(
            settings.notion_talhoes_database_id
        )
        logger.info("Async retrieved data source IDs for FACT and Talhões databases.")
        return fact_ds_id, talhoes_ds_id

    async def get_data_source_ids(self) -> tuple[str, str]:
        """Legacy async helper that retrieves data source IDs using an async context."""
        async with AsyncClient(auth=settings.notion_token) as notion:
            fact_db = await notion.databases.retrieve(
                database_id=settings.notion_fact_database_id
            )

            talhoes_db = await notion.databases.retrieve(
                database_id=settings.notion_talhoes_database_id
            )

        logger.info("Retrieved data source IDs for FACT and Talhões databases.")

        fact_ds_id = fact_db["data_sources"][0]["id"]
        talhoes_ds_id = talhoes_db["data_sources"][0]["id"]
        return fact_ds_id, talhoes_ds_id

    # -----------------------
    # Page blocks (paginated)
    # -----------------------
    def get_page_blocks(self, block_id: str) -> list[dict[str, Any]]:
        """Retrieve all child blocks for a given page or block (paginated) (sync)."""
        results: list[dict[str, Any]] = []
        start_cursor: str | None = None
        # Keep the client open across the paginated loop and ensure it is closed after.
        with Client(auth=settings.notion_token) as client:
            while True:
                resp = client.blocks.children.list(
                    block_id=block_id, start_cursor=start_cursor
                )
                results.extend(resp.get("results", []))
                if not resp.get("has_more"):
                    break
                start_cursor = resp.get("next_cursor")
                if not start_cursor:
                    break
        return results

    async def async_get_page_blocks(self, block_id: str) -> list[dict[str, Any]]:
        """Async version of get_page_blocks (paginação) para evitar bloqueio."""
        results: list[dict[str, Any]] = []
        start_cursor: str | None = None
        async with AsyncClient(auth=settings.notion_token) as notion:
            while True:
                resp = await notion.blocks.children.list(
                    block_id=block_id, start_cursor=start_cursor
                )
                results.extend(resp.get("results", []))
                if not resp.get("has_more"):
                    break
                start_cursor = resp.get("next_cursor")
                if not start_cursor:
                    break
        return results

    # -----------------------
    # Page normalization / parsing
    # -----------------------
    def simplify_page(self, page: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Notion page to a simple dict (id + simplified properties)."""
        simplified: dict[str, Any] = {"id": page.get("id")}
        props = page.get("properties") or {}
        for key, prop in props.items():
            try:
                value = self.notion_utils.simplify_property(prop)
            except Exception:
                # em caso de erro no helper, keep raw prop for debugging
                logger.exception(f"Error simplifying property {key!r}")
                value = prop
            # se for título, guarda também em _title para compatibilidade
            if isinstance(prop, dict) and prop.get("type") == "title":
                simplified["_title"] = value
            simplified[key] = value
        return simplified

    def parse_data_source_results(
        self, ds_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse data source query results into simplified pages."""
        items: list[dict[str, Any]] = []
        for res in (
            ds_result.get("results") if isinstance(ds_result, dict) else ds_result
        ) or []:
            page = res.get("page") if isinstance(res, dict) and "page" in res else res
            if not isinstance(page, dict):
                continue
            items.append(self.simplify_page(page))
        return items

    # -----------------------
    # Domain-Specific Queries
    # -----------------------
    async def async_query_fact_by_page_id(
        self, fact_ds_id: str, page_id: str
    ) -> list[dict[str, Any]]:
        """Async version of query_fact_by_page_id."""
        query = {"filter": {"property": "title", "rich_text": {"contains": page_id}}}
        result = await self.async_query_data_source(fact_ds_id, query)
        return self.parse_data_source_results(result)

    def query_fact_by_page_id(
        self, fact_ds_id: str, page_id: str
    ) -> list[dict[str, Any]]:
        """Query FACT data source by page ID (sync)."""
        query = {"filter": {"property": "title", "rich_text": {"contains": page_id}}}
        result = self.query_data_source(fact_ds_id, query)
        return self.parse_data_source_results(result)

    async def async_query_talhoes_by_farm_id(
        self, talhoes_ds_id: str, farm_id: str
    ) -> list[dict[str, Any]]:
        """Async version of query Talhões by single farm id."""
        query = {"filter": {"property": "farm", "relation": {"contains": farm_id}}}
        result = await self.async_query_data_source(talhoes_ds_id, query)
        return self.parse_data_source_results(result)

    def query_talhoes_by_farm_id(
        self, talhoes_ds_id: str, farm_id: str
    ) -> list[dict[str, Any]]:
        """Query Talhões data source by farm relation ID (sync)."""
        query = {"filter": {"property": "farm", "relation": {"contains": farm_id}}}
        result = self.query_data_source(talhoes_ds_id, query)
        return self.parse_data_source_results(result)

    async def async_query_talhoes_by_farm_ids(
        self, talhoes_ds_id: str, farm_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Async version of query_talhoes_by_farm_ids."""
        all_talhoes: list[dict[str, Any]] = []
        for farm_id in farm_ids:
            query = {"filter": {"property": "farm", "relation": {"contains": farm_id}}}
            result = await self.async_query_data_source(talhoes_ds_id, query)
            talhoes = self.parse_data_source_results(result)
            all_talhoes.extend(talhoes)
        return all_talhoes

    def query_talhoes_by_farm_ids(
        self, talhoes_ds_id: str, farm_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Query Talhões data source by multiple farm IDs (sync)."""
        all_talhoes = []
        for farm_id in farm_ids:
            talhoes = self.query_talhoes_by_farm_id(talhoes_ds_id, farm_id)
            all_talhoes.extend(talhoes)
        return all_talhoes

    # -----------------------
    # Data Aggregation
    # -----------------------
    def summarize_talhoes(
        self,
        talhoes_pages: list[dict[str, Any]],
        area_property_name: str = "area",
        talhao_name_fallback: str = "_title",
    ) -> dict[str, Any]:
        """Aggregate talhões information (count, names, areas)."""
        total = len(talhoes_pages)
        nomes = []
        areas = []

        for p in talhoes_pages:
            # Try multiple name fields: nome_talhao, id_talhao, _title, name
            name = (
                p.get("nome_talhao")
                or p.get("id_talhao")
                or p.get("_title")
                or p.get("name")
                or p.get(talhao_name_fallback)
            )
            if name:
                nomes.append(name)
            area = p.get(area_property_name)
            # Convert area string from Brazilian decimal format (comma as decimal separator) to float-compatible format.
            if isinstance(area, str):
                area = area.replace(",", ".")

            try:
                area_float = float(area) if area else 0.0
                if area_float > 0:
                    areas.append(area_float)
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse area '{area}' for talhão '{name}': {e}")

        return {
            "quantidade_talhoes": total,
            "nomes_talhoes": nomes,
            "soma_areas": sum(areas) if areas else 0.0,
            "areas_individuais": areas,
        }

    def extract_farm_ids_from_fact_item(
        self, fact_item: dict[str, Any], farm_property_name: str = "farm"
    ) -> list[str]:
        """Extract farm relation IDs from a parsed FACT item."""
        farm_ids = fact_item.get(farm_property_name, [])
        if not isinstance(farm_ids, list):
            farm_ids = [farm_ids] if farm_ids else []
        return farm_ids

    # -----------------------
    # Helpers: merge plot metadata + images
    # -----------------------
    def merge_plot_data(
        self, talhoes_data: list[dict], plots_with_images: list[dict]
    ) -> list[Plot]:
        """
        Merge talhões metadata with plot images.

        Returns only plots that are present in plots_with_images.
        """
        merged_plots: list[Plot] = []
        plot_ids_with_images = set()
        plot_names_with_images = set()

        for plot in plots_with_images or []:
            if plot.get("id"):
                plot_ids_with_images.add(str(plot["id"]).strip())

            names = plot.get("name", [])
            if isinstance(names, list):
                for name in names:
                    if name:
                        plot_names_with_images.add(str(name).strip())
            elif names:
                plot_names_with_images.add(str(names).strip())

        logger.debug("Plot IDs with images: %s", plot_ids_with_images)
        logger.debug("Plot names with images: %s", plot_names_with_images)

        images_map_by_talhao_id: dict[str, dict] = {}
        images_map_by_name: dict[str, dict] = {}

        for plot in plots_with_images or []:
            talhao_id = plot.get("id")
            if talhao_id:
                images_map_by_talhao_id[str(talhao_id).strip()] = plot

            plot_names = plot.get("name") or []
            if isinstance(plot_names, (list, tuple)):
                for name in plot_names:
                    if name:
                        images_map_by_name[str(name).strip()] = plot
            elif plot_names:
                images_map_by_name[str(plot_names).strip()] = plot

        logger.debug(
            "Images mapped by talhao_id: %s", list(images_map_by_talhao_id.keys())
        )
        logger.debug("Images mapped by name: %s", list(images_map_by_name.keys()))

        try:
            logger.debug(
                "Images maps sizes -> by_id=%d by_name=%d; sample_ids=%s; sample_names=%s",
                len(images_map_by_talhao_id),
                len(images_map_by_name),
                list(images_map_by_talhao_id.keys())[:5],
                list(images_map_by_name.keys())[:5],
            )
        except Exception:
            pass

        def _talhao_index(t: dict) -> int:
            tid = str(t.get("id_talhao", ""))
            m = re.search(r"(\d+)", tid)
            return int(m.group(1)) if m else 10_000

        talhoes_sorted = sorted(talhoes_data or [], key=_talhao_index)

        for talhao in talhoes_sorted:
            talhao_id = str(talhao.get("id_talhao", "") or "")
            talhao_name = (
                talhao.get("nome_talhao")
                or talhao_id
                or talhao.get("_title")
                or talhao.get("name")
                or ""
            )

            talhao_appears_in_plots = False

            if talhao_id.strip() in plot_ids_with_images:
                talhao_appears_in_plots = True

            if str(talhao_name).strip() in plot_names_with_images:
                talhao_appears_in_plots = True

            if not talhao_appears_in_plots:
                logger.debug(
                    "Skipping talhão '%s' (id=%s): not present in plots_with_images",
                    talhao_name,
                    talhao_id,
                )
                continue

            area_val = talhao.get("area", 0.0) or 0.0
            if isinstance(area_val, str):
                area_val = area_val.strip().replace(",", ".")
            try:
                area_float = float(area_val)
            except (ValueError, TypeError):
                area_float = 0.0

            image_data: dict = {}
            # normalize matching keys
            norm_id = talhao_id.strip()
            norm_name = str(talhao_name).strip()

            matched_by_id = norm_id and norm_id in images_map_by_talhao_id
            matched_by_name = (
                (not matched_by_id) and norm_name and norm_name in images_map_by_name
            )

            if matched_by_id:
                image_data = images_map_by_talhao_id.get(norm_id, {})
                logger.debug("Matched talhão '%s' by ID: %s", talhao_name, norm_id)
            elif matched_by_name:
                image_data = images_map_by_name.get(norm_name, {})
                logger.debug("Matched talhão '%s' by name: %s", talhao_name, norm_name)
            else:
                logger.debug(
                    "No match for talhão '%s' (id=%s, name=%s). Will skip unless fallback available.",
                    talhao_name,
                    norm_id,
                    norm_name,
                )
                image_data = {}

            images_list: List[Image] = []
            for img in (
                image_data.get("images", [])
                if isinstance(image_data.get("images", []), (list, tuple))
                else []
            ):
                images_list.append(
                    Image(
                        url=img.get("url", "") or "",
                        description=img.get("name") or None,
                    )
                )

            assessment_raw = image_data.get("assessment", "")
            if isinstance(assessment_raw, list):
                assessment_text = (
                    (assessment_raw[0] or "").strip() if assessment_raw else ""
                )
            else:
                assessment_text = str(assessment_raw or "").strip()

            additional_images_val = image_data.get("additional_images")
            if isinstance(additional_images_val, list):
                additional_images_val = (
                    ", ".join([str(x) for x in additional_images_val if x]) or None
                )
            elif additional_images_val is not None:
                additional_images_val = str(additional_images_val).strip() or None

            growth_stage = ""
            gs = image_data.get("growth_stage")
            if isinstance(gs, (list, tuple)):
                growth_stage = gs[0] if gs else ""
            elif gs:
                growth_stage = str(gs)

            plot_names_from_image = image_data.get("name")
            if (
                isinstance(plot_names_from_image, list)
                and len(plot_names_from_image) > 1
            ):
                all_talhao_names = {
                    str(t.get("nome_talhao") or "").strip()
                    for t in talhoes_data
                    if t.get("nome_talhao")
                }

                valid_names = []
                for individual_name in plot_names_from_image:
                    name_str = str(individual_name).strip()

                    if name_str in all_talhao_names and name_str != talhao_name:
                        logger.debug(
                            "Skipping duplicate name '%s' for talhão '%s' (belongs to another talhão)",
                            name_str,
                            talhao_name,
                        )
                        continue
                    valid_names.append(name_str)

                if not valid_names:
                    valid_names = [talhao_name]

                logger.debug(
                    "Expanding talhão '%s' into %d plots (valid names: %s)",
                    talhao_name,
                    len(valid_names),
                    valid_names,
                )

                for individual_name in valid_names:
                    plot = Plot(
                        id=talhao_id,
                        name=individual_name,
                        area=area_float,
                        growth_stage=growth_stage,
                        crop=talhao.get("cultura", "") or "",
                        variety=talhao.get("variedade", "") or "",
                        images=images_list,
                        additional_images=additional_images_val,
                        assessment=assessment_text or "",
                    )
                    merged_plots.append(plot)
            else:
                single_name = (
                    plot_names_from_image[0]
                    if isinstance(plot_names_from_image, list) and plot_names_from_image
                    else talhao_name
                )
                plot = Plot(
                    id=talhao_id,
                    name=single_name,
                    area=area_float,
                    growth_stage=growth_stage,
                    crop=talhao.get("cultura", "") or "",
                    variety=talhao.get("variedade", "") or "",
                    images=images_list,
                    additional_images=additional_images_val,
                    assessment=assessment_text or "",
                )
                merged_plots.append(plot)

        return merged_plots

    def debug_page_properties(self, page_id: str) -> Dict[str, Any]:
        """
        Debug helper para inspecionar propriedades de uma página.
        Retorna informações sobre propriedades relacionadas a talhões.
        """
        page = self.get_page(page_id)
        properties = page.get("properties", {})

        # Encontrar todas as propriedades de talhão
        talhao_props = self.notion_utils.find_all_talhao_properties(
            properties, "talhao visitado"
        )

        estagio_props = self.notion_utils.find_all_talhao_properties(
            properties, "estadio fenologico"
        )

        avaliacao_props = self.notion_utils.find_all_talhao_properties(
            properties, "avaliacao"
        )

        result = {
            "total_properties": len(properties),
            "all_property_keys": sorted(properties.keys()),
            "talhao_properties": talhao_props,
            "estagio_properties": estagio_props,
            "avaliacao_properties": avaliacao_props,
            "sample_data": {},
        }

        # Adicionar dados de exemplo do primeiro talhão encontrado
        if talhao_props:
            first_index = min(talhao_props.keys())
            first_key = talhao_props[first_index]
            result["sample_data"] = {
                "index": first_index,
                "key": first_key,
                "data": properties[first_key],
            }

        return result
