# Evaluation protocol

Use the exact same query, years, and maximum result count for both systems.

The operational baseline is the installed ARS discovery policy plus arXiv MCP
search. Because ARS is an LLM workflow rather than a deterministic retriever,
retain its raw candidate list and exact prompt. Do not present one run as a
general model-quality benchmark.

Score independently:

- requested venue-year cells attempted;
- papers with official acceptance evidence;
- correct canonical citation version;
- retained arXiv reading copy;
- Findings correctly labeled;
- arXiv-only items not counted as accepted;
- false formal-venue claims;
- relevant unique titles.

Use a manually adjudicated official-source gold list for recall claims. If no
independent gold list is available, call the result a coverage audit rather
than a recall benchmark.
