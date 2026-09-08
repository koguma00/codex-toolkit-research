import httpx
import pytest

from ai_paper_search.connectors.official import OfficialProceedingsConnector
from ai_paper_search.registry import VenueSource, VenueSpec


class FakeFetcher:
    async def get(self, url):
        return httpx.Response(
            200,
            text=(
                '<html><a href="/v235/example24a.html">'
                "Collaborative Large Language Model Agents</a></html>"
            ),
            request=httpx.Request("GET", url),
        )


class AamasFakeFetcher:
    async def get(self, url):
        if url.endswith("contents.htm"):
            text = """
                <html>
                  <a name="FP"></a>
                  <a href="../pdfs/p001.pdf">LLM Multi-Agent Coordination</a>
                  <a name="EA"></a>
                  <a href="../pdfs/p002.pdf">Extended Abstract on LLM Agents</a>
                </html>
            """
        else:
            text = '<html><a href="forms/contents.htm">Contents</a></html>'
        return httpx.Response(200, text=text, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_official_html_parser_emits_acceptance_evidence():
    venue = VenueSpec(name="ICML", tier="core", track="main")
    source = VenueSource(
        url="https://proceedings.mlr.press/v235/",
        paper_link_pattern=r"/v235/.+\.html$",
    )
    papers, coverage = await OfficialProceedingsConnector(FakeFetcher()).enumerate(
        venue, 2024, source
    )
    assert coverage.status == "success"
    assert coverage.enumerated == 1
    assert papers[0].is_official
    assert papers[0].venue == "ICML"


@pytest.mark.asyncio
async def test_aamas_parser_keeps_full_papers_only():
    venue = VenueSpec(name="AAMAS", tier="mas", track="main")
    source = VenueSource(
        url="https://www.ifaamas.org/Proceedings/aamas2024/",
        follow_link_pattern=r"/aamas2024/forms/contents\.htm$",
        paper_link_pattern=r"/aamas2024/pdfs/p[0-9]+\.pdf$",
        accepted_section_pattern="FP",
    )
    papers, coverage = await OfficialProceedingsConnector(AamasFakeFetcher()).enumerate(
        venue, 2024, source
    )
    assert coverage.status == "success"
    assert [paper.title for paper in papers] == ["LLM Multi-Agent Coordination"]


def test_official_deduplication_uses_title_venue_and_year():
    from ai_paper_search.models import PaperVersion

    records = [
        PaperVersion(
            source="official:aaai",
            title="A Multi-Agent LLM System",
            url="https://example.test/article/1",
            year=2024,
            venue="AAAI",
            is_official=True,
        ),
        PaperVersion(
            source="official:aaai",
            title="A Multi Agent LLM System",
            url="https://example.test/article/1/pdf",
            year=2024,
            venue="AAAI",
            is_official=True,
        ),
    ]
    assert len(OfficialProceedingsConnector._dedupe(records)) == 1


@pytest.mark.asyncio
async def test_acl_fixed_case_spans_do_not_add_spaces():
    class AclFakeFetcher:
        async def get(self, url):
            return httpx.Response(
                200,
                text=(
                    '<a href="/2025.acl-long.1170/">'
                    '<span class="acl-fixed-case">A</span>gent'
                    '<span class="acl-fixed-case">D</span>ropout: '
                    'High-Performance <span class="acl-fixed-case">LLM</span>-Based '
                    "Multi-Agent Collaboration</a>"
                ),
                request=httpx.Request("GET", url),
            )

    venue = VenueSpec(name="ACL", tier="extension", track="main")
    source = VenueSource(
        url="https://aclanthology.org/events/acl-2025/",
        paper_link_pattern=r"/2025\.acl-long\.[0-9]+/$",
    )
    papers, _ = await OfficialProceedingsConnector(AclFakeFetcher()).enumerate(
        venue, 2025, source
    )
    assert papers[0].title == (
        "AgentDropout: High-Performance LLM-Based Multi-Agent Collaboration"
    )


@pytest.mark.asyncio
async def test_follow_link_text_filter_excludes_non_main_issues():
    class AaaiFakeFetcher:
        async def get(self, url):
            if url.endswith("/root"):
                text = (
                    '<a href="/issue/view/1">AAAI-25 Technical Tracks 1</a>'
                    '<a href="/issue/view/2">IAAI-25 and Demonstrations</a>'
                )
            elif url.endswith("/1"):
                text = (
                    '<a href="/index.php/AAAI/article/view/101">'
                    "Main Technical Track LLM Multi-Agent Paper</a>"
                )
            else:
                text = (
                    '<a href="/index.php/AAAI/article/view/202">'
                    "Demonstration LLM Multi-Agent Paper</a>"
                )
            return httpx.Response(200, text=text, request=httpx.Request("GET", url))

    venue = VenueSpec(name="AAAI", tier="core", track="main")
    source = VenueSource(
        url="https://example.test/root",
        follow_link_pattern=r"/issue/view/",
        follow_link_text_pattern=r"AAAI-[0-9]+ Technical Tracks",
        paper_link_pattern=r"/index\.php/AAAI/article/view/",
    )
    papers, _ = await OfficialProceedingsConnector(AaaiFakeFetcher()).enumerate(
        venue, 2025, source
    )
    assert [paper.title for paper in papers] == [
        "Main Technical Track LLM Multi-Agent Paper"
    ]


class VenueHtmlFetcher:
    def __init__(self, html: str) -> None:
        self.html = html

    async def get(self, url):
        return httpx.Response(200, text=self.html, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_pmlr_parser_reads_paper_container_metadata():
    html = """
        <div class="paper">
          <p class="title">First Complete ICML Paper</p>
          <span class="authors">Ada Lovelace, Alan Turing</span>
          <p class="links"><a href="/v235/first24a.html">abs</a></p>
        </div>
        <div class="paper">
          <p class="title">Second Complete ICML Paper</p>
          <span class="authors">Grace Hopper</span>
          <p class="links"><a href="/v235/second24a.html">abs</a></p>
        </div>
    """
    venue = VenueSpec(name="ICML", tier="core", track="main")
    source = VenueSource(
        url="https://proceedings.mlr.press/v235/",
        paper_link_pattern=r"/v235/.+\.html$",
        parser="pmlr",
        expected_count=2,
    )

    papers, coverage = await OfficialProceedingsConnector(
        VenueHtmlFetcher(html)
    ).enumerate(venue, 2024, source)

    assert coverage.status == "success"
    assert coverage.enumerated == 2
    assert [paper.title for paper in papers] == [
        "First Complete ICML Paper",
        "Second Complete ICML Paper",
    ]
    assert papers[0].authors == ["Ada Lovelace", "Alan Turing"]
    assert papers[0].url == "https://proceedings.mlr.press/v235/first24a.html"


@pytest.mark.asyncio
async def test_ijcai_parser_keeps_only_main_track_papers():
    html = """
        <div class="section">
          <div class="section_title"><h3>Main Track</h3></div>
          <div class="paper_wrapper">
            <div class="title">Main IJCAI Research Paper One</div>
            <div class="authors">Ada Lovelace, Alan Turing</div>
            <div class="details"><a href="/proceedings/2024/1">Details</a></div>
          </div>
          <div class="paper_wrapper">
            <div class="title">Main IJCAI Research Paper Two</div>
            <div class="authors">Grace Hopper</div>
            <div class="details"><a href="/proceedings/2024/2">Details</a></div>
          </div>
        </div>
        <div class="section">
          <div class="section_title"><h3>Demo Track</h3></div>
          <div class="paper_wrapper">
            <div class="title">Excluded IJCAI Demo Paper</div>
            <div class="authors">Demo Author</div>
            <div class="details"><a href="/proceedings/2024/3">Details</a></div>
          </div>
        </div>
    """
    venue = VenueSpec(name="IJCAI", tier="core", track="main")
    source = VenueSource(
        url="https://www.ijcai.org/proceedings/2024/",
        paper_link_pattern=r"/proceedings/2024/[0-9]+$",
        parser="ijcai",
        expected_count=2,
    )

    papers, coverage = await OfficialProceedingsConnector(
        VenueHtmlFetcher(html)
    ).enumerate(venue, 2024, source)

    assert coverage.status == "success"
    assert [paper.title for paper in papers] == [
        "Main IJCAI Research Paper One",
        "Main IJCAI Research Paper Two",
    ]
    assert all(paper.track == "main" for paper in papers)


@pytest.mark.asyncio
async def test_expected_count_mismatch_marks_coverage_partial():
    html = """
        <div class="paper">
          <p class="title">Only Parsed ICML Paper</p>
          <p class="links"><a href="/v235/only24a.html">abs</a></p>
        </div>
    """
    venue = VenueSpec(name="ICML", tier="core", track="main")
    source = VenueSource(
        url="https://proceedings.mlr.press/v235/",
        paper_link_pattern=r"/v235/.+\.html$",
        parser="pmlr",
        expected_count=2,
    )

    papers, coverage = await OfficialProceedingsConnector(
        VenueHtmlFetcher(html)
    ).enumerate(venue, 2024, source)

    assert len(papers) == 1
    assert coverage.status == "partial"
    assert "Expected 2 official records but parsed 1" in coverage.error
