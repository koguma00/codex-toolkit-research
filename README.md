# Research Codex Toolkit

Public, version-pinned management for a personal Codex research stack.

## New device

Give a fresh Codex session only this request:

> https://github.com/koguma00/codex-toolkit-research 에서 연구용 툴킷 설치해.

No prior plugin context or GitHub login is required. Codex should clone this
public repository and run one of these commands:

```bash
# macOS or Linux
python3 bootstrap.py

# Windows PowerShell
py -3 bootstrap.py
```

Start a new Codex conversation after installation. You can then say only:

- `연구용 플러그인 설치해.`
- `연구용 플러그인 업데이트해.`
- `연구용 플러그인 상태 확인해.`
- `AICA 포트 <현재 포트>로 다시 연결하고 iPhone 연결 코드 발급해.`

## Default stack

- Research Toolkit Manager `0.4.0`, including the macOS/Windows AICA reconnect
  and iPhone Remote pairing skill
- SIIT Presentation `0.1.1`, installed from `codex-presentation-siit` with a Google Slides-first and PowerPoint-finishing workflow
- ARS-Codex `0.1.27`
- AI Paper Search `0.3.1`, including the pinned arXiv MCP runtime
- Anthropic Community `eli5`, pinned by commit with a minimal Codex adapter
- Matt Pocock `handoff`, pinned by commit with a copyable-output Codex adapter

First-party repositories follow `codex-<purpose>-<specialization>`, so tools
sort by purpose while the final segment records the implementation intent or local style.

The standalone arXiv MCP plugin is superseded by AI Paper Search and removed
during toolkit updates to avoid loading the same MCP server twice.

Project-specific tools such as `auto-eval-MAS` are intentionally not managed
here. Keep each one in its own project-scoped Codex plugin repository.

The repository contains no credentials or private Codex data. Dependencies are
downloaded directly from their public upstream repositories at the refs and
commits pinned in `plugins.lock.json`.

## AICA reconnect on macOS and Windows

The bundled `aica-reconnect` skill uses the same OpenSSH aliases and persistent
AICA environment on both platforms. macOS stores them under `~/.ssh`; Windows
uses `%USERPROFILE%\.ssh` and applies private-key ACLs with `icacls`. Every
computer creates its own `aica-codex` Ed25519 key. Only public keys are copied
to the persistent server-side registry; private keys never enter this
repository or move between computers.

Give Codex the current proxy port and ask it to reconnect. On a new computer,
also provide the AICA host, SSH user, personal persistent root, and admin PEM
path when asked. Those connection settings are saved only in that computer's
local Codex home, so later port changes need only the new port. Unknown or
changed SSH host keys require explicit fingerprint approval before the skill
trusts them. Connection settings, pairing codes, remote-control environment
IDs, credentials, and Codex history are not committed.
