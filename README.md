# Codex toolkit

One `junwon` marketplace with two independently installable Codex plugins.

| Plugin | Skills | Other components |
| --- | --- | --- |
| `research@junwon` | ai-paper-search, siit-presentation, eli5, handoff | AI Paper Search CLI and arXiv MCP |
| `management@junwon` | aica-reconnect, harness-review | — |

## Install on another device

```bash
codex plugin marketplace add https://github.com/koguma00/codex-toolkit.git
codex plugin add research@junwon
codex plugin add management@junwon
```

If `junwon` is already registered, upgrade it rather than adding it. Alternatively,
clone this repository and run `python3 bootstrap.py` (`py -3` on Windows).
Start a new Codex task to load the updated skills and tools.

The search runtime uses a dedicated Conda environment; see the
[research runtime guide](plugins/research/README.md). Its arXiv MCP declaration
uses `uvx arxiv-mcp-server==0.7.1`, which must be available on PATH. The plugin
installation does not install Conda or uv, authenticate connected services,
or install the separate [`codex-harness`](https://github.com/koguma00/codex-harness).
Configure Google Slides and AICA access separately when needed.

## Update

```bash
codex plugin marketplace upgrade junwon
codex plugin add research@junwon
codex plugin add management@junwon
```

Existing `research@research-codex` installations can be migrated with
`python3 bootstrap.py --migrate-legacy`. The script verifies both new plugins
before removing former plugin installations. It preserves unmanaged standalone
skills and backs up toolkit-managed ELI5/Handoff copies if present.

## Development

Edit the source in `plugins/research/` or `plugins/management/`, not an installed
cache. The former standalone plugin repositories are historical sources, not
dependencies. Their provenance and licenses are recorded in the
[source registry](plugins/research/sources.json) and
[notices](plugins/research/THIRD_PARTY_NOTICES.md).

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
conda run -n ai-paper-search python -m pytest plugins/research/tests
```

Read [AGENTS.md](AGENTS.md) before editing. Deep Research and connected service
plugins remain independently installed.
