from __future__ import annotations

from .models import SearchReport


def render_markdown(report: SearchReport) -> str:
    verified = sum(
        record.acceptance_status.startswith("verified") for record in report.records
    )
    lines = [
        "# AI Paper Search report",
        "",
        f"- Query: `{report.query}`",
        f"- Query variants: {', '.join(report.query_variants) or 'none'}",
        f"- Years: {', '.join(map(str, report.years))}",
        f"- Profile: {report.profile}",
        f"- Results: {len(report.records)} ({verified} formally verified)",
        f"- Searched at: {report.searched_at}",
        "",
        "## Papers",
        "",
    ]
    for index, record in enumerate(report.records, 1):
        venue = (
            f"{record.accepted_venue} {record.venue_year}"
            if record.accepted_venue
            else "arXiv-only / venue unverified"
        )
        lines.extend(
            [
                f"### {index}. {record.title}",
                "",
                f"- Status: **{record.acceptance_status}**",
                f"- Venue: {venue}",
                f"- Track: {record.track or 'n/a'}",
                f"- Citation version: {record.canonical_citation_url}",
                f"- Reading copy: {record.reading_copy_url}",
                f"- Acceptance evidence: {record.acceptance_evidence_url or 'none'}",
                f"- Versions linked: {len(record.versions)}",
                "",
            ]
        )

    lines.extend(
        [
            "## Coverage ledger",
            "",
            "| Venue | Year | Status | Enumerated | Direct matches | Official source |",
            "|---|---:|---|---:|---:|---|",
        ]
    )
    for item in report.coverage:
        lines.append(
            f"| {item.venue} | {item.year} | {item.status} | "
            f"{item.enumerated} | {item.directly_matched} | {item.official_source} |"
        )
    if report.limitations:
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {item}" for item in report.limitations)
    return "\n".join(lines) + "\n"
