from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .connectors import (
    ArxivConnector,
    DblpConnector,
    OfficialProceedingsConnector,
    OpenAlexConnector,
    SemanticScholarConnector,
)
from .connectors.topic import run_topic_connectors
from .http import Fetcher
from .models import PaperVersion, SearchReport
from .query import is_relevant, plan_queries
from .registry import VenueRegistry
from .resolver import resolve_records


class SearchEngine:
    def __init__(self, registry: VenueRegistry | None = None) -> None:
        self.registry = registry or VenueRegistry.load()

    async def search(
        self,
        query: str,
        years: list[int] | None = None,
        profile: str = "auto",
        max_results: int = 50,
        query_variants: list[str] | None = None,
    ) -> SearchReport:
        years = sorted(set(years or [2023, 2024, 2025]))
        plans = plan_queries(query, query_variants)
        include_nlp = profile in {"all", "nlp"} or (
            profile == "auto" and any(plan.use_nlp_extension for plan in plans)
        )
        fetcher = Fetcher()
        try:
            official_connector = OfficialProceedingsConnector(fetcher)
            selected = self.registry.selected(years, include_nlp=include_nlp)
            official_results = await asyncio.gather(
                *(
                    official_connector.enumerate(venue, year, source)
                    for venue, year, source in selected
                )
            )
            official_catalog = [
                paper for papers, _coverage in official_results for paper in papers
            ]
            coverage = [entry for _papers, entry in official_results]
            for entry, (papers, _ignored) in zip(
                coverage, official_results, strict=True
            ):
                entry.directly_matched = sum(
                    any(
                        is_relevant(paper.title, paper.abstract, plan) for plan in plans
                    )
                    for paper in papers
                )

            topic_connectors = [
                ArxivConnector(fetcher),
                OpenAlexConnector(fetcher),
                DblpConnector(fetcher),
                SemanticScholarConnector(fetcher),
            ]
            topic_versions: list[PaperVersion] = []
            topic_counts: dict[str, int] = {}
            topic_errors: list[str] = []
            for plan in plans:
                versions, _counts, errors = await run_topic_connectors(
                    topic_connectors, plan, years
                )
                topic_versions.extend(versions)
                topic_errors.extend(
                    f"query={plan.original!r}: {error}" for error in errors
                )
            topic_versions = list(
                {
                    (version.source, version.url): version for version in topic_versions
                }.values()
            )
            for version in topic_versions:
                topic_counts[version.source] = topic_counts.get(version.source, 0) + 1
            records = resolve_records(topic_versions, official_catalog, plans)

            official_counts: dict[str, int] = {}
            for paper in official_catalog:
                official_counts[paper.source] = official_counts.get(paper.source, 0) + 1
            source_counts = {**official_counts, **topic_counts}
            limitations = topic_errors
            limitations.extend(
                f"{entry.venue} {entry.year}: {entry.error}"
                for entry in coverage
                if entry.status != "success" and entry.error
            )
            limitations.append(
                "Live scholarly indexes and proceedings pages can change; retain this report as the search snapshot."
            )
            if len(plans) > 1:
                limitations.append(
                    "Query variants expand candidate recall but require final semantic screening against the user's inclusion criteria."
                )
            return SearchReport(
                query=query,
                query_variants=[plan.original for plan in plans[1:]],
                years=years,
                searched_at=datetime.now(timezone.utc).isoformat(),
                profile="nlp" if include_nlp else "core-mas",
                records=records[:max_results],
                coverage=coverage,
                source_counts=source_counts,
                limitations=limitations,
            )
        finally:
            await fetcher.close()
