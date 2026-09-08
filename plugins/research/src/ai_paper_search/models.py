from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PaperVersion(BaseModel):
    source: str
    title: str
    url: str
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    venue: str | None = None
    track: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    is_official: bool = False
    evidence_type: str = "index_metadata"


class PaperRecord(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    accepted_venue: str | None = None
    venue_year: int | None = None
    track: str | None = None
    acceptance_status: Literal[
        "verified_proceedings",
        "verified_accepted",
        "candidate_unverified",
        "preprint_only",
    ]
    acceptance_evidence_url: str | None = None
    canonical_citation_url: str
    reading_copy_url: str
    relevance_score: float = 0.0
    versions: list[PaperVersion] = Field(default_factory=list)


class CoverageEntry(BaseModel):
    venue: str
    year: int
    official_source: str
    status: Literal["success", "partial", "error"]
    enumerated: int = 0
    directly_matched: int = 0
    error: str | None = None


class SearchReport(BaseModel):
    query: str
    query_variants: list[str] = Field(default_factory=list)
    years: list[int]
    searched_at: str
    profile: str
    records: list[PaperRecord]
    coverage: list[CoverageEntry]
    source_counts: dict[str, int]
    limitations: list[str] = Field(default_factory=list)


class BibtexResult(BaseModel):
    status: Literal["success", "unavailable"]
    format: Literal["bibtex"] = "bibtex"
    title: str
    canonical_citation_url: str
    bibtex: str | None = None
    source_type: Literal[
        "official_bibtex",
        "doi_content_negotiation",
        "none",
    ] = "none"
    source_url: str | None = None
    unavailable_reason: str | None = None
