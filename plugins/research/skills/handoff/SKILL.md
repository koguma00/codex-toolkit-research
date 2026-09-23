---
name: handoff
description: Compact the current conversation into copyable Markdown for another agent to continue the work.
---

Return only a compact handoff document as ordinary rendered Markdown in one assistant response, ready for conversation-level copying. Use fenced code blocks only for literal snippets. Save a file only when the user explicitly asks.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Reference content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs) by path or URL, and summarize only the context needed to continue the work.

Exclude sensitive information such as API keys, passwords, and personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
