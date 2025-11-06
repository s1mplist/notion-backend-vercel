import functools
from datetime import date, datetime

from notion_client import AsyncClient

from config import get_settings
from models.generation import GenerationMetadata
from utils.json import to_json_string
from utils.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)


class NotionWriter:
    """Service for writing data to Notion databases."""

    @staticmethod
    def _build_children_blocks(
        payload: dict,
        metadata: GenerationMetadata,
        pdf_url: str | None,
        preview_url: str | None = None,
    ):
        payload_json = to_json_string(payload)
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

        if preview_url:
            blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Pré-visualização (HTML)"},
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "bookmark",
                        "bookmark": {"url": preview_url},
                    },
                ]
            )

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
        pdf_url: str | None = None,
        preview_url: str | None = None,
        additional_fields: dict | None = None,
        notion: AsyncClient | None = None,
    ) -> str:
        """Create a page record in the target Notion database to log a generation.

        Returns the created page id.
        """
        close_client = False
        if notion is None:
            notion = AsyncClient(auth=settings.notion_token)
            close_client = True
        try:
            db = await notion.databases.retrieve(database_id=database_id)
            db_props = db.get("properties", {}) or {}

            # Fallback: if properties are empty, fetch from data_sources
            try:
                data_sources = db.get("data_sources") or []
                if data_sources:
                    ds_id = data_sources[0].get("id")
                    if ds_id:
                        ds = await notion.data_sources.retrieve(ds_id)
                        db_props = ds.get("properties", {}) or {}
            except (KeyError, AttributeError) as e:
                logger.warning(f"Error retrieving data source properties: {e}")
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
                        except Exception as e:
                            logger.warning(
                                f"Error checking title property for candidate '{candidate}': {e}"
                            )
                            pass

                for name, schema in db_props.items():
                    try:
                        if schema.get("type") == "title":
                            title_prop = name
                            break
                    except Exception as e:
                        logger.exception(
                            f"Exception while inspecting property '{name}' for type 'title': {e}"
                        )
                        continue
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
                            "text": {"content": title[:200] if title else "Relatório"},
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
                except Exception as e:
                    logger.exception(f"Error building property '{prop_name}': {e}")
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

            # Preview URL (url)
            add_prop(
                "Preview",
                lambda s: {"url": preview_url}
                if s.get("type") == "url" and preview_url
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
            duration_s = None
            if metadata.generation_started_at and metadata.generation_completed_at:
                try:
                    duration_s = (
                        metadata.generation_completed_at
                        - metadata.generation_started_at
                    )
                except Exception as e:
                    logger.exception(f"Error calculating duration: {e}")
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
            def builder(schema, val):
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
                if t == "number":
                    try:
                        return {"number": float(val)}
                    except (ValueError, TypeError) as e:
                        logger.exception(
                            f"Error converting value '{val}' to float for property: {e}"
                        )
                        return None
                if t == "date":
                    try:
                        if isinstance(val, (datetime, date)):
                            return {"date": {"start": val.isoformat()}}
                    except Exception as e:
                        logger.exception(
                            f"Error converting value '{val}' to date property: {e}"
                        )
                        return None
                    except Exception:
                        return None
                if t == "select":
                    return {"select": {"name": str(val)[:100]}}
                # For unsupported types we skip
                return None

            if additional_fields:
                for k, v in additional_fields.items():
                    if v is None:
                        continue
                    add_prop(k, functools.partial(builder, val=v))
            page = await notion.pages.create(
                parent={"type": "database_id", "database_id": database_id},
                properties=properties,
                children=NotionWriter._build_children_blocks(
                    payload, metadata, pdf_url, preview_url
                ),
            )
            return page.get("id")
        except Exception as e:
            logger.exception(f"Error creating generation record in Notion: {e}")
            raise
        finally:
            if close_client:
                await notion.aclose()
            if close_client:
                await notion.aclose()
