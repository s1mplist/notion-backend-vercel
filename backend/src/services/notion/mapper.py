from typing import Any

from models.report import Image, Plot
from utils.logging import get_logger


logger = get_logger(__name__)


class NotionDataMapper:
    @staticmethod
    def filter_properties(properties: dict[str, Any]) -> dict[str, Any]:
        """Return a new dict containing only Notion properties that have a meaningful value.

        This helps downstream mapping code ignore empty fields and simplifies templates.
        """
        if not properties:
            return {}

        def has_value(prop: dict[str, Any]) -> bool:
            if not prop:
                return False
            prop_type = prop.get("type") or ""
            val = (
                prop.get(prop_type)
                if isinstance(prop_type, str) and prop_type != ""
                else None
            )

            # Text-like properties (title, rich_text)
            if prop_type in ("title", "rich_text"):
                if not val:
                    return False
                # val is a list of rich text objects
                text = " ".join(item.get("text", {}).get("content", "") for item in val)
                return bool(text.strip())

            # Lists: multi_select, files, people, relation
            if prop_type in ("multi_select", "files", "people", "relation"):
                return bool(val and len(val) > 0)

            # Date
            if prop_type == "date":
                return bool(val and (val.get("start") or val.get("end")))

            # Number
            if prop_type == "number":
                return val is not None

            # Checkbox: consider only when True
            if prop_type == "checkbox":
                return val is True

            # Select-like and single-value fields
            if prop_type in (
                "select",
                "url",
                "email",
                "phone_number",
                "created_by",
                "last_edited_by",
                "rollup",
                "formula",
                "created_time",
                "last_edited_time",
            ):
                return bool(val)

            return bool(val)

        filtered: dict[str, Any] = {}
        for k, v in properties.items():
            try:
                if has_value(v):
                    filtered[k] = v
            except Exception:
                if v:
                    filtered[k] = v

        return filtered

    @staticmethod
    def extract_images(files: list[dict[str, Any]]) -> list[Image]:
        """Extract images from Notion's files property"""
        images = []
        for file in files:
            if file.get("type") == "file" or file.get("type") == "external":
                url = file.get("file", {}).get("url") or file.get("external", {}).get(
                    "url"
                )
                if url:
                    images.append(Image(url=url, description=file.get("name", "")))
        return images

    @classmethod
    def map_plot(cls, plot_data: dict[str, Any]) -> Plot:
        """Map Notion page data to Plot model"""
        return Plot(
            id=plot_data.get("id", ""),
            area=0.0,  # Area will be filled later if necessary
            growth_stage=plot_data.get("growth_stage", [""])[0]
            if plot_data.get("growth_stage")
            else "",
            crop=plot_data.get("name", [""])[0] if plot_data.get("name") else "",
            variety="",  # Variety will be filled in later if necessary
            images=[
                Image(url=img.get("url", ""), description="")
                for img in plot_data.get("images", [])
            ],
            additional_images=[],
            assessment=plot_data.get("assessment", [""])[0]
            if plot_data.get("assessment")
            else "",
        )
