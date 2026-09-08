# Research plugin development

Own one `research` plugin with five focused skills: ai-paper-search,
siit-presentation, aica-reconnect, eli5 and handoff. Keep each skill scoped to
its task; do not introduce an overarching research workflow or manager skill.

## Structure

- `plugins/research/`: shipped skills, search Python package, assets and MCP declaration.
- `.agents/plugins/marketplace.json`: single public marketplace entry.
- `bootstrap.py`: optional installation and explicit legacy migration.
- `plugins/research/sources.json` and licenses: imported source attribution.

Use the dedicated `ai-paper-search` Conda environment for search development
and pytest. Python 3 is sufficient for bootstrap/AICA unit tests. Preserve
original SIIT assets and external licenses. Update the plugin version for
releases, validate, commit/push, then upgrade the marketplace and install
`research@research-codex`. Edit maintained sources here, not the installed cache.

Never commit authentication, local profiles, SSH keys, host addresses, pairing
codes, session state or generated artifacts. AICA operations require the user's
task-specific authorization; packaging tests use temporary fixtures.
