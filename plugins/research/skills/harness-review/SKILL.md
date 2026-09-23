---
name: harness-review
description: Revise or audit the research Codex harness after an observed bad response, an instruction-cleanup request, or a backbone-model change.
---

# Harness review

Use this skill for deliberate instruction maintenance. A complaint about one task does not by itself justify a permanent rule; first determine whether the work product, the instruction, or the model behavior needs correction.

## Diagnose from an example

- Establish the observed bad answer or action, the desired good one, and the reason the difference matters. Use the user's actual example when available; label a constructed example as illustrative. If the expectation is unclear and changes the rule, ask a focused question after completing the independent review.
- Identify the instruction or missing context that plausibly caused the failure. Check the task's active instruction paths and the relevant owning document. Distinguish a recurrent or predictable ambiguity from a one-off execution error. Correct the work product as well when the user requested that task's completion.
- For a proposed instruction change, show **bad case → good case → judgment reason**, then state the exact existing sentence to keep, revise, move, or delete. The comparison is analysis; put an example in the enduring guide only when it resolves a real ambiguity.

## Audit existing instructions

- When asked for a full audit, or when a backbone model changes, inspect the visible effective instruction stack and its owners: platform constraints, user-controlled global/project `AGENTS.md`, relevant guidance, skills, and current runtime configuration. Edit only user-owned files; report conflicts with platform instructions that cannot be edited here. Review all in-scope instruction files for duplicate owners, contradictory directions, stale model or tool assumptions, overly broad triggers, unnecessary pre-reading or repeated checks, and rules that no longer change outcomes. Do not assume that a file named `AGENTS.md` is automatically loaded across an independent Git boundary; verify the actual route where it matters.
- Test a questionable rule against a concrete bad case and good case. Explain why keeping, rewriting, moving, or deleting it better serves the user's research purpose. Preserve scientific integrity, project boundaries, evidence provenance, and explicit user decisions; a newer model alone is not evidence that a boundary can be dropped.
- For model-change audits, identify the exact active model and check current official documentation for that model before adapting prompting advice. Compare official guidance with observed local failures, and separate provider-specific examples from Codex behavior. Record uncertainties instead of asserting that a model automatically follows an unstated convention. Revisit only model-sensitive instructions unless the user requests a broader audit.

## Apply and verify

When the research harness is installed, follow its `guidance/project_structure.md` in the active Codex home for document placement, coherent edits, validation, and the designated Git workflow. If that guide is absent, identify the current instruction owner instead of assuming the research-harness layout. This skill owns the example comparison and audit method; the applicable `AGENTS.md` or task guide owns enduring behavior.

Report the example comparison, the exact instruction changed or the reason no change was warranted, and the verification. For a requested audit, group findings by keep, revise, move, and delete with decisive evidence; do not manufacture bad cases to fill a template.
