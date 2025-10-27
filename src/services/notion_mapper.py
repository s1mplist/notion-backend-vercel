from datetime import datetime
from typing import Dict, Any, List
from models.report import Report, Plot, Image
from utils.notion_utils import extract_text


class NotionDataMapper:
    @staticmethod
    def filter_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
        """Return a new dict containing only Notion properties that have a meaningful value.

        This helps downstream mapping code ignore empty fields and simplifies templates.
        """
        if not properties:
            return {}

        def has_value(prop: Dict[str, Any]) -> bool:
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
                return bool(val) is True

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

            # Fallback: consider truthiness
            return bool(val)

        filtered: Dict[str, Any] = {}
        for k, v in properties.items():
            try:
                if has_value(v):
                    filtered[k] = v
            except Exception:
                # If unknown structure, keep conservative: include if non-empty
                if v:
                    filtered[k] = v

        return filtered

    @staticmethod
    def extract_images(files: List[Dict[str, Any]]) -> List[Image]:
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

    # normalize_prop_name, extract_text, extract_date agora estão em src.utils.notion_utils

    @classmethod
    def map_plot(cls, plot_data: Dict[str, Any]) -> Plot:
        """Map Notion page data to Plot model"""
        return Plot(
            id=plot_data.get("id", ""),
            area=0.0,  # Área será preenchida posteriormente se necessário
            growth_stage=plot_data.get("growth_stage", [""])[0]
            if plot_data.get("growth_stage")
            else "",
            crop=plot_data.get("name", [""])[0] if plot_data.get("name") else "",
            variety="",  # Variedade será preenchida posteriormente se necessário
            images=[
                Image(url=img.get("url", ""), description="")
                for img in plot_data.get("images", [])
            ],
            additional_images="",
            assessment=plot_data.get("assessment", [""])[0]
            if plot_data.get("assessment")
            else "",
        )

    @classmethod
    def map_to_report(
        cls, notion_data: Dict[str, Any], plots_data: List[Dict[str, Any]]
    ) -> Report:
        """Map Notion data to Report model (ignore empty fields)"""
        props = notion_data.get("properties", {})

        # Extrair textos das propriedades rich_text
        informacoes = extract_text(
            props.get("Informações Gerais", {}).get("rich_text", [])
        )
        cronograma = extract_text(
            props.get("Cronograma de Operações da Fazenda", {}).get("rich_text", [])
        )

        # Extrair datas
        data_visita = extract_text(props.get("Data da Visita", {}).get("rich_text", []))
        data_retorno = extract_text(
            props.get("Data de Retorno (Prevista)", {}).get("rich_text", [])
        )

        # Converter strings de data para objetos datetime
        try:
            current_visit_date = datetime.strptime(data_visita, "%d/%m/%Y")
        except (ValueError, TypeError):
            current_visit_date = datetime.now()

        try:
            next_visit_date = datetime.strptime(data_retorno, "%d/%m/%Y")
        except (ValueError, TypeError):
            next_visit_date = datetime.now()

        # Mapear plots
        mapped_plots = [
            cls.map_plot(plot)
            for plot in (plots_data if isinstance(plots_data, list) else [])
        ]

        return Report(
            farm_name="",  # Será preenchido posteriormente
            consultant_name="",  # Será preenchido posteriormente
            report_month=datetime.now().strftime("%B %Y"),
            owner_name="",  # Será preenchido posteriormente
            farm_city="",  # Será preenchido posteriormente
            harvest_period="2025/2026",  # Valor padrão ou será preenchido posteriormente
            general_info=informacoes,
            next_visit_date=next_visit_date,
            current_visit_date=current_visit_date,
            operations_schedule=cronograma,
            plots=mapped_plots,
        )
