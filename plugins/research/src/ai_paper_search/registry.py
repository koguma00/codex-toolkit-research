from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class VenueSource(BaseModel):
    url: str
    paper_link_pattern: str
    parser: Literal["generic", "pmlr", "ijcai"] = "generic"
    expected_count: int | None = None
    follow_link_pattern: str | None = None
    follow_link_text_pattern: str | None = None
    accepted_section_pattern: str | None = None
    source_type: Literal["html", "openreview"] = "html"


class VenueSpec(BaseModel):
    name: str
    tier: Literal["core", "mas", "extension", "secondary"]
    track: str
    years: dict[int, list[VenueSource]] = Field(default_factory=dict)


class VenueRegistry(BaseModel):
    venues: list[VenueSpec]

    @classmethod
    def load(cls, path: Path | None = None) -> "VenueRegistry":
        if path is None:
            path = Path(__file__).with_name("venue_registry.yaml")
        return cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

    def selected(
        self, years: list[int], include_nlp: bool
    ) -> list[tuple[VenueSpec, int, VenueSource]]:
        selected: list[tuple[VenueSpec, int, VenueSource]] = []
        for venue in self.venues:
            if venue.tier in {"extension", "secondary"} and not include_nlp:
                continue
            for year in years:
                for source in venue.years.get(year, []):
                    selected.append((venue, year, source))
        return selected
