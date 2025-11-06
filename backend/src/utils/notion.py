import codecs
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from utils.logging import get_logger


logger = get_logger(__name__)


class NotionUtils:
    """Helpers para extrair/normalizar propriedades do Notion de forma segura e testável."""

    def __init__(self) -> None:
        logger.info("NotionUtils initialized")

    # --------------------
    # Normalização de nomes
    # --------------------
    def normalize_prop_name(self, name: str) -> str:
        """Remove acentos, pontuação e normaliza espaços (lowercase)."""
        if not name:
            return ""
        nfkd = unicodedata.normalize("NFKD", name)
        no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
        s = no_accents.lower()
        # keep alnum and spaces only
        s = re.sub(r"[^a-z0-9\s]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def to_snake(self, name: str) -> str:
        """Converte um nome normalizado para snake_case (determinístico)."""
        n = self.normalize_prop_name(name)
        if not n:
            return ""
        s = re.sub(r"\s+", "_", n)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    def normalize_properties(self, props: Dict[str, Any]) -> Dict[str, Tuple[str, Any]]:
        """
        Retorna um dict snake_name -> (original_key, original_value).
        Primeiro encontro vence para evitar sobrescrita não determinística.
        """
        if not props:
            return {}
        norm: Dict[str, Tuple[str, Any]] = {}
        for orig_key, val in props.items():
            if not isinstance(orig_key, str):
                continue
            snake = self.to_snake(orig_key)
            if not snake:
                continue
            if snake not in norm:
                norm[snake] = (orig_key, val)
        return norm

    # --------------------
    # Busca por regex no nome normalizado
    # --------------------
    def find_property_by_regex(self, props: Dict[str, Any], pattern: str) -> Optional[Any]:
        """
        Pesquisa por propriedade usando regex aplicada ao snake_case normalizado.
        Retorna o valor da propriedade encontrada ou None.
        """
        if not props or not pattern:
            return None
        try:
            reg = re.compile(pattern, flags=re.IGNORECASE)
        except re.error:
            logger.warning("Regex inválido em find_property_by_regex: %s", pattern)
            return None

        norm = self.normalize_properties(props)
        # buscar por correspondência direta em snake names
        for snake, (orig, val) in norm.items():
            if reg.search(snake):
                return val
        # fallback: também testar normalize_prop_name sem underscores (mais permissivo)
        for orig_key, val in props.items():
            nk = self.normalize_prop_name(orig_key)
            if reg.search(nk):
                return val
        return None

    # --------------------
    # Extração de rich text / title / rollup
    # --------------------
    def plain_text(self, rich: List[Dict[str, Any]]) -> str:
        """Extrai plain_text de um array rich text"""
        if not rich:
            return ""
        parts: List[str] = []
        for seg in rich:
            if not isinstance(seg, dict):
                continue
            pt = seg.get("plain_text") or seg.get("text", {}).get("content") or ""
            if pt:
                parts.append(pt)
        #return self.decode_escapes("".join(parts))
        return "".join(parts)

    def extract_text(self, rich_text_list: List[Dict[str, Any]]) -> str:
        """Compatibilidade: extrai 'text' content"""
        if not rich_text_list:
            return ""
        raw = " ".join(
            (t.get("text", {}).get("content", "") if isinstance(t, dict) else "") for t in rich_text_list
        )
        #return self.decode_escapes(raw)
        return raw

    def extract_title(self, prop: Dict[str, Any]) -> str:
        return self.plain_text(prop.get("title") or [])

    def extract_rich_text(self, prop: Dict[str, Any]) -> str:
        return self.plain_text(prop.get("rich_text") or [])

    # --------------------
    # Outras extrações (files, relation, rollup, etc.)
    # --------------------
    def extract_relation_ids(self, prop: Dict[str, Any]) -> List[str]:
        rel = prop.get("relation") or []
        return [r.get("id", "").replace("-", "") for r in rel if r.get("id")]

    def extract_files(self, prop: Dict[str, Any]) -> List[str]:
        files: List[str] = []
        for f in prop.get("files") or []:
            if not isinstance(f, dict):
                continue
            if f.get("type") == "file":
                url = f.get("file", {}).get("url")
                if url:
                    files.append(url)
            elif f.get("type") == "external":
                url = f.get("external", {}).get("url")
                if url:
                    files.append(url)
        return files

    def extract_rollup(self, prop: Dict[str, Any]) -> Any:
        roll = prop.get("rollup") or {}
        rtype = roll.get("type")
        if rtype == "array":
            arr = roll.get("array") or []
            values: List[Any] = []
            for item in arr:
                if not isinstance(item, dict):
                    continue
                itype = item.get("type")
                if itype in ("rich_text", "title"):
                    values.append(self.plain_text(item.get(itype) or []))
                elif itype == "number":
                    values.append(item.get("number"))
                elif itype == "relation":
                    rels = item.get("relation") or []
                    values.extend([r.get("id", "").replace("-", "") for r in rels if r.get("id")])
                else:
                    # fallback: try coletar any plain_text presentes
                    for v in item.values():
                        if isinstance(v, list):
                            for seg in v:
                                if isinstance(seg, dict):
                                    pt = seg.get("plain_text")
                                    if pt:
                                        values.append(pt)
            if not values:
                return None
            return values[0] if len(values) == 1 else values
        for key in ("number", "date", "string", "boolean"):
            if key in roll:
                return roll.get(key)
        return None

    def simplify_property(self, prop: Dict[str, Any]) -> Any:
        """Mapeia tipos Notion para valores Python simples."""
        ptype = prop.get("type")
        if ptype == "rollup":
            return self.extract_rollup(prop)
        if ptype == "title":
            return self.extract_title(prop)
        if ptype == "rich_text":
            return self.extract_rich_text(prop)
        if ptype == "number":
            return prop.get("number")
        if ptype == "select":
            sel = prop.get("select")
            return sel.get("name") if sel else None
        if ptype == "multi_select":
            return [s.get("name") for s in (prop.get("multi_select") or []) if s.get("name") is not None]
        if ptype == "relation":
            return self.extract_relation_ids(prop)
        if ptype == "people":
            return [p.get("name") for p in (prop.get("people") or []) if p.get("name") is not None]
        if ptype == "date":
            return self.extract_date(prop)
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
            return self.extract_files(prop)
        logger.warning("Unknown Notion property type: %r in prop: %r", ptype, prop)
        return None

    # pequeno utilitário usado acima
    def extract_date(self, prop: Dict[str, Any]) -> Dict[str, Optional[str]]:
        d = prop.get("date") or {}
        return {"start": d.get("start"), "end": d.get("end")}
