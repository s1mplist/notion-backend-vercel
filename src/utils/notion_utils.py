import unicodedata
import re
from datetime import datetime
from typing import List, Dict, Any


def normalize_prop_name(name: str) -> str:
    """Normalize a Notion property name for robust matching.
    - Convert to lowercase
    - Remove diacritics (accents)
    - Replace non-alphanumeric characters with a single space
    - Collapse multiple spaces and strip
    """
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    s = no_accents.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_text(rich_text_list: List[Dict[str, Any]]) -> str:
    """Extract text from Notion's rich_text format"""
    if not rich_text_list:
        return ""
    return " ".join(text.get("text", {}).get("content", "") for text in rich_text_list)


def extract_date(date_obj: Dict[str, Any]) -> datetime:
    """Convert Notion date to datetime"""
    if not date_obj or "start" not in date_obj:
        return datetime.now()
    return datetime.fromisoformat(date_obj["start"].replace("Z", "+00:00"))
