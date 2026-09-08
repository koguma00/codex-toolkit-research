from __future__ import annotations

import asyncio
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http import Fetcher
from ..models import CoverageEntry, PaperVersion
from ..normalization import normalize_title
from ..registry import VenueSource, VenueSpec


GENERIC_LABELS = {
    "abstract",
    "article",
    "full paper",
    "html",
    "paper",
    "pdf",
    "view",
}


def _openreview_value(value):
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _visible_text(element) -> str:
    return " ".join("".join(element.strings).split())


def _split_authors(element) -> list[str]:
    if element is None:
        return []
    return [part.strip() for part in _visible_text(element).split(",") if part.strip()]


def _direct_section_title(section) -> str:
    title_container = section.find("div", class_="section_title", recursive=False)
    if title_container is None:
        return ""
    heading = title_container.find(["h2", "h3", "h4"], recursive=False)
    return _visible_text(heading if heading is not None else title_container)


class OfficialProceedingsConnector:
    def __init__(self, fetcher: Fetcher, concurrency: int = 4) -> None:
        self.fetcher = fetcher
        self.semaphore = asyncio.Semaphore(concurrency)

    async def enumerate(
        self, venue: VenueSpec, year: int, source: VenueSource
    ) -> tuple[list[PaperVersion], CoverageEntry]:
        coverage = CoverageEntry(
            venue=venue.name,
            year=year,
            official_source=source.url,
            status="success",
        )
        try:
            async with self.semaphore:
                if source.source_type == "openreview":
                    papers = await self._openreview(venue, year, source)
                else:
                    papers = await self._html(venue, year, source)
            coverage.enumerated = len(papers)
            if not papers:
                coverage.status = "partial"
                coverage.error = "Official page returned no parseable paper records."
            elif (
                source.expected_count is not None
                and len(papers) != source.expected_count
            ):
                coverage.status = "partial"
                coverage.error = (
                    f"Expected {source.expected_count} official records but parsed "
                    f"{len(papers)}. Proceedings completeness is unverified."
                )
            return papers, coverage
        except Exception as exc:  # coverage must survive individual source failures
            coverage.status = "error"
            coverage.error = f"{type(exc).__name__}: {exc}"
            return [], coverage

    async def _openreview(
        self, venue: VenueSpec, year: int, source: VenueSource
    ) -> list[PaperVersion]:
        records: list[PaperVersion] = []
        offset = 0
        expected: int | None = None
        while expected is None or offset < expected:
            separator = "&" if "?" in source.url else "?"
            response = await self.fetcher.get(f"{source.url}{separator}offset={offset}")
            payload = response.json()
            notes = payload.get("notes", [])
            expected = int(payload.get("count", len(notes)))
            if not notes:
                break
            for note in notes:
                content = note.get("content", {})
                title = _openreview_value(content.get("title")) or ""
                authors = _openreview_value(content.get("authors")) or []
                venue_id = _openreview_value(content.get("venueid")) or venue.name
                note_id = note.get("forum") or note.get("id")
                if not title or not note_id:
                    continue
                records.append(
                    PaperVersion(
                        source="openreview",
                        title=str(title).strip(),
                        url=f"https://openreview.net/forum?id={note_id}",
                        year=year,
                        authors=[str(a) for a in authors],
                        venue=venue.name,
                        track=venue.track,
                        is_official=True,
                        evidence_type=f"official_accepted_record:{venue_id}",
                    )
                )
            offset += len(notes)
            if len(notes) < 1 or offset >= 5000:
                break
        return self._dedupe(records)

    async def _html(
        self, venue: VenueSpec, year: int, source: VenueSource
    ) -> list[PaperVersion]:
        response = await self.fetcher.get(source.url)
        pages = [(str(response.url), response.text)]
        if source.follow_link_pattern:
            soup = BeautifulSoup(response.text, "html.parser")
            follow_urls = {
                urljoin(str(response.url), anchor.get("href", ""))
                for anchor in soup.find_all("a", href=True)
                if re.search(
                    source.follow_link_pattern,
                    urljoin(str(response.url), anchor.get("href", "")),
                    re.I,
                )
                and (
                    source.follow_link_text_pattern is None
                    or re.search(
                        source.follow_link_text_pattern, _visible_text(anchor), re.I
                    )
                )
            }
            fetched = await asyncio.gather(
                *(self.fetcher.get(url) for url in sorted(follow_urls)),
                return_exceptions=True,
            )
            pages.extend(
                (str(item.url), item.text)
                for item in fetched
                if not isinstance(item, Exception)
            )

        if source.parser == "pmlr":
            return self._pmlr(pages, venue, year, source)
        if source.parser == "ijcai":
            return self._ijcai(pages, venue, year, source)

        records: list[PaperVersion] = []
        pattern = re.compile(source.paper_link_pattern, re.I)
        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                absolute = urljoin(page_url, anchor["href"])
                parsed_target = urlparse(absolute)
                match_surface = parsed_target.path
                if not pattern.search(match_surface):
                    continue
                if source.accepted_section_pattern:
                    marker = anchor.find_previous("a", attrs={"name": True})
                    marker_name = marker.get("name", "") if marker is not None else ""
                    if not re.fullmatch(source.accepted_section_pattern, marker_name):
                        continue
                title = _visible_text(anchor)
                if title.lower() in GENERIC_LABELS or len(title) < 12:
                    heading = anchor.find_previous(["h2", "h3", "h4", "h5", "strong"])
                    if heading is not None:
                        title = _visible_text(heading)
                if len(title) < 8:
                    continue
                records.append(
                    PaperVersion(
                        source=f"official:{venue.name.lower().replace(' ', '-')}",
                        title=title,
                        url=absolute,
                        year=year,
                        venue=venue.name,
                        track=venue.track,
                        is_official=True,
                        evidence_type="official_proceedings",
                    )
                )
        return self._dedupe(records)

    def _pmlr(
        self,
        pages: list[tuple[str, str]],
        venue: VenueSpec,
        year: int,
        source: VenueSource,
    ) -> list[PaperVersion]:
        records: list[PaperVersion] = []
        pattern = re.compile(source.paper_link_pattern, re.I)
        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for paper in soup.select("div.paper"):
                title_node = paper.select_one(".title")
                authors_node = paper.select_one(".authors")
                link = next(
                    (
                        anchor
                        for anchor in paper.find_all("a", href=True)
                        if pattern.search(
                            urlparse(urljoin(page_url, anchor["href"])).path
                        )
                    ),
                    None,
                )
                if title_node is None or link is None:
                    continue
                title = _visible_text(title_node)
                if len(title) < 8:
                    continue
                records.append(
                    self._paper_version(
                        venue,
                        year,
                        title,
                        urljoin(page_url, link["href"]),
                        _split_authors(authors_node),
                    )
                )
        return self._dedupe(records)

    def _ijcai(
        self,
        pages: list[tuple[str, str]],
        venue: VenueSpec,
        year: int,
        source: VenueSource,
    ) -> list[PaperVersion]:
        records: list[PaperVersion] = []
        pattern = re.compile(source.paper_link_pattern, re.I)
        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            main_section = next(
                (
                    section
                    for section in soup.find_all("div", class_="section")
                    if _direct_section_title(section) == "Main Track"
                ),
                None,
            )
            if main_section is None:
                continue
            for paper in main_section.select("div.paper_wrapper"):
                title_node = paper.select_one(".title")
                authors_node = paper.select_one(".authors")
                link = next(
                    (
                        anchor
                        for anchor in paper.find_all("a", href=True)
                        if pattern.search(
                            urlparse(urljoin(page_url, anchor["href"])).path
                        )
                    ),
                    None,
                )
                if title_node is None or link is None:
                    continue
                title = _visible_text(title_node)
                if len(title) < 8:
                    continue
                records.append(
                    self._paper_version(
                        venue,
                        year,
                        title,
                        urljoin(page_url, link["href"]),
                        _split_authors(authors_node),
                    )
                )
        return self._dedupe(records)

    @staticmethod
    def _paper_version(
        venue: VenueSpec,
        year: int,
        title: str,
        url: str,
        authors: list[str],
    ) -> PaperVersion:
        return PaperVersion(
            source=f"official:{venue.name.lower().replace(' ', '-')}",
            title=title,
            url=url,
            year=year,
            authors=authors,
            venue=venue.name,
            track=venue.track,
            is_official=True,
            evidence_type="official_proceedings",
        )

    @staticmethod
    def _dedupe(records: list[PaperVersion]) -> list[PaperVersion]:
        unique: dict[tuple[str, str, str], PaperVersion] = {}
        for record in records:
            key = (normalize_title(record.title), record.venue or "", str(record.year))
            unique.setdefault(key, record)
        return list(unique.values())
