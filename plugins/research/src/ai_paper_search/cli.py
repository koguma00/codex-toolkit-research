from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .render import render_markdown
from .search import SearchEngine


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Venue-first discovery of verified AI conference papers."
    )
    parser.add_argument("query")
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument(
        "--profile", choices=["auto", "core", "nlp", "all"], default="auto"
    )
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument(
        "--query-variant",
        action="append",
        default=[],
        help="Meaning-preserving alternate query; repeat up to five times.",
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path)
    return parser


async def _run(args: argparse.Namespace) -> str:
    report = await SearchEngine().search(
        args.query,
        years=args.years,
        profile=args.profile,
        max_results=args.max_results,
        query_variants=args.query_variant,
    )
    if args.format == "json":
        return (
            json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n"
        )
    return render_markdown(report)


def main() -> None:
    args = _parser().parse_args()
    output = asyncio.run(_run(args))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise SystemExit(f"Refusing to overwrite retained artifact: {args.output}")
        args.output.write_text(output, encoding="utf-8")
        print(args.output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
