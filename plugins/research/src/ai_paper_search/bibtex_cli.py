from __future__ import annotations

import argparse
import asyncio
import json

from .bibtex import BibtexResolver


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retrieve title-validated BibTeX from a paper's canonical source."
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--canonical-url", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=[
            "verified_proceedings",
            "verified_accepted",
            "candidate_unverified",
            "preprint_only",
        ],
    )
    parser.add_argument("--doi")
    parser.add_argument("--year", type=int)
    parser.add_argument("--format", choices=["bibtex", "json"], default="bibtex")
    return parser


async def _run(args: argparse.Namespace) -> str:
    resolver = BibtexResolver()
    try:
        result = await resolver.resolve(
            title=args.title,
            canonical_citation_url=args.canonical_url,
            acceptance_status=args.status,
            doi=args.doi,
            year=args.year,
        )
    finally:
        await resolver.close()
    if args.format == "json":
        output = json.dumps(
            result.model_dump(mode="json"), indent=2, ensure_ascii=False
        )
        return f"{output}\n"
    if result.status == "success":
        return f"{result.bibtex}\n"
    return f"BibTeX unavailable: {result.unavailable_reason}\n"


def main() -> None:
    args = _parser().parse_args()
    output = asyncio.run(_run(args))
    print(output, end="")


if __name__ == "__main__":
    main()
