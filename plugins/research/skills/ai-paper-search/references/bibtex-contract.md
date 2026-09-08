# BibTeX contract

## Canonical-version rule

BibTeX must describe the version selected by the version graph:

- formally published paper: official proceedings or publisher record;
- accepted record without proceedings: official accepted-record citation;
- DOI-backed unverified candidate: DOI registration metadata, still labeled
  unverified for acceptance;
- arXiv-only preprint: authoritative arXiv metadata and `@misc`.

Never substitute an arXiv `@misc` entry when a verified proceedings version is
the canonical citation. The arXiv URL remains a reading copy only.

## Retrieval order

For a non-preprint record, use this order:

1. official venue-provided `.bib`, BibTeX block, or BibTeX download;
2. DOI content negotiation using `Accept: application/x-bibtex`;
3. explicit unavailable result while retaining the paper record.

For `preprint_only`, use the bundled arXiv MCP `export_citations` tool. It reads
the arXiv API record and preserves a requested version suffix.

## Validation

Accept a retrieved entry only when:

- it contains a parseable BibTeX entry and title field;
- its normalized title matches the resolved paper title;
- its year matches the venue year when both are present;
- the source is the canonical official URL, an official citation link reached
  from it, DOI content negotiation for its DOI, or arXiv for a preprint-only
  record.

Do not invent missing authors, venue, pages, DOI, year, entry type, or citation
key. Do not silently clean a source record beyond returning the exact matched
entry. Include `source_type` and `source_url` in machine-readable outputs.

BibTeX availability never controls paper inclusion. Report each requested
citation as either `bibtex_status: available` or
`bibtex_status: unavailable`, with `unavailable_reason` in the latter case.

## CLI

Resolve the plugin root and run:

```bash
conda run -n ai-paper-search ai-paper-bibtex \
  --title "<exact resolved title>" \
  --canonical-url "<canonical_citation_url>" \
  --status "<acceptance_status>" \
  --year <venue_year> \
  --doi "<doi when present>" \
  --format json
```

Omit `--year` or `--doi` when absent. Missing or mismatched citation metadata
returns a normal `unavailable` result so a batch can continue.
