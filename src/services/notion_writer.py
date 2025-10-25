import json
import os
from typing import Optional
from datetime import datetime, date
import uuid as _uuid
from notion_client import AsyncClient

from src.models.generation import GenerationMetadata


class NotionWriter:
    @staticmethod
    def _json_default(o):
        # Handle common non-serializable types
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, _uuid.UUID):
            return str(o)
        return str(o)

    @staticmethod
    def _to_json_text(obj: dict) -> str:
        try:
            return json.dumps(
                obj, ensure_ascii=False, indent=2, default=NotionWriter._json_default
            )
        except Exception:
            # Fallback to simple string representation
            return str(obj)

    @staticmethod
    async def _get_title_property_name(notion: AsyncClient, database_id: str) -> str:
        """Detect the title property name for a Notion database.

        Falls back to "Name" if detection fails.
        """
        try:
            db = await notion.databases.retrieve(database_id=database_id)
            props = db.get("properties", {}) or {}
            for name, schema in props.items():
                if schema.get("type") == "title":
                    return name
        except Exception:
            pass
        return "Name"

    @staticmethod
    def _build_children_blocks(
        payload: dict, metadata: GenerationMetadata, pdf_url: Optional[str]
    ):
        payload_json = NotionWriter._to_json_text(payload)
        metadata_json = metadata.model_dump_json(indent=2)

        blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Dados do Webhook"}}
                    ]
                },
            },
            {
                "object": "block",
                "type": "code",
                "code": {
                    "language": "json",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": payload_json[:1900]},
                        }
                    ],
                },
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Metadata de Geração"}}
                    ]
                },
            },
            {
                "object": "block",
                "type": "code",
                "code": {
                    "language": "json",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": metadata_json[:1900]},
                        }
                    ],
                },
            },
        ]

        if pdf_url:
            blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "PDF"}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "file",
                        "file": {
                            "type": "external",
                            "external": {"url": pdf_url},
                            "caption": [
                                {
                                    "type": "text",
                                    "text": {"content": "Relatório em PDF"},
                                }
                            ],
                        },
                    },
                ]
            )

        return blocks

    @staticmethod
    async def create_generation_record(
        database_id: str,
        title: str,
        payload: dict,
        metadata: GenerationMetadata,
        pdf_url: Optional[str] = None,
        additional_fields: Optional[dict] = None,
    ) -> str:
        """Create a page record in the target Notion database to log a generation.

        Returns the created page id.
        """
        async with AsyncClient(auth=os.environ["NOTION_TOKEN"]) as notion:
            db = await notion.databases.retrieve(database_id=database_id)
            db_props = db.get("properties", {}) or {}

            # Fallback: if properties are empty, fetch from data_sources
            if not db_props:
                try:
                    data_sources = db.get("data_sources") or []
                    if data_sources:
                        ds_id = data_sources[0].get("id")
                        if ds_id:
                            ds = await notion.data_sources.retrieve(ds_id)
                            db_props = ds.get("properties", {}) or {}
                except Exception:
                    pass

            # Detect title property robustly
            title_prop = None
            for name, schema in db_props.items():
                try:
                    if isinstance(schema, dict) and schema.get("type") == "title":
                        title_prop = name
                        break
                except Exception:
                    continue

            # Common localized fallbacks if not found yet
            if not title_prop:
                for candidate in ("Name", "Título", "Title", "Nome"):
                    if candidate in db_props:
                        # Only accept if the schema type is actually 'title'
                        try:
                            if db_props.get(candidate, {}).get("type") == "title":
                                title_prop = candidate
                                break
                        except Exception:
                            pass

            if not title_prop:
                # As a last resort, try to pick the first property with type 'title' by inspecting values
                for name, schema in db_props.items():
                    try:
                        if schema.get("type") == "title":
                            title_prop = name
                            break
                    except Exception:
                        continue

            if not title_prop:
                raise ValueError(
                    f"Could not detect the database title property. Properties available: {list(db_props.keys())}"
                )

            # Base properties with title
            properties = {
                title_prop: {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title[:200] or "Relatório"},
                        }
                    ]
                }
            }

            # Helper: add property if present in DB schema
            def add_prop(prop_name: str, value_builder):
                schema = db_props.get(prop_name)
                if not schema:
                    return
                try:
                    built = value_builder(schema)
                    if built is not None:
                        properties[prop_name] = built
                except Exception:
                    pass

            # Optional structured props
            # First, map to your Data Source (snake_case) names if they exist
            start_iso = (
                metadata.generation_started_at.isoformat()
                if metadata.generation_started_at
                else None
            )
            end_iso = (
                metadata.generation_completed_at.isoformat()
                if metadata.generation_completed_at
                else None
            )
            add_prop(
                "generation_status",
                lambda s: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": (metadata.generation_status or "")[:2000]
                            },
                        }
                    ]
                }
                if s.get("type") == "rich_text" and metadata.generation_status
                else None,
            )
            add_prop(
                "generation_error",
                lambda s: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": str(metadata.generation_error)[:2000]},
                        }
                    ]
                }
                if s.get("type") == "rich_text" and metadata.generation_error
                else None,
            )
            add_prop(
                "entity_id",
                lambda s: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": str(metadata.entity_id)[:2000]},
                        }
                    ]
                }
                if s.get("type") == "rich_text" and metadata.entity_id
                else None,
            )
            add_prop(
                "webhook_timestamp",
                lambda s: {"date": {"start": metadata.webhook_timestamp.isoformat()}}
                if s.get("type") == "date" and metadata.webhook_timestamp
                else None,
            )
            add_prop(
                "generation_started_at",
                lambda s: {"date": {"start": start_iso}}
                if s.get("type") == "date" and start_iso
                else None,
            )
            add_prop(
                "generation_completed_at",
                lambda s: {"date": {"start": end_iso}}
                if s.get("type") == "date" and end_iso
                else None,
            )

            # Then, also support friendly names if the schema has them
            add_prop(
                "Status",
                lambda s: {
                    "select": {"name": (metadata.generation_status or "unknown")[:100]}
                }
                if s.get("type") == "select" and metadata.generation_status
                else None,
            )

            # PDF URL (url)
            add_prop(
                "PDF",
                lambda s: {"url": pdf_url}
                if s.get("type") == "url" and pdf_url
                else None,
            )

            add_prop(
                "Started At",
                lambda s: {"date": {"start": start_iso}}
                if s.get("type") == "date" and start_iso
                else None,
            )
            add_prop(
                "Completed At",
                lambda s: {"date": {"start": end_iso}}
                if s.get("type") == "date" and end_iso
                else None,
            )

            # Duration seconds (number)
            duration_s = None
            if metadata.generation_started_at and metadata.generation_completed_at:
                try:
                    duration_s = (
                        metadata.generation_completed_at
                        - metadata.generation_started_at
                    ).total_seconds()
                except Exception:
                    duration_s = None
            add_prop(
                "Duration (s)",
                lambda s: {"number": float(duration_s)}
                if s.get("type") == "number" and duration_s is not None
                else None,
            )

            # Error (rich_text)
            add_prop(
                "Error",
                lambda s: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": str(metadata.generation_error)[:2000]},
                        }
                    ]
                }
                if s.get("type") == "rich_text" and metadata.generation_error
                else None,
            )

            # Additional fields (e.g., Farm/Fazenda)
            if additional_fields:
                for k, v in additional_fields.items():
                    if v is None:
                        continue

                    def builder(schema, val=v):
                        t = schema.get("type")
                        if t == "rich_text":
                            return {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": str(val)[:2000]},
                                    }
                                ]
                            }
                        if t == "url":
                            return {"url": str(val)}
                        if t == "number":
                            try:
                                return {"number": float(val)}
                            except Exception:
                                return None
                        if t == "date":
                            try:
                                if isinstance(val, (datetime, date)):
                                    return {"date": {"start": val.isoformat()}}
                            except Exception:
                                return None
                        if t == "select":
                            return {"select": {"name": str(val)[:100]}}
                        # For unsupported types we skip
                        return None

                    add_prop(k, builder)

            page = await notion.pages.create(
                parent={"type": "database_id", "database_id": database_id},
                properties=properties,
                children=NotionWriter._build_children_blocks(
                    payload, metadata, pdf_url
                ),
            )
            return page.get("id")
