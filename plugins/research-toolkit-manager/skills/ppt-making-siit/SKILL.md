---
name: ppt-making-siit
description: Create or revise research presentations in the user's preferred SIIT/KAIST visual style for Google Slides or PowerPoint. Use when the user requests SIIT styling, their preferred presentation design, or a deck based on their saved presentation example; do not apply it to unrelated presentation styles unless requested.
---

# SIIT presentation making

Create an editable research deck whose argument is clear before adding visual polish.
Treat the saved example's direct formatting as the visual authority and the THMX-derived
theme as a structural asset.

## Required references

Read [references/style-system.md](references/style-system.md) for every task that creates
or restyles slides. Read [references/layout-catalog.md](references/layout-catalog.md) when
choosing or varying slide layouts. Use
[references/design-tokens.json](references/design-tokens.json) when exact values are useful
for generated PPTX, SVG, HTML, or Google Slides elements.

## Non-negotiable defaults

- Use `Noto Sans KR` for every text element, including Korean, Latin text, numbers,
  equations rendered as text, captions, and citations. Do not restore the legacy
  Kimpo Peace Gothic declarations embedded in the source THMX.
- Work in 16:9 unless the user or venue specifies another size.
- Preserve editable text, shapes, charts, and tables whenever the target format allows it.
- Keep Google Slides as the iteration surface when the user is still revising the story;
  use PowerPoint for final production when requested.
- Never copy the reference deck's research content. Reuse only its visual language,
  hierarchy, spacing, master structure, and components.
- Never invent claims, citations, experimental numbers, or publication status to fill a
  layout.

## Authoring decisions

1. Establish the audience, presentation goal, output format, and current narrative.
2. Give each slide one communicative job and write its takeaway before choosing a layout.
3. Select the closest layout family from the catalogue; adapt it when the content demands
   a better information structure rather than forcing a template.
4. Prefer a large diagram, figure, or comparison over dense prose. Use blue for the main
   conceptual path and green for extension, complementarity, or positive evidence.
5. Keep citations and qualifications quiet but readable near the bottom edge.
6. Render or export the deck at its intended dimensions and inspect for clipping, font
   substitution, weak contrast, crowded figures, and inconsistent alignment.

## Assets

- Start from [assets/siit-reference-template.pptx](assets/siit-reference-template.pptx)
  when a local editable PowerPoint seed is useful. It is a sanitized derivative containing
  generic sample content only.
- Use [assets/siit-noto-sans-kr.thmx](assets/siit-noto-sans-kr.thmx) when a PowerPoint theme
  file is required. Its typeface declarations have been normalized to `Noto Sans KR`.
- Use the SVGs under `assets/previews/` as fast visual references for the layout families.
- Use the logos under `assets/logos/` only for SIIT/KAIST-affiliated work or when the user
  explicitly asks for them. Do not imply institutional endorsement for unrelated work.

## Handoff

Return the requested editable source plus an inspection format such as PDF or rendered
slide images when practical. State which font and template were used and flag any element
that could not remain editable or any font substitution observed during export.
