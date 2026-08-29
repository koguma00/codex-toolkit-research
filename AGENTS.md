# Research purpose

This public repository provides a minimal, reproducible Codex research-plugin
stack. It manages only the pinned public dependencies in
`plugins/research-toolkit-manager/registry/plugins.lock.json`. Never add a
plugin to the default set without an explicit user request and a successful
installation check.

# Environment

This repository needs only Git, Python 3, internet access, and a Codex CLI with
plugin support. It contains no credentials and must remain usable through
anonymous HTTPS access.

Interpret short Korean requests as follows:

- “연구용 플러그인 설치해”: run
  `python3 plugins/research-toolkit-manager/scripts/manage.py install`.
- “연구용 플러그인 업데이트해”: pull this repository with
  `git pull --ff-only`, then run
  `python3 plugins/research-toolkit-manager/scripts/manage.py update`.
- “연구용 플러그인 상태 확인해”: run
  `python3 plugins/research-toolkit-manager/scripts/manage.py status`.

Do not install entries under `experimental_plugins` unless the user explicitly
names one. Report exact versions after every operation. Do not store API keys,
Codex authentication, user configuration, task history, or session history.

# Repository structure

- `.agents/plugins/marketplace.json`: public Codex marketplace entry.
- `plugins/research-toolkit-manager/`: installable manager plugin and skill.
- `plugins/research-toolkit-manager/registry/plugins.lock.json`: canonical
  dependency versions and commits.
- `plugins/research-toolkit-manager/scripts/manage.py`: install, update, and
  status implementation.
- `README.md`: anonymous first-install instructions.
