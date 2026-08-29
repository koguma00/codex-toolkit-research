---
name: research-toolkit-manager
description: Install, update, or report the user's minimal research plugin stack. Use when the user says “연구용 플러그인 설치해”, “연구용 플러그인 업데이트해”, “연구용 플러그인 상태 확인해”, or asks to manage the research Codex toolkit.
---

# Research Toolkit Manager

Manage only the dependencies declared in `../../registry/plugins.lock.json`.
Do not install experimental entries unless the user explicitly names them.

Resolve `../../scripts/manage.py` relative to this `SKILL.md`, convert it to an
absolute path, and use the matching command:

- Install: `python3 <absolute-manage.py> install`
- Update: first run `codex plugin marketplace upgrade research-codex`, then
  `codex plugin add research-toolkit-manager@research-codex`, resolve the
  currently installed manager plugin path from `codex plugin list --json`, and
  run its `scripts/manage.py update`.
- Status: `python3 <absolute-manage.py> status`

The commands are intentionally non-interactive. Ask the user only if Codex is
missing, a public repository cannot be reached, or a managed install fails.
After install or update, report the exact installed versions and tell the user
to start a new conversation so newly installed skills and MCP tools are loaded.
