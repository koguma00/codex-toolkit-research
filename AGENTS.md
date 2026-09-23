# Codex toolkit development

Own one `junwon` marketplace with two focused plugins. `research` contains
ai-paper-search, siit-presentation, eli5 and handoff; `management` contains
aica-reconnect and harness-review. Keep each skill scoped to its task.

## Structure

- `plugins/research/`: research skills, search Python package, assets and MCP declaration.
- `plugins/management/`: AICA and harness management skills.
- `.agents/plugins/marketplace.json`: the two plugin entries.
- `bootstrap.py`: optional installation and explicit legacy migration.
- `plugins/research/sources.json` and licenses: imported source attribution.

Use the dedicated `ai-paper-search` Conda environment for search development
and pytest. Python 3 is sufficient for bootstrap/AICA unit tests. Preserve
original SIIT assets and external licenses. Update the plugin version for
releases, validate, commit/push, then upgrade the marketplace and install
`research@junwon` and `management@junwon`. Edit maintained sources here, not the installed cache.

Never commit authentication, local profiles, SSH keys, host addresses, pairing
codes, session state or generated artifacts. AICA operations require the user's
task-specific authorization; packaging tests use temporary fixtures.
