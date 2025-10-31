from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from notion_client import Client
from core.config import settings


class NotionService:
    """Service for interacting with Notion API and Data Sources."""

    def __init__(self):
        self.client = Client(auth=settings.notion_token)

    # -----------------------
    # Data Source Operations
    # -----------------------
    def get_data_source_id(self, database_id: str) -> str:
        """Get the first data source ID from a database."""
        db = self.client.databases.retrieve(database_id)
        ds_list = db.get("data_sources") or []
        if not ds_list:
            raise RuntimeError(f"Database {database_id} não possui data_sources.")
        return ds_list[0]["id"]

    def query_data_source(
        self, data_source_id: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a query on a data source."""
        return self.client.data_sources.query(data_source_id, **query)

    def get_fact_and_talhoes_data_sources(self) -> Tuple[str, str]:
        """Get data source IDs for FACT and Talhões databases."""
        fact_ds_id = self.get_data_source_id(settings.notion_fact_database_id)
        talhoes_ds_id = self.get_data_source_id(settings.notion_talhoes_database_id)
        return fact_ds_id, talhoes_ds_id

    # -----------------------
    # Page Operations
    # -----------------------
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a single page by ID."""
        return self.client.pages.retrieve(page_id)

    def get_page_blocks(self, block_id: str) -> List[Dict[str, Any]]:
        """Retrieve all child blocks for a given page or block (paginated)."""
        results: List[Dict[str, Any]] = []
        start_cursor: Optional[str] = None
        while True:
            resp = self.client.blocks.children.list(
                block_id=block_id, start_cursor=start_cursor
            )
            results.extend(resp.get("results", []))
            if not resp.get("has_more"):
                break
            start_cursor = resp.get("next_cursor")
            if not start_cursor:
                break
        return results

    def get_pages(self, page_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve multiple pages by IDs."""
        pages = []
        for pid in page_ids:
            try:
                pages.append(self.get_page(pid))
            except Exception as exc:
                print(f"Falha ao obter página {pid}: {exc}")
        return pages

    def resolve_page_title(self, page_id: str) -> Optional[str]:
        """Get the title property value from a page."""
        try:
            page = self.get_page(page_id)
            props = page.get("properties") or {}
            for v in props.values():
                if v.get("type") == "title":
                    return self._extract_title(v)
        except Exception:
            pass
        return None

    # -----------------------
    # Property Extractors
    # -----------------------
    def _plain_text(self, rich: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array."""
        return "".join((t.get("plain_text") or "") for t in (rich or []))

    def _extract_title(self, prop: Dict[str, Any]) -> str:
        return self._plain_text(prop.get("title") or [])

    def _extract_rich_text(self, prop: Dict[str, Any]) -> str:
        return self._plain_text(prop.get("rich_text") or [])

    def _extract_relation_ids(self, prop: Dict[str, Any]) -> List[str]:
        rel = prop.get("relation") or []
        return [r.get("id", "").replace("-", "") for r in rel if r.get("id")]

    def _extract_select(self, prop: Dict[str, Any]) -> Optional[str]:
        sel = prop.get("select")
        return sel["name"] if sel else None

    def _extract_multi_select(self, prop: Dict[str, Any]) -> List[str]:
        return [s["name"] for s in (prop.get("multi_select") or [])]

    def _extract_date(self, prop: Dict[str, Any]) -> Dict[str, Optional[str]]:
        d = prop.get("date") or {}
        return {"start": d.get("start"), "end": d.get("end")}

    def _extract_files(self, prop: Dict[str, Any]) -> List[str]:
        files = []
        for f in prop.get("files") or []:
            if f.get("type") == "file":
                files.append(f["file"]["url"])
            elif f.get("type") == "external":
                files.append(f["external"]["url"])
        return files

    def _simplify_property(self, prop: Dict[str, Any]) -> Any:
        """Convert a Notion property to a simplified value."""
        ptype = prop.get("type")
        if ptype == "title":
            return self._extract_title(prop)
        if ptype == "rich_text":
            return self._extract_rich_text(prop)
        if ptype == "number":
            return prop.get("number")
        if ptype == "select":
            return self._extract_select(prop)
        if ptype == "multi_select":
            return self._extract_multi_select(prop)
        if ptype == "relation":
            return self._extract_relation_ids(prop)
        if ptype == "people":
            return [p.get("name") for p in (prop.get("people") or [])]
        if ptype == "date":
            return self._extract_date(prop)
        if ptype == "checkbox":
            return prop.get("checkbox")
        if ptype == "url":
            return prop.get("url")
        if ptype == "email":
            return prop.get("email")
        if ptype == "phone_number":
            return prop.get("phone_number")
        if ptype == "status":
            s = prop.get("status")
            return s.get("name") if s else None
        if ptype == "files":
            return self._extract_files(prop)
        return prop.get(ptype)

    # -----------------------
    # Page Parsing
    # -----------------------
    def simplify_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Notion page to a simplified dictionary."""
        props = page.get("properties") or {}
        simple = {k: self._simplify_property(v) for k, v in props.items()}

        # Add metadata
        title = None
        for k, v in props.items():
            if v.get("type") == "title":
                title = self._extract_title(v)
                break

        simple["_id"] = page.get("id", "").replace("-", "")
        simple["_url"] = page.get("url")
        if title is not None:
            simple["_title"] = title

        return simple

    def parse_data_source_results(
        self, ds_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse data source query results into simplified pages."""
        items = []
        for res in ds_result.get("results") or []:
            page = res.get("page") if isinstance(res, dict) and "page" in res else res
            if not isinstance(page, dict):
                continue
            items.append(self.simplify_page(page))
        return items

    # -----------------------
    # Domain-Specific Queries
    # -----------------------
    def query_fact_by_page_id(
        self, fact_ds_id: str, page_id: str
    ) -> List[Dict[str, Any]]:
        """Query FACT data source by page ID."""
        query = {"filter": {"property": "title", "rich_text": {"contains": page_id}}}
        result = self.query_data_source(fact_ds_id, query)
        return self.parse_data_source_results(result)

    def query_talhoes_by_farm_id(
        self, talhoes_ds_id: str, farm_id: str
    ) -> List[Dict[str, Any]]:
        """Query Talhões data source by farm relation ID."""
        query = {"filter": {"property": "farm", "relation": {"contains": farm_id}}}
        result = self.query_data_source(talhoes_ds_id, query)
        return self.parse_data_source_results(result)

    def query_talhoes_by_farm_ids(
        self, talhoes_ds_id: str, farm_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Query Talhões data source by multiple farm IDs."""
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
        talhoes_pages: List[Dict[str, Any]],
        area_property_name: str = "area",
        talhao_name_fallback: str = "_title",
    ) -> Dict[str, Any]:
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
            # Handle Brazilian decimal format (comma as decimal separator)
            if isinstance(area, str):
                area = area.replace(",", ".")

            try:
                area_float = float(area) if area else 0.0
                if area_float > 0:
                    areas.append(area_float)
            except (ValueError, TypeError):
                pass

        return {
            "quantidade_talhoes": total,
            "nomes_talhoes": nomes,
            "soma_areas": sum(areas) if areas else 0.0,
            "areas_individuais": areas,
        }

    def extract_farm_ids_from_fact_item(
        self, fact_item: Dict[str, Any], farm_property_name: str = "farm"
    ) -> List[str]:
        """Extract farm relation IDs from a parsed FACT item."""
        farm_ids = fact_item.get(farm_property_name, [])
        if not isinstance(farm_ids, list):
            farm_ids = [farm_ids] if farm_ids else []
        return farm_ids
