from ai_paper_search.models import PaperVersion
from ai_paper_search.query import plan_query
from ai_paper_search.resolver import resolve_records


def version(**overrides):
    data = {
        "source": "arxiv",
        "title": "Collaborative Large Language Model Agents",
        "url": "https://arxiv.org/abs/2401.00001",
        "year": 2024,
        "abstract": "A multi-agent system based on LLMs.",
        "venue": "arXiv",
        "arxiv_id": "2401.00001",
    }
    data.update(overrides)
    return PaperVersion(**data)


def test_official_proceedings_beats_arxiv_but_reading_copy_survives():
    official = version(
        source="official:neurips",
        url="https://proceedings.neurips.cc/paper_files/paper/2024/hash/x-Abstract-Conference.html",
        venue="NeurIPS",
        track="main",
        is_official=True,
        evidence_type="official_proceedings",
        abstract=None,
        arxiv_id=None,
    )
    record = resolve_records(
        [version()], [official], plan_query("llm multi agent system")
    )[0]
    assert record.acceptance_status == "verified_proceedings"
    assert record.accepted_venue == "NeurIPS"
    assert record.canonical_citation_url.startswith("https://proceedings.neurips.cc")
    assert record.reading_copy_url == "https://arxiv.org/abs/2401.00001"
    assert len(record.versions) == 2


def test_arxiv_only_is_never_promoted_to_accepted():
    record = resolve_records([version()], [], plan_query("llm multi agent system"))[0]
    assert record.acceptance_status == "preprint_only"
    assert record.acceptance_evidence_url is None


def test_findings_is_labeled_secondary():
    findings = version(
        source="official:acl-findings",
        url="https://aclanthology.org/2024.findings-acl.1/",
        venue="ACL Findings",
        track="findings",
        is_official=True,
        evidence_type="official_proceedings",
        abstract=None,
        arxiv_id=None,
    )
    record = resolve_records(
        [version()], [findings], plan_query("llm multi agent system")
    )[0]
    assert record.accepted_venue == "ACL Findings"
    assert record.track == "findings"


def test_query_variant_recovers_semantically_named_official_paper():
    candidate = version(
        source="openalex",
        title="Emergent Societies of Generative Agents",
        url="https://openalex.org/W123",
        abstract="We study collective decision making in agent societies.",
        venue="NeurIPS",
        arxiv_id=None,
    )
    official = candidate.model_copy(
        update={
            "source": "official:neurips",
            "url": "https://proceedings.neurips.cc/paper/2024/hash/x.html",
            "is_official": True,
            "evidence_type": "official_proceedings",
            "abstract": None,
        }
    )

    records = resolve_records(
        [candidate],
        [official],
        [
            plan_query("llm multi agent system"),
            plan_query("collective decision making generative agent societies"),
        ],
    )

    assert len(records) == 1
    assert records[0].acceptance_status == "verified_proceedings"
    assert records[0].title == "Emergent Societies of Generative Agents"
