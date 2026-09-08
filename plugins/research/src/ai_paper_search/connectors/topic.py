from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from ..http import Fetcher
from ..models import PaperVersion
from ..normalization import normalize_title
from ..query import QueryPlan


ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"(\d{4})", value)
    return int(match.group(1)) if match else None


def _dedupe(records: list[PaperVersion]) -> list[PaperVersion]:
    unique: dict[tuple[str, str], PaperVersion] = {}
    for record in records:
        unique.setdefault((normalize_title(record.title), record.url), record)
    return list(unique.values())


class ArxivConnector:
    name = "arxiv"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def search(
        self, plan: QueryPlan, years: list[int], max_results: int = 50
    ) -> list[PaperVersion]:
        query = (
            'all:"large language model" AND '
            '(all:"multi-agent" OR all:"multi agent" OR all:"multiple agents")'
            if plan.use_nlp_extension and len(plan.concept_groups) >= 2
            else f'all:"{plan.original}"'
        )
        params = {
            "search_query": query,
            "start": 0,
            "max_results": min(max_results, 50),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        response = await self.fetcher.get(
            f"https://export.arxiv.org/api/query?{urlencode(params)}"
        )
        root = ET.fromstring(response.content)
        records: list[PaperVersion] = []
        for entry in root.findall("atom:entry", ATOM):
            title = " ".join((entry.findtext("atom:title", "", ATOM)).split())
            abstract = " ".join((entry.findtext("atom:summary", "", ATOM)).split())
            published = entry.findtext("atom:published", "", ATOM)
            year = _year_from_date(published)
            if year not in years:
                continue
            entry_url = entry.findtext("atom:id", "", ATOM)
            arxiv_id = entry_url.rsplit("/", 1)[-1]
            authors = [
                item.findtext("atom:name", "", ATOM)
                for item in entry.findall("atom:author", ATOM)
            ]
            journal_ref = entry.findtext("arxiv:journal_ref", None, ATOM)
            doi = entry.findtext("arxiv:doi", None, ATOM)
            records.append(
                PaperVersion(
                    source="arxiv",
                    title=title,
                    url=entry_url,
                    year=year,
                    authors=authors,
                    abstract=abstract,
                    venue=journal_ref or "arXiv",
                    doi=doi,
                    arxiv_id=arxiv_id,
                    evidence_type="author_preprint_metadata",
                )
            )
        return _dedupe(records)


class OpenAlexConnector:
    name = "openalex"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    @staticmethod
    def _abstract(index: dict[str, list[int]] | None) -> str | None:
        if not index:
            return None
        positions = sorted((pos, word) for word, values in index.items() for pos in values)
        return " ".join(word for _, word in positions)

    async def search(
        self, plan: QueryPlan, years: list[int], max_results: int = 100
    ) -> list[PaperVersion]:
        params = {
            "search": plan.original,
            "filter": (
                f"from_publication_date:{min(years)}-01-01,"
                f"to_publication_date:{max(years)}-12-31"
            ),
            "per-page": min(max_results, 100),
            "select": (
                "id,doi,title,display_name,publication_year,authorships,"
                "primary_location,locations,abstract_inverted_index"
            ),
        }
        response = await self.fetcher.get(
            f"https://api.openalex.org/works?{urlencode(params)}"
        )
        records: list[PaperVersion] = []
        for item in response.json().get("results", []):
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            url = location.get("landing_page_url") or item.get("doi") or item.get("id")
            if not url:
                continue
            authors = [
                authorship.get("author", {}).get("display_name", "")
                for authorship in item.get("authorships", [])
                if authorship.get("author", {}).get("display_name")
            ]
            records.append(
                PaperVersion(
                    source="openalex",
                    title=item.get("display_name") or item.get("title") or "",
                    url=url,
                    year=item.get("publication_year"),
                    authors=authors,
                    abstract=self._abstract(item.get("abstract_inverted_index")),
                    venue=source.get("display_name"),
                    doi=item.get("doi"),
                    evidence_type="index_metadata",
                )
            )
        return _dedupe([record for record in records if record.title])


class DblpConnector:
    name = "dblp"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def search(
        self, plan: QueryPlan, years: list[int], max_results: int = 100
    ) -> list[PaperVersion]:
        params = {"q": plan.original, "format": "json", "h": min(max_results, 100)}
        response = await self.fetcher.get(
            f"https://dblp.org/search/publ/api?{urlencode(params)}"
        )
        hits = response.json().get("result", {}).get("hits", {}).get("hit", [])
        records: list[PaperVersion] = []
        for hit in hits:
            info = hit.get("info", {})
            try:
                year = int(info.get("year")) if info.get("year") else None
            except ValueError:
                year = None
            if year not in years:
                continue
            author_data = info.get("authors", {}).get("author", [])
            if isinstance(author_data, dict):
                author_data = [author_data]
            authors = [
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in author_data
            ]
            url = info.get("ee") or info.get("url")
            if isinstance(url, list):
                url = url[0]
            if not url:
                continue
            records.append(
                PaperVersion(
                    source="dblp",
                    title=re.sub(r"<[^>]+>", "", info.get("title", "")).rstrip("."),
                    url=url,
                    year=year,
                    authors=authors,
                    venue=info.get("venue"),
                    doi=info.get("doi"),
                    evidence_type="bibliographic_index",
                )
            )
        return _dedupe([record for record in records if record.title])


class SemanticScholarConnector:
    name = "semantic_scholar"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def search(
        self, plan: QueryPlan, years: list[int], max_results: int = 50
    ) -> list[PaperVersion]:
        fields = "title,authors,abstract,year,venue,url,externalIds,openAccessPdf"
        params = {
            "query": plan.original,
            "limit": min(max_results, 100),
            "fields": fields,
            "year": f"{min(years)}-{max(years)}",
        }
        response = await self.fetcher.get(
            f"https://api.semanticscholar.org/graph/v1/paper/search?{urlencode(params)}"
        )
        records: list[PaperVersion] = []
        for item in response.json().get("data", []):
            external = item.get("externalIds") or {}
            open_pdf = item.get("openAccessPdf") or {}
            url = item.get("url") or open_pdf.get("url")
            if not url:
                continue
            records.append(
                PaperVersion(
                    source="semantic_scholar",
                    title=item.get("title", ""),
                    url=url,
                    year=item.get("year"),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    abstract=item.get("abstract"),
                    venue=item.get("venue"),
                    doi=external.get("DOI"),
                    arxiv_id=external.get("ArXiv"),
                    evidence_type="bibliographic_index",
                )
            )
        return _dedupe([record for record in records if record.title])


async def run_topic_connectors(
    connectors: list, plan: QueryPlan, years: list[int]
) -> tuple[list[PaperVersion], dict[str, int], list[str]]:
    results = await asyncio.gather(
        *(connector.search(plan, years) for connector in connectors),
        return_exceptions=True,
    )
    records: list[PaperVersion] = []
    counts: dict[str, int] = {}
    errors: list[str] = []
    for connector, result in zip(connectors, results, strict=True):
        if isinstance(result, Exception):
            counts[connector.name] = 0
            errors.append(f"{connector.name}: {type(result).__name__}: {result}")
            continue
        counts[connector.name] = len(result)
        records.extend(result)
    return _dedupe(records), counts, errors
