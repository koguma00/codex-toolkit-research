from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .bibtex import BibtexResolver
from .search import SearchEngine


mcp = FastMCP("ai-paper-search")


@mcp.tool()
async def search_ai_papers(
    query: str,
    years: list[int] | None = None,
    profile: str = "auto",
    max_results: int = 50,
    query_variants: list[str] | None = None,
) -> dict:
    """Search official venues with optional meaning-preserving query variants."""
    report = await SearchEngine().search(
        query=query,
        years=years,
        profile=profile,
        max_results=max_results,
        query_variants=query_variants,
    )
    return report.model_dump(mode="json")


@mcp.tool()
async def get_paper_bibtex(
    title: str,
    canonical_citation_url: str,
    acceptance_status: str,
    doi: str | None = None,
    year: int | None = None,
) -> dict:
    """Retrieve source-provided BibTeX and reject title/version mismatches."""
    resolver = BibtexResolver()
    try:
        result = await resolver.resolve(
            title=title,
            canonical_citation_url=canonical_citation_url,
            acceptance_status=acceptance_status,
            doi=doi,
            year=year,
        )
    finally:
        await resolver.close()
    return result.model_dump(mode="json")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
