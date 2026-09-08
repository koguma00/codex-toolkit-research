---
name: siit-presentation
description: Create or revise research presentations through a Google Slides-first narrative workflow and detailed PowerPoint finishing in the user's preferred SIIT/KAIST visual style. Use when the user requests their saved presentation design, SIIT styling, or coordinated Google Slides, PPTX, or HTML presentation work; do not apply it to unrelated styles unless requested.
---

# SIIT presentation

Create an editable research deck whose argument is clear before detailed visual finishing.
The saved example's direct formatting is the visual authority; the normalized THMX and
sanitized PPTX are structural assets.

## Required references

Read [references/workflow.md](references/workflow.md) and
[references/style-system.md](references/style-system.md) for every creation or restyling task.
Read [references/layout-catalog.md](references/layout-catalog.md) when choosing layouts. Use
[references/design-tokens.json](references/design-tokens.json) when exact values are useful.

## Non-negotiable defaults

- Use `Noto Sans KR` for every editable text element in Google Slides, PowerPoint, and HTML,
  including Korean, Latin text, numbers, captions, and citations.
- Work in 16:9 unless the user or venue specifies another size.
- Use Google Slides for the first draft and narrative/layout iteration unless the user explicitly
  requests a local-only or PPTX-first workflow.
- If Google Slides cannot be accessed or edited, ask the user how to proceed and wait for their
  answer. Do not silently substitute PPTX, HTML, or another authoring surface.
- Move to PowerPoint only after the sequence and visible copy are stable, then finish master
  application, exact spacing, alignment, line breaks, figure treatment, and export quality.
- Use HTML as an inspectable visual prototype or design reference, not as a substitute when
  the user requested an editable Slides or PowerPoint deliverable.
- Preserve editable text, shapes, charts, and tables whenever the target format allows it.
- Never copy the reference deck's research content or invent claims, citations, numbers, or
  publication status to fill a layout.

## Authoring decisions

1. Establish the audience, decision or communication goal, output surfaces, and source material.
2. Give each slide one communicative job and write its takeaway before selecting a layout.
3. Select the closest layout family from the catalogue and adapt it to the information structure.
4. Prefer one large diagram, figure, or comparison over dense prose. Use blue for the main
   conceptual path and green for extension, complementarity, or positive evidence.
5. Keep citations and qualifications quiet but readable near the bottom edge.
6. At the Slides-to-PowerPoint gate, freeze slide order and visible copy unless a finishing
   problem exposes a genuine narrative defect.
7. Inspect the final PPTX and exported PDF or images for clipping, font substitution, weak
   contrast, crowded figures, inconsistent alignment, and broken page boundaries.

## Assets

- [assets/siit-reference-template.pptx](assets/siit-reference-template.pptx): sanitized,
  editable PowerPoint seed with generic content.
- [assets/siit-noto-sans-kr.thmx](assets/siit-noto-sans-kr.thmx): PowerPoint theme normalized
  to `Noto Sans KR`.
- `assets/previews/`: inspectable SVG layout families.
- [assets/html/siit-style-reference.html](assets/html/siit-style-reference.html): self-contained
  HTML reference for quickly comparing the visual language and component rhythm.
- `assets/logos/`: SIIT/KAIST marks for affiliated work only.

## Handoff

Return the requested editable source and an inspection format when practical. State which
surfaces, template, and font were used. Flag any element that could not remain editable or
any font substitution observed during export.
