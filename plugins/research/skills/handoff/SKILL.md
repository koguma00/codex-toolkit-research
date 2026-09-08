---
name: handoff
description: Compact the current conversation into copyable Markdown for another agent to continue the work.
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Output it directly in the conversation inside one fenced Markdown code block so the user can copy and paste it. Do not save a file unless the user explicitly asks. Output no preamble or follow-up outside the block.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
