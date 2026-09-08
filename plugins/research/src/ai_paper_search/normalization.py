from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_title(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(arxiv|preprint|proceedings version)\b", " ", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def title_similarity(left: str, right: str) -> float:
    a, b = normalize_title(left), normalize_title(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()
