# Research purpose

This public repository provides a minimal, reproducible Codex research toolkit.
It manages only the pinned public plugins and skills in
`plugins/research-toolkit-manager/registry/plugins.lock.json`. Never add a
dependency to the default set without an explicit user request and a successful
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

When a user gives this repository URL to a fresh Codex session and asks to
install or set up the research toolkit, clone the public repository if needed
and run `python3 bootstrap.py`. This single entry point installs the manager,
all default plugins, and all default standalone skills.

Do not install entries under `experimental_plugins` unless the user explicitly
names one. Report exact versions after every operation. Do not store API keys,
Codex authentication, user configuration, task history, or session history.

# Repository structure

- `.agents/plugins/marketplace.json`: public Codex marketplace entry.
- `plugins/research-toolkit-manager/`: installable manager plugin, research
  manager skill, and cross-platform AICA reconnect skill.
- `plugins/research-toolkit-manager/registry/plugins.lock.json`: canonical
  plugin and skill versions, paths, and commits.
- `plugins/research-toolkit-manager/scripts/manage.py`: install, update, and
  status implementation.
- `bootstrap.py`: context-free first-install entry point for a new device.
- `README.md`: anonymous first-install instructions.

The bundled AICA skill must remain portable. Never commit its host, SSH user,
personal persistent root, local profile, private key, public-key blob, pairing
code, environment ID, access token, dynamic SSH port, or copied Codex state.
