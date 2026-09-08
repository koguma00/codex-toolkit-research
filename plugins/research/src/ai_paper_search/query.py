from __future__ import annotations

import re
from dataclasses import dataclass


STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "or",
    "paper",
    "papers",
    "search",
    "system",
    "systems",
    "the",
    "to",
    "using",
    "with",
}


@dataclass(frozen=True)
class QueryPlan:
    original: str
    concept_groups: tuple[tuple[str, ...], ...]
    broad_terms: tuple[str, ...]
    external_queries: tuple[str, ...]
    use_nlp_extension: bool


def plan_queries(
    query: str, query_variants: list[str] | None = None, max_variants: int = 5
) -> tuple[QueryPlan, ...]:
    """Build de-duplicated plans for one intent without unbounded query fan-out."""
    primary = query.strip()
    if not primary:
        raise ValueError("query must not be empty")
    variants: list[str] = []
    seen = {_normal(primary)}
    for raw in query_variants or []:
        variant = raw.strip()
        normalized = _normal(variant)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        variants.append(variant)
    if len(variants) > max_variants:
        raise ValueError(
            f"query_variants supports at most {max_variants} unique entries"
        )
    return tuple(plan_query(item) for item in [primary, *variants])


def _normal(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def plan_query(query: str) -> QueryPlan:
    normalized = _normal(query)
    groups: list[tuple[str, ...]] = []
    external = [query]

    llm_signal = bool(re.search(r"\bllms?\b|large language model", normalized))
    mas_signal = bool(
        re.search(r"multi agent|multiagent|agent collaboration|agentic", normalized)
    )

    if llm_signal:
        groups.append(("large language model", "large language models", "llm", "llms"))
    if mas_signal:
        groups.append(
            (
                "multi agent",
                "multiagent",
                "multiple agents",
                "agent collaboration",
                "collaborative agents",
                "language model agents",
                "agent society",
            )
        )
    if llm_signal and mas_signal:
        external = [
            '"large language model" "multi-agent"',
            '"large language model" "multi agent system"',
            'LLM "multi-agent collaboration"',
            '"language model agents" collaboration',
        ]

    broad_terms = tuple(
        token
        for token in normalized.split()
        if len(token) > 2 and token not in STOPWORDS
    )
    if not groups:
        groups = [(term,) for term in broad_terms[:4]]

    return QueryPlan(
        original=query,
        concept_groups=tuple(groups),
        broad_terms=broad_terms,
        external_queries=tuple(dict.fromkeys(external)),
        use_nlp_extension=llm_signal,
    )


def relevance_score(title: str, abstract: str | None, plan: QueryPlan) -> float:
    title_norm = _normal(title)
    text = f"{title_norm} {_normal(abstract or '')}"
    if not text:
        return 0.0

    group_hits = [any(term in text for term in group) for group in plan.concept_groups]
    title_group_hits = [
        any(term in title_norm for term in group) for group in plan.concept_groups
    ]
    broad_hits = sum(term in text for term in plan.broad_terms)
    broad_denominator = max(1, len(plan.broad_terms))

    score = 0.55 * (sum(group_hits) / max(1, len(group_hits)))
    score += 0.25 * (sum(title_group_hits) / max(1, len(title_group_hits)))
    score += 0.20 * (broad_hits / broad_denominator)
    return round(min(score, 1.0), 4)


def is_relevant(title: str, abstract: str | None, plan: QueryPlan) -> bool:
    score = relevance_score(title, abstract, plan)
    if len(plan.concept_groups) >= 2:
        text = _normal(f"{title} {abstract or ''}")
        return all(any(term in text for term in group) for group in plan.concept_groups)
    return score >= 0.45
