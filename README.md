# Research plugin

One Codex plugin containing five focused skills and the arXiv MCP connection.
The repository name is retained to preserve existing links and Git history.

| Skill | Purpose |
| --- | --- |
| ai-paper-search | Official AI proceedings, version verification and BibTeX |
| siit-presentation | SIIT/KAIST presentation workflow and editable templates |
| aica-reconnect | AICA SSH recovery and optional mobile pairing |
| eli5 | Simple visual HTML explanations |
| handoff | Copyable context for another conversation |

## Install on another device

Tell Codex: `Install my research plugin from https://github.com/koguma00/codex-toolkit-research`.
With Codex CLI available:

```bash
codex plugin marketplace add https://github.com/koguma00/codex-toolkit-research.git
codex plugin add research@research-codex
```

If the marketplace is already registered, upgrade it instead of adding it.
Alternatively clone this repository and run `python3 bootstrap.py` (`py -3` on Windows).
Start a new task to load the new skill/tool set.

All five skills, search source code, and presentation assets are included.
The search runtime uses its dedicated Conda environment; see
[the runtime guide](plugins/research/README.md). The arXiv MCP runtime uses
`uvx arxiv-mcp-server==0.7.1`; `uvx` must be on PATH. This external tool runtime
is separate from project ML environments. Installation does not install Conda,
uv, or authenticate services. Google Slides access and AICA credentials are
configured separately when needed. Global/project AGENTS remain in their own
Git repositories.

## Update

```bash
codex plugin marketplace upgrade research-codex
codex plugin add research@research-codex
```

There is no manager skill and no installation registry of other plugins.

## Migrate an existing toolkit installation

Run `python3 bootstrap.py --migrate-legacy`. It installs and verifies the new
plugin first, then removes the former paper-search, presentation and manager
plugins. Toolkit-managed standalone ELI5/Handoff folders are moved intact to a
dated local backup. Unmanaged same-name folders remain untouched and are
reported for manual review. Authentication and machine settings are not copied.

## Development

All five skills are maintained under `plugins/research/skills/`; search code is
under `plugins/research/src/`. Former standalone repository histories are preserved in maintainer Git backups.
They are no longer dependencies. Edit the unified source here.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
conda run -n ai-paper-search python -m pytest plugins/research/tests
```

Read AGENTS.md before editing. Imported revisions and licenses are recorded in
[notices](plugins/research/THIRD_PARTY_NOTICES.md) and
[sources](plugins/research/sources.json). Deep Research and connected service
plugins remain independently installed.
