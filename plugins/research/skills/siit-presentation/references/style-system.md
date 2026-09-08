# SIIT visual system

## Source authority

The user's saved Google Slides example is authoritative for actual spacing, hierarchy,
content density, and component treatment. The original `SIIT_JC169` THMX is useful for
master structure and brand artwork, but its legacy font metadata and default Office accent
slots are not authoritative.

Detailed source and sanitization metadata is recorded in [source-provenance.json](source-provenance.json).

When the sources disagree, use this priority:

1. the user's explicit instruction for the current deck;
2. this maintained style system;
3. direct formatting observed in the saved example;
4. the sanitized PPTX seed and normalized THMX.

## Typography

Use `Noto Sans KR` exclusively so the same deck remains stable in Google Slides and
PowerPoint. Apply the typeface to Latin, East Asian, and complex-script font declarations
when authoring OOXML.

| Role | Default | Guidance |
| --- | ---: | --- |
| Slide title | 36 pt bold | Left aligned; approximately 34–38 pt is acceptable |
| Section or card heading | 18 pt bold | Use sparingly for local structure |
| Body | 12.5 pt regular | Prefer short statements; avoid going below 12 pt |
| Annotation | 10.5 pt regular | Figure labels, qualifiers, and compact notes |
| Citation | 9.5–10 pt regular | Quiet placement at the bottom; never unreadably small |

Use dark text `#2D3741` on white. Prefer weight and spacing over extra colors to express
hierarchy. Avoid all-caps paragraphs and excessive bolding.

## Palette

| Role | Value | Typical use |
| --- | --- | --- |
| Primary navy | `#004191` | Main title emphasis, primary path |
| Primary blue | `#0E6EB8` | Rules, process arrows, key structures |
| Primary green | `#8EC31F` | Extension, positive evidence, complementarity |
| Main dark text | `#2D3741` | Titles and body copy |
| Deep blue-gray | `#142E47` | Strong labels and dark anchors |
| Secondary gray | `#636E78` | Supporting copy |
| Light border | `#CDD5DD` | Containers and separators |
| Secondary border | `#D1D9E0` | Tables and low-emphasis rules |
| Background | `#FFFFFF` | Default canvas |

Purple `#7030A0` and orange `#ED631A` are optional categorical accents. Use them only
when blue and green cannot distinguish a necessary category; do not turn them into the
dominant palette.

## Canvas and grid

- Default canvas: 16:9, white.
- Keep a wide top title region and a thin blue-to-green rule immediately beneath it.
- Align content to a small number of persistent vertical guides. Typical outer margins are
  4.5–6% of slide width and 5–7% of slide height.
- Reserve an unobtrusive lower-right region for SIIT/KAIST identity when applicable.
- Let the main figure or diagram occupy most of the slide. Explanatory text should clarify
  the visual, not restate it.
- Use whitespace to separate ideas. Avoid filling empty areas with decorative objects.

## Components

- Process steps: thin rectangular containers, light-gray borders, small numbered labels,
  restrained blue/green accents, and simple arrows.
- Timelines: a clear horizontal or vertical spine with compact stage labels and an obvious
  current/future distinction.
- Results: table-like rows or aligned metric blocks with minimal borders. Make the measured
  quantity and interpretation more prominent than ornament.
- Research figures: use a large image area, a concise caption, and enough padding for axis
  labels and legends.
- Publication or deliverable lists: numbered rows with short contribution summaries and a
  quiet venue/status field.

Rounded rectangles are secondary. Avoid heavy shadows, glass effects, decorative gradients,
cream grids, arbitrary icons, and repetitive dashboard-style card walls.

## Logos and institutional identity

Use SIIT and KAIST marks only when the presentation is affiliated with them or the user asks
for the marks. Preserve aspect ratio, keep them small, and do not recolor them. When the deck
is personal or unaffiliated, omit the logos while retaining the typography, palette, and
layout language.

## Quality check

- The title and main claim must remain legible at presentation distance.
- No text should clip, overlap, or wrap into an unintended additional line.
- All editable text must report `Noto Sans KR` after export; inspect both Latin and Korean
  runs because PowerPoint stores them separately.
- Diagrams must preserve scientific meaning and source provenance.
- Repetition should create rhythm, not make every slide structurally identical.
