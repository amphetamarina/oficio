import os
import re
import unicodedata
from datetime import datetime

DEFAULT_AGENT_MARKER = "@agent"
AUTO_ID_FALLBACK = "pedido"
ID_PATTERN = re.compile(r"\bid:([A-Za-z0-9_.:-]+)")


def agent_marker() -> str:
    """Marker that identifies a request line. Override via ``OFICIO_AGENT_MARKER``."""
    return os.environ.get("OFICIO_AGENT_MARKER", "").strip() or DEFAULT_AGENT_MARKER


def today_id_prefix() -> str:
    return datetime.now().strftime("%Y%m%d")


def auto_id(index: int) -> str:
    return f"{today_id_prefix()}-{index + 1}"


def find_max_auto_id(text: str) -> int:
    pattern = re.compile(rf"\bid:{today_id_prefix()}-(\d+)\b")
    return max((int(match.group(1)) for match in pattern.finditer(text)), default=0)


def slugify_request_id(text: str, *, fallback: str = AUTO_ID_FALLBACK) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    lowered = re.sub(r"\bid:[A-Za-z0-9_.:-]+\b", " ", lowered)
    lowered = lowered.replace(agent_marker(), " ")
    lowered = re.sub(r"^-\s*\[ \]\s*", " ", lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or fallback


def next_available_request_id(preferred_id: str, *texts: str) -> str:
    candidate = preferred_id.strip()
    if not candidate:
        raise ValueError("preferred_id is required")

    corpus = "\n".join(texts)
    if _id_is_available(candidate, corpus):
        return candidate
    return _next_suffixed_id(candidate, corpus)


def _id_is_available(request_id: str, corpus: str) -> bool:
    return f"## {request_id}" not in corpus and f"id:{request_id}" not in corpus


def _next_suffixed_id(candidate: str, corpus: str) -> str:
    suffix = 2
    while not _id_is_available(f"{candidate}-{suffix}", corpus):
        suffix += 1
    return f"{candidate}-{suffix}"
