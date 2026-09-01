# Research Codex Toolkit

Public, version-pinned management for a personal Codex research stack.

## New device

Give a fresh Codex session only this request:

> https://github.com/koguma00/research-codex-toolkit 에서 연구용 툴킷 설치해.

No prior plugin context or GitHub login is required. Codex should clone this
public repository and run:

```bash
python3 bootstrap.py
```

Start a new Codex conversation after installation. You can then say only:

- `연구용 플러그인 설치해.`
- `연구용 플러그인 업데이트해.`
- `연구용 플러그인 상태 확인해.`

## Default stack

- Research Toolkit Manager `0.3.0`
- `ppt-making-siit`, the bundled SIIT/KAIST research-presentation style skill using `Noto Sans KR` for Google Slides and PowerPoint compatibility
- ARS-Codex `0.1.27`
- AI Paper Search `0.3.1`, including the pinned arXiv MCP runtime
- Anthropic Community `eli5`, pinned by commit with a minimal Codex adapter
- Matt Pocock `handoff`, pinned by commit with a copyable-output Codex adapter

The standalone arXiv MCP plugin is superseded by AI Paper Search and removed
during toolkit updates to avoid loading the same MCP server twice.

Project-specific tools such as `auto-eval-MAS` are intentionally not managed
here. Keep each one in its own project-scoped Codex plugin repository.

The repository contains no credentials or private Codex data. Dependencies are
downloaded directly from their public upstream repositories at the refs and
commits pinned in `plugins.lock.json`.
