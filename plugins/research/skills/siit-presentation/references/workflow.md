# Presentation workflow

## Phase 1: narrative draft in Google Slides

Use Google Slides as the canonical working surface while the research story is changing.

- Establish the audience, talk length, central claim, and evidence boundary.
- Draft the slide sequence before detailed styling.
- Keep visible text short and editable in `Noto Sans KR`.
- Use diagrams and placeholder figure frames to test information structure.
- Apply the SIIT title region, palette, spacing, and layout families early enough to expose
  density problems, but do not spend time on pixel-level polish.
- When a native layout creates title or body placeholders, inspect those generated objects before
  adding custom text boxes. Reuse the layout placeholder or delete it first; never leave a second
  empty or overlapping title box.
- Do not assume that inherited layout placeholders share the same geometry as manually positioned
  titles. For every non-cover slide, normalize title X/Y, effective width and height, font size,
  paragraph spacing, and vertical alignment against one approved reference slide. Remove unintended
  empty title paragraphs: identical box coordinates can still render at different heights when a
  vertically centered title contains trailing blank lines.

If Google Slides cannot be accessed or edited, stop before authoring and ask the user how to
proceed. Continue with an editable PPTX draft only when the user explicitly chooses a local-only
or PPTX-first workflow. Do not infer that choice from tool unavailability.

## Phase 2: revision

Revise argument and layout together.

- Verify that each slide has one communicative job and a defensible takeaway.
- When a slide's purpose changes, reassess what its layout implies. Use opposition or directional
  arrows only when the content supports contrast or sequence; a prior-work overview should map
  each work to its research question without implying exclusive choices or an unverified lineage.
- Remove duplicate setup, premature detail, and transitions that do not advance the argument.
- Replace placeholders with source-backed figures, tables, citations, and results.
- Keep speaker-only explanation in notes when the working surface supports it.
- Do not move to detailed PowerPoint finishing while slide order or visible copy remains volatile.

## Slides-to-PowerPoint gate

Move to PowerPoint when all of the following are stable:

- slide sequence;
- visible slide copy;
- required figures and evidence;
- approximate layout family for every slide;
- expected talk duration and section balance.

A later narrative change is allowed when finishing reveals a real communication defect, but avoid
using PowerPoint as the primary brainstorming surface.

## Phase 3: detailed PowerPoint finishing

Use the normalized THMX and sanitized PPTX seed.

- Apply masters and layouts without reintroducing legacy fonts.
- Set Latin, East Asian, and complex-script declarations to `Noto Sans KR`.
- Refine exact alignment, spacing, line breaks, connector geometry, table rhythm, and figure crops.
- Preserve editability for text, shapes, tables, and charts whenever practical.
- Check institutional marks, citation placement, page numbers, and repeated elements.
- Avoid decorative effects that are not part of the SIIT visual language.

## Phase 4: inspection and delivery

Inspect the actual exported artifact, not only the authoring surface.

- Check PPTX reopening and PDF or image export.
- Check Korean and Latin font substitution separately.
- Check clipping, unintended wrapping, low-contrast labels, and off-slide elements.
- For every newly created slide and every slide sharing its layout rule, inspect both the rendered
  image and the object tree: keep exactly one intended title box, remove unused generated
  placeholders, and compare title geometry against the approved reference slide.
- Check consistency across prior-work introductions, overview slides, summary tables, and speaker
  notes after changing the selected literature. Remove stale entries unless they have an explicit
  remaining role, and inspect every affected slide in the rendered deck.
- Verify that every reported number and citation matches its source.
- Deliver the editable source plus a stable inspection format when requested.

## HTML reference

The self-contained HTML asset is a visual and machine-readable reference for layout, typography,
tokens, and component rhythm. It may also be used for fast narrative prototypes. It does not
replace Google Slides or PowerPoint when the requested deliverable must remain editable there.
