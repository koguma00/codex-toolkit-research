# Research Codex Toolkit

Public, version-pinned management for a minimal Codex research stack.

## One-time setup on a new device

No GitHub login is required:

```bash
codex plugin marketplace add koguma00/research-codex-toolkit --ref main
codex plugin add research-toolkit-manager@research-codex
```

Start a new Codex conversation. You can then say only:

- `연구용 플러그인 설치해.`
- `연구용 플러그인 업데이트해.`
- `연구용 플러그인 상태 확인해.`

## Default stack

- ARS-Codex `0.1.27`
- arXiv MCP Server `0.7.1`

AI Paper Search is tracked as experimental and is not installed by default
until its recall and proceedings-enumeration issues are fixed.

The repository contains no credentials or private Codex data. Dependencies are
downloaded directly from their public upstream repositories at the refs pinned
in `plugins.lock.json`.
