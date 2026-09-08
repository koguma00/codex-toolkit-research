from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .models import PaperRecord, PaperVersion
from .normalization import normalize_title, title_similarity
from .query import QueryPlan, is_relevant, relevance_score


KNOWN_VENUE_TOKENS = (
    "neurips",
    "neural information processing systems",
    "icml",
    "international conference on machine learning",
    "iclr",
    "aaai",
    "ijcai",
    "aamas",
    "acl",
    "emnlp",
)


def _title_tokens(title: str) -> set[str]:
    return {token for token in normalize_title(title).split() if len(token) > 3}


def _best_official(
    candidate: PaperVersion,
    official_by_title: dict[str, list[PaperVersion]],
    official_token_index: dict[tuple[int | None, str], list[PaperVersion]],
) -> PaperVersion | None:
    normalized = normalize_title(candidate.title)
    exact = official_by_title.get(normalized)
    if exact:
        return sorted(exact, key=lambda item: item.track == "findings")[0]

    candidate_tokens = _title_tokens(candidate.title)
    narrowed: dict[str, PaperVersion] = {}
    for token in candidate_tokens:
        for official in official_token_index.get((candidate.year, token), []):
            narrowed.setdefault(official.url, official)

    best: PaperVersion | None = None
    best_score = 0.0
    for official in narrowed.values():
        official_normalized = normalize_title(official.title)
        if abs(len(official_normalized) - len(normalized)) > 25:
            continue
        official_tokens = _title_tokens(official.title)
        union = candidate_tokens | official_tokens
        if not union or len(candidate_tokens & official_tokens) / len(union) < 0.45:
            continue
        score = title_similarity(candidate.title, official.title)
        if score > best_score:
            best, best_score = official, score
    return best if best_score >= 0.92 else None


def _dedupe_versions(versions: list[PaperVersion]) -> list[PaperVersion]:
    unique: dict[tuple[str, str], PaperVersion] = {}
    for version in versions:
        unique.setdefault((version.source, version.url), version)
    return list(unique.values())


def resolve_records(
    topic_versions: list[PaperVersion],
    official_catalog: list[PaperVersion],
    plans: QueryPlan | Sequence[QueryPlan],
) -> list[PaperRecord]:
    active_plans = (plans,) if isinstance(plans, QueryPlan) else tuple(plans)
    if not active_plans:
        raise ValueError("at least one query plan is required")

    def relevant(version: PaperVersion) -> bool:
        return any(
            is_relevant(version.title, version.abstract, plan) for plan in active_plans
        )

    official_by_title: dict[str, list[PaperVersion]] = defaultdict(list)
    official_token_index: dict[tuple[int | None, str], list[PaperVersion]] = (
        defaultdict(list)
    )
    for official in official_catalog:
        official_by_title[normalize_title(official.title)].append(official)
        for token in _title_tokens(official.title):
            official_token_index[(official.year, token)].append(official)

    clusters: dict[str, list[PaperVersion]] = defaultdict(list)
    directly_relevant_official = [
        record for record in official_catalog if relevant(record)
    ]
    for official in directly_relevant_official:
        clusters[normalize_title(official.title)].append(official)

    for candidate in topic_versions:
        if not relevant(candidate):
            continue
        official = _best_official(candidate, official_by_title, official_token_index)
        key = normalize_title(official.title if official else candidate.title)
        clusters[key].append(candidate)
        if official:
            clusters[key].append(official)

    records: list[PaperRecord] = []
    for versions in clusters.values():
        versions = _dedupe_versions(versions)
        official = sorted(
            (item for item in versions if item.is_official),
            key=lambda item: (item.track == "findings", -(item.year or 0)),
        )
        arxiv = [item for item in versions if item.source == "arxiv"]
        representative = official[0] if official else versions[0]
        abstract_version = next((item for item in versions if item.abstract), None)
        author_version = max(versions, key=lambda item: len(item.authors))
        score = max(
            relevance_score(item.title, item.abstract, plan)
            for item in versions
            for plan in active_plans
        )

        if official:
            evidence = official[0]
            status = (
                "verified_accepted"
                if evidence.evidence_type.startswith("official_accepted_record")
                else "verified_proceedings"
            )
            accepted_venue = evidence.venue
            venue_year = evidence.year
            track = evidence.track
            evidence_url = evidence.url
            canonical_url = evidence.url
        else:
            claimed = next(
                (
                    item
                    for item in versions
                    if item.venue
                    and item.venue.lower() != "arxiv"
                    and any(token in item.venue.lower() for token in KNOWN_VENUE_TOKENS)
                ),
                None,
            )
            status = "candidate_unverified" if claimed else "preprint_only"
            accepted_venue = claimed.venue if claimed else None
            venue_year = claimed.year if claimed else None
            track = None
            evidence_url = None
            canonical_url = (
                f"https://doi.org/{claimed.doi.removeprefix('https://doi.org/')}"
                if claimed and claimed.doi
                else representative.url
            )

        reading_copy = arxiv[0].url if arxiv else representative.url
        records.append(
            PaperRecord(
                title=representative.title,
                authors=author_version.authors,
                year=representative.year,
                abstract=abstract_version.abstract if abstract_version else None,
                accepted_venue=accepted_venue,
                venue_year=venue_year,
                track=track,
                acceptance_status=status,
                acceptance_evidence_url=evidence_url,
                canonical_citation_url=canonical_url,
                reading_copy_url=reading_copy,
                relevance_score=score,
                versions=versions,
            )
        )

    status_order = {
        "verified_proceedings": 0,
        "verified_accepted": 1,
        "candidate_unverified": 2,
        "preprint_only": 3,
    }
    return sorted(
        records,
        key=lambda item: (
            status_order[item.acceptance_status],
            item.track == "findings",
            -item.relevance_score,
            -(item.year or 0),
            item.title.lower(),
        ),
    )
