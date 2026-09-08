import argparse
import json
from urllib.parse import urlparse

import httpx
import pytest

from ai_paper_search.bibtex import (
    BibtexResolver,
    _ALLOWED_CANONICAL_HOSTS,
    _validated_entry,
)
from ai_paper_search.bibtex_cli import _run
from ai_paper_search.registry import VenueRegistry


TITLE = "Collaborative Large Language Model Agents"
BIBTEX = """@inproceedings{smith2025collaborative,
  title = {{Collaborative Large Language Model Agents}},
  author = {Smith, Ada and Doe, Jin},
  booktitle = {Proceedings of the Test Conference},
  year = {2025}
}"""


class FakeFetcher:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return httpx.Response(
            200,
            text=value,
            request=httpx.Request("GET", url),
        )


@pytest.mark.asyncio
async def test_acl_uses_official_bib_file_before_landing_page():
    canonical = "https://aclanthology.org/2025.acl-long.1170/"
    bib_url = "https://aclanthology.org/2025.acl-long.1170.bib"
    fetcher = FakeFetcher({bib_url: BIBTEX})

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url=canonical,
        acceptance_status="verified_proceedings",
        year=2025,
    )

    assert result.status == "success"
    assert result.source_type == "official_bibtex"
    assert result.source_url == bib_url
    assert result.canonical_citation_url == canonical
    assert [call[0] for call in fetcher.calls] == [bib_url]


@pytest.mark.asyncio
async def test_embedded_official_bibtex_is_returned_exactly():
    canonical = "https://proceedings.mlr.press/v267/example25a.html"
    html = f"<html><pre>{BIBTEX}</pre></html>"
    fetcher = FakeFetcher({canonical: html})

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url=canonical,
        acceptance_status="verified_proceedings",
        year=2025,
    )

    assert result.status == "success"
    assert result.bibtex == BIBTEX
    assert result.source_url == canonical


@pytest.mark.asyncio
async def test_embedded_bibtex_decodes_html_entities():
    canonical = "https://proceedings.mlr.press/v267/example25a.html"
    encoded = BIBTEX.replace("Smith, Ada and Doe, Jin", "Smith, Ada &amp; Doe, Jin")
    fetcher = FakeFetcher({canonical: f"<html><pre>{encoded}</pre></html>"})

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url=canonical,
        acceptance_status="verified_proceedings",
        year=2025,
    )

    assert result.status == "success"
    assert "Smith, Ada & Doe, Jin" in result.bibtex
    assert "&amp;" not in result.bibtex


@pytest.mark.asyncio
async def test_official_page_doi_uses_content_negotiation():
    canonical = "https://ojs.aaai.org/index.php/AAAI/article/view/12345"
    doi_url = "https://doi.org/10.1609/aaai.v39i1.12345"
    fetcher = FakeFetcher(
        {
            canonical: (
                '<html><meta name="citation_doi" '
                'content="10.1609/aaai.v39i1.12345"></html>'
            ),
            doi_url: BIBTEX,
        }
    )

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url=canonical,
        acceptance_status="verified_proceedings",
        year=2025,
    )

    assert result.status == "success"
    assert result.source_type == "doi_content_negotiation"
    assert result.source_url == doi_url
    assert fetcher.calls[-1][1]["headers"] == {"Accept": "application/x-bibtex"}


@pytest.mark.asyncio
async def test_title_mismatch_is_unavailable_without_arxiv_substitution():
    canonical = "https://proceedings.neurips.cc/paper/2025/hash/example.html"
    wrong = BIBTEX.replace(TITLE, "A Different Paper")
    fetcher = FakeFetcher({canonical: f"<pre>{wrong}</pre>"})

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url=canonical,
        acceptance_status="verified_proceedings",
        year=2025,
    )

    assert result.status == "unavailable"
    assert result.bibtex is None
    assert "Refusing to fabricate" in result.unavailable_reason


@pytest.mark.asyncio
async def test_preprint_only_is_delegated_to_authoritative_arxiv_export():
    fetcher = FakeFetcher({})

    result = await BibtexResolver(fetcher).resolve(
        title=TITLE,
        canonical_citation_url="https://arxiv.org/abs/2501.00001",
        acceptance_status="preprint_only",
        year=2025,
    )

    assert result.status == "unavailable"
    assert "export_citations" in result.unavailable_reason
    assert fetcher.calls == []


@pytest.mark.asyncio
async def test_unavailable_json_is_a_normal_result():
    output = await _run(
        argparse.Namespace(
            title=TITLE,
            canonical_url="https://arxiv.org/abs/2501.00001",
            status="preprint_only",
            doi=None,
            year=2025,
            format="json",
        )
    )

    payload = json.loads(output)
    assert payload["status"] == "unavailable"
    assert payload["bibtex"] is None
    assert "export_citations" in payload["unavailable_reason"]


def test_bibtex_validation_handles_protective_title_braces():
    assert _validated_entry(BIBTEX, TITLE, 2025) == BIBTEX
    assert _validated_entry(BIBTEX, TITLE, 2024) is None


def test_bibtex_validation_selects_matching_entry_from_multiple_entries():
    wrong = BIBTEX.replace(TITLE, "A Different Paper")
    assert _validated_entry(f"{wrong}\n\n{BIBTEX}", TITLE, 2025) == BIBTEX


def test_all_registered_official_hosts_are_allowlisted():
    registry = VenueRegistry.load()
    hosts = {
        urlparse(source.url).hostname
        for venue in registry.venues
        for sources in venue.years.values()
        for source in sources
    }
    assert hosts <= _ALLOWED_CANONICAL_HOSTS
