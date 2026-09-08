from __future__ import annotations

import re
from collections.abc import Iterator
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http import Fetcher
from .models import BibtexResult
from .normalization import title_similarity


_BIBTEX_ENTRY = re.compile(
    r"@(?!comment\b|string\b|preamble\b)[a-zA-Z]+\s*([({])",
    re.IGNORECASE,
)
_DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_ALLOWED_CANONICAL_HOSTS = {
    "aclanthology.org",
    "www.aclanthology.org",
    "openreview.net",
    "iclr.cc",
    "www.iclr.cc",
    "proceedings.iclr.cc",
    "proceedings.mlr.press",
    "proceedings.neurips.cc",
    "ojs.aaai.org",
    "aaai.org",
    "www.aaai.org",
    "ijcai.org",
    "www.ijcai.org",
    "ifaamas.org",
    "www.ifaamas.org",
    "doi.org",
    "dx.doi.org",
}
_DOI_META_NAMES = {
    "citation_doi",
    "dc.identifier",
    "dc.identifier.doi",
    "bepress_citation_doi",
}


def _first_bibtex_entry(text: str) -> str | None:
    match = _BIBTEX_ENTRY.search(text)
    if match is None:
        return None
    opening = match.group(1)
    closing = "}" if opening == "{" else ")"
    depth = 1
    escaped = False
    quoted = False
    for index in range(match.end(), len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1].strip()
    return None


def _bibtex_entries(text: str) -> Iterator[str]:
    offset = 0
    while offset < len(text):
        remaining = text[offset:]
        entry = _first_bibtex_entry(remaining)
        if entry is None:
            return
        relative_start = remaining.find(entry)
        yield entry
        offset += relative_start + len(entry)


def _bibtex_field(entry: str, field: str) -> str | None:
    match = re.search(rf"\b{re.escape(field)}\s*=\s*", entry, re.IGNORECASE)
    if match is None:
        return None
    index = match.end()
    if index >= len(entry):
        return None
    opening = entry[index]
    if opening not in {"{", '"'}:
        end = entry.find(",", index)
        return entry[index : end if end >= 0 else len(entry)].strip()
    closing = "}" if opening == "{" else '"'
    depth = 1
    escaped = False
    for cursor in range(index + 1, len(entry)):
        char = entry[cursor]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if opening == "{" and char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return entry[index + 1 : cursor].strip()
    return None


def _plain_latex(value: str) -> str:
    value = re.sub(r"\\(?:textsc|textit|textbf|emph|mathrm|mathbf)\s*", "", value)
    value = re.sub(r"\\[a-zA-Z]+\*?", "", value)
    return value.replace("{", "").replace("}", "").replace("~", " ")


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    candidate = re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
        "",
        value.strip(),
        flags=re.IGNORECASE,
    )
    candidate = candidate.strip().rstrip(".,;)")
    return candidate if _DOI.fullmatch(candidate) else None


def _validated_entry(
    text: str, expected_title: str, expected_year: int | None
) -> str | None:
    for entry in _bibtex_entries(text):
        actual_title = _bibtex_field(entry, "title")
        if actual_title is None:
            continue
        if title_similarity(_plain_latex(actual_title), expected_title) < 0.9:
            continue
        if expected_year is not None:
            actual_year = _bibtex_field(entry, "year")
            if actual_year and actual_year.strip() != str(expected_year):
                continue
        return entry
    return None


def _citation_links(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        label = " ".join(anchor.stripped_strings)
        if not re.search(
            r"bibtex|\.bib(?:$|[?#])|citation[^/]*bib", f"{label} {href}", re.I
        ):
            continue
        candidate = urljoin(page_url, href)
        parsed = urlparse(candidate)
        if (
            parsed.scheme in {"http", "https"}
            and parsed.hostname in _ALLOWED_CANONICAL_HOSTS
        ):
            links.append(candidate)
    return list(dict.fromkeys(links))[:5]


def _embedded_bibtex(
    html: str, expected_title: str, expected_year: int | None
) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select("pre, code, textarea"):
        entry = _validated_entry(element.get_text(), expected_title, expected_year)
        if entry:
            return entry
    return _validated_entry(soup.get_text("\n"), expected_title, expected_year)


def _metadata_doi(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for meta in soup.find_all("meta"):
        name = str(meta.get("name") or meta.get("property") or "").lower()
        if name not in _DOI_META_NAMES:
            continue
        doi = _normalize_doi(str(meta.get("content") or ""))
        if doi:
            return doi
    for anchor in soup.find_all("a", href=True):
        parsed = urlparse(urljoin("https://example.invalid", str(anchor["href"])))
        if parsed.hostname in {"doi.org", "dx.doi.org"}:
            doi = _normalize_doi(parsed.path.lstrip("/"))
            if doi:
                return doi
    return None


def _acl_bibtex_url(canonical_url: str) -> str | None:
    parsed = urlparse(canonical_url)
    if parsed.hostname not in {"aclanthology.org", "www.aclanthology.org"}:
        return None
    path = parsed.path.rstrip("/")
    if path.endswith((".bib", ".pdf", ".xml")):
        path = path.rsplit(".", 1)[0]
    return f"https://aclanthology.org{path}.bib"


class BibtexResolver:
    """Retrieve source-provided BibTeX and fail closed on version mismatches."""

    def __init__(self, fetcher: Fetcher | None = None) -> None:
        self.fetcher = fetcher or Fetcher()
        self._owns_fetcher = fetcher is None

    async def close(self) -> None:
        if self._owns_fetcher:
            await self.fetcher.close()

    async def _from_url(
        self,
        url: str,
        title: str,
        year: int | None,
        source_type: str,
    ) -> BibtexResult | None:
        try:
            response = await self.fetcher.get(url)
        except Exception:
            return None
        entry = _validated_entry(response.text, title, year)
        if entry is None:
            return None
        return BibtexResult(
            status="success",
            title=title,
            canonical_citation_url=url,
            bibtex=entry,
            source_type=source_type,
            source_url=url,
        )

    async def _from_doi(
        self,
        doi: str,
        title: str,
        year: int | None,
        canonical_url: str,
    ) -> BibtexResult | None:
        source_url = f"https://doi.org/{doi}"
        try:
            response = await self.fetcher.get(
                source_url,
                headers={"Accept": "application/x-bibtex"},
            )
        except Exception:
            return None
        entry = _validated_entry(response.text, title, year)
        if entry is None:
            return None
        return BibtexResult(
            status="success",
            title=title,
            canonical_citation_url=canonical_url,
            bibtex=entry,
            source_type="doi_content_negotiation",
            source_url=source_url,
        )

    async def resolve(
        self,
        *,
        title: str,
        canonical_citation_url: str,
        acceptance_status: str,
        doi: str | None = None,
        year: int | None = None,
    ) -> BibtexResult:
        if acceptance_status == "preprint_only":
            return BibtexResult(
                status="unavailable",
                title=title,
                canonical_citation_url=canonical_citation_url,
                unavailable_reason=(
                    "Preprint-only records must use the bundled arXiv MCP "
                    "export_citations tool with the verified arXiv ID."
                ),
            )

        parsed = urlparse(canonical_citation_url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in _ALLOWED_CANONICAL_HOSTS
        ):
            return BibtexResult(
                status="unavailable",
                title=title,
                canonical_citation_url=canonical_citation_url,
                unavailable_reason="Canonical URL is not an allowlisted official proceedings or DOI host.",
            )

        normalized_doi = _normalize_doi(doi)
        if parsed.hostname in {"doi.org", "dx.doi.org"}:
            normalized_doi = normalized_doi or _normalize_doi(parsed.path.lstrip("/"))

        direct_acl = _acl_bibtex_url(canonical_citation_url)
        if direct_acl:
            result = await self._from_url(direct_acl, title, year, "official_bibtex")
            if result:
                result.canonical_citation_url = canonical_citation_url
                return result

        page_html: str | None = None
        if parsed.hostname not in {"doi.org", "dx.doi.org"}:
            try:
                page = await self.fetcher.get(canonical_citation_url)
                page_html = page.text
            except Exception:
                page_html = None

        if page_html:
            embedded = _embedded_bibtex(page_html, title, year)
            if embedded:
                return BibtexResult(
                    status="success",
                    title=title,
                    canonical_citation_url=canonical_citation_url,
                    bibtex=embedded,
                    source_type="official_bibtex",
                    source_url=canonical_citation_url,
                )
            for citation_url in _citation_links(canonical_citation_url, page_html):
                result = await self._from_url(
                    citation_url, title, year, "official_bibtex"
                )
                if result:
                    result.canonical_citation_url = canonical_citation_url
                    return result
            normalized_doi = normalized_doi or _metadata_doi(page_html)

        if normalized_doi:
            result = await self._from_doi(
                normalized_doi, title, year, canonical_citation_url
            )
            if result:
                return result

        return BibtexResult(
            status="unavailable",
            title=title,
            canonical_citation_url=canonical_citation_url,
            unavailable_reason=(
                "No title-matched BibTeX was retrievable from the official page "
                "or DOI metadata. Refusing to fabricate fields or substitute an "
                "arXiv citation for a published version."
            ),
        )
