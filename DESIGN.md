---
name: Penned or Prompted?
description: A research instrument in UST gold and black that reads an AI-generation probability like a measurement on the study's Table 4 scale.
colors:
  ink: "#121212"
  ink-muted: "#b6b6ae"
  paper: "#f6f6f4"
  panel: "#ffffff"
  text: "#121212"
  muted: "#5c5c58"
  rule: "#d4d4cf"
  track: "#e2e2de"
  gold: "#f5b800"
  error: "#9b2c1c"
  paper-dark: "#0e0e0d"
  panel-dark: "#181816"
  text-dark: "#edede8"
  muted-dark: "#a3a39c"
  rule-dark: "#34342f"
  track-dark: "#2a2a26"
  error-dark: "#ff9a85"
typography:
  wordmark:
    fontFamily: "Cinzel, serif"
    fontSize: "clamp(22px, 2.4vw, 30px)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "0.08em"
  display:
    fontFamily: "Geist, sans-serif"
    fontSize: "clamp(88px, 10vw, 168px)"
    fontWeight: 600
    lineHeight: 0.88
    letterSpacing: "-0.04em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Geist, sans-serif"
    fontSize: "clamp(20px, 2vw, 26px)"
    fontWeight: 600
    lineHeight: 1.25
  title:
    fontFamily: "Geist, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    fontFeature: "tnum"
  body:
    fontFamily: "Geist, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.65
  body-small:
    fontFamily: "Geist, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontFamily: "Geist, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Geist Mono, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.12em"
rounded:
  none: "0px"
spacing:
  cell: "12px"
  stack: "14px"
  panel: "28px"
  column-gap: "32px"
  row-gap: "40px"
  page-end: "64px"
  page-x: "clamp(16px, 4vw, 56px)"
components:
  button-primary:
    backgroundColor: "{colors.text}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "14px 26px"
  button-primary-hover:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "14px 26px"
  paste-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.none}"
    padding: "28px"
  masthead:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    padding: "24px clamp(16px, 4vw, 56px)"
  signal-bar:
    backgroundColor: "{colors.track}"
    height: "8px"
  band-rail:
    backgroundColor: "{colors.track}"
    height: "14px"
---

# Design System: Penned or Prompted?

## Overview

**Creative North Star: "The Thomasian Instrument"**

The page is a measuring instrument issued under the University of Santo Tomas's own colours: an ink masthead, a paper ground ruled by a visible 12-column grid, and a single gold that belongs to the model's signal. The score is read the way a gauge is read: a large tabular numeral, a band name, and a needle on a segmented rail whose proportions are the paper's Table 4 bands, with the 0.50 decision threshold drawn as a tick. Everything around the reading is quiet so the reading carries the weight.

Density is calm and documentary. Structure comes from 1px hairlines and square edges, not from cards, shadows or tint. Labels are set as uppercase Geist Mono tokens, the way a lab instrument stencils its scales; the wordmark alone speaks in Roman capitals (Cinzel). Light and dark follow the device; gold and ink stay fixed across both.

The world refuses the category default for AI detectors: a circular gauge on a white SaaS page with purple or blue accents.

**Key Characteristics:**
- Ink masthead band, paper ground, white field panel; gold only where the model speaks.
- A drawn 12-column grid (hairline at the start of every column track).
- Zero radius everywhere; 1px hairlines for every division.
- Display-size tabular score, Table 4 band rail with threshold tick and needle.
- Uppercase mono tokens for labels, scales and metadata.

## Colors

A near-monochrome ink-and-paper palette with one saturated gold reserved for measurement.

### Primary
- **Thomasian Gold** (gold): the model's signal and nothing else. It fills the 80-100 "Highly likely AI" rail segment, the passage score bars, and the "or" in the wordmark. Identical in light and dark.

### Neutral
- **Instrument Ink** (ink): the masthead band in both modes; also the light-mode text colour (text).
- **Masthead Graphite** (ink-muted): the mono method line on the ink masthead. Fixed in both modes because the masthead is always ink.
- **Cool Paper** (paper / paper-dark): page ground; also the inverted text colour on the primary button and the masthead wordmark.
- **Field White** (panel / panel-dark): the paste panel, the only raised plane.
- **Bone Text** (text-dark): body and display text in dark mode.
- **Stencil Grey** (muted / muted-dark): mono labels, placeholder, caption, caveat, scale numbers.
- **Hairline** (rule / rule-dark): every 1px division: panel border, token cells, passage rows, textarea scroll edge, secondary button stroke.
- **Rail Track** (track / track-dark): unfilled rail segments, empty bar tracks, and the drawn grid lines.

### Tertiary
- **Notice Red** (error / error-dark): the error notice stroke and text only.

### Named Rules
**The Signal Gold Rule.** Gold is reserved for the model's signal: the wordmark "or", the 80-100 rail segment, and passage bars. Never on controls, focus rings, caret, selection, links, borders or decoration. Controls and browser surfaces stay ink and paper.

**The Inverted Selection Rule.** Selection, caret and focus use the text colour against paper (selection inverts text on paper; focus is a 2px text-colour outline offset 3px).

## Typography

**Display Font:** Cinzel 600 (with serif), wordmark only
**Body Font:** Geist (with sans-serif)
**Label/Mono Font:** Geist Mono (with monospace)

**Character:** Roman capitals give the masthead its institutional seal; Geist carries every reading and sentence plainly; Geist Mono, uppercase and tracked, labels scales and metadata like stencilled instrument marks.

### Hierarchy
- **Wordmark** (Cinzel 600, clamp(22px, 2.4vw, 30px), 1.1, 0.08em): the product name in the masthead. Cinzel appears nowhere else.
- **Display** (Geist 600, clamp(88px, 10vw, 168px), 0.88, -0.04em, tabular): the overall probability. The percent sign sits at 0.34em, top-aligned.
- **Headline** (Geist 600, clamp(20px, 2vw, 26px), 1.25): the band name under the score.
- **Title** (Geist 600, 20px, tabular): values in the data token row (words, passages, threshold).
- **Body** (Geist 400, 17px, 1.65): the pasted text. Empty-state prose runs 17px / 1.55 in muted, max 46ch.
- **Body small** (Geist 400, 14px, 1.45): passage excerpts, clamped to two lines.
- **Caption** (Geist 400, 13px, 1.55, max 60ch): the "probability, not proof" caveat.
- **Label** (Geist Mono 500, 12px, 1.4, 0.12em, uppercase): field labels, word count and hint, section labels, token names, passage indices, the method line. Rail scale numbers and band names use the same face at 0.06em; passage percentages at 0.04em in text colour.

### Named Rules
**The Tabular Reading Rule.** Every number that is a reading (score, token values) is set with tabular numerals so values align and do not jitter.

**The One Seal Rule.** Cinzel is the wordmark's alone; headings and readings are Geist.

## Layout

A 12-column grid, max 1600px wide and centred, with 32px column gaps, 40px row gaps, 40px top and 64px bottom padding, and side padding of clamp(16px, 4vw, 56px). The grid is drawn: a track-coloured 1px rule at the start of every column, spanning the full height of the grid but only the column area (never the side padding), painted on a pseudo-element behind content. On desktop the paste panel takes columns 1-6 and the result columns 7-12.

At 960px and below the drawn grid is hidden, both regions span all columns (result stacks under the paste panel), the paste panel drops its 560px minimum height, the rail's band-name row is hidden (the headline band name carries it), and passage rows reflow to index / excerpt / value with the bar on a second row.

Rhythm: 12px inside data cells and passage rows, 14px between panel parts, 20px between result blocks, 28px panel padding.

## Elevation & Depth

Flat. There are no shadows anywhere. Depth is tonal: the white field panel sits on paper behind a 1px hairline, and the ink masthead is a solid band. Focus and hover never lift; they change stroke or fill.

### Named Rules
**The Hairline Not Shadow Rule.** Separate planes with a 1px rule or a tonal step, never with a shadow.

## Shapes

Square. Radius is zero on every element, including buttons, the panel, bars and the rail. Divisions are 1px hairlines. The rail is three flat segments sized 20 / 59 / 21 with 3px gaps; the threshold is a 1px text-colour tick (26px tall) at 50%; the needle is a 4px text-colour bar (36px tall) standing proud of the rail.

## Components

### Buttons
Blunt, rectangular, inked.
- **Shape:** square corners (0px), 1px stroke, Geist 600 14px, padding 14px 26px.
- **Primary:** text-colour fill with paper text and a matching 1px stroke ("Check text").
- **Hover / Focus:** on hover-capable devices the primary empties to transparent with text-colour text; the secondary's stroke darkens from hairline to text colour. Transitions 0.2s on the expo-out curve. Focus is the global 2px text-colour outline, offset 3px.
- **Secondary:** transparent with a hairline stroke ("Clear"), sits left of the primary with a 10px gap.
- **Disabled:** 0.45 opacity, not-allowed cursor; the adjacent mono hint states why.

### Cards / Containers
- **Corner Style:** square (0px).
- **Background:** the paste panel is Field White on Cool Paper; it is the only container.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px hairline.
- **Internal Padding:** 28px.

### Inputs / Fields
- **Style:** the white paste panel is the text field. The textarea inside has no box, no outline and a transparent ground; a single hairline on its top edge marks the scroll edge so a scrolled first line does not look sliced. Body type, 17px / 1.65.
- **Focus:** the whole panel takes a 2px text-colour outline (inset 1px) while any part of it has focus.
- **Footer:** the mono word count and hint on the left, the button pair on the right.

### Navigation
None beyond the masthead: an ink band, 24px vertical padding, the Cinzel wordmark left and the mono method line right, wrapping on narrow screens.

### Band Rail (signature)
Three segments in Table 4 proportions (0-20, 21-79, 80-100), the last in gold and the others in track. A threshold tick at 50%, mono scale numbers at their true positions (0, 20, 50 · threshold, 80, 100), band names centred under their segments. When a result lands the needle sweeps from 0 and settles on the score (0.9s, expo-out). Beneath, a muted mono line states the band set and the threshold relation ("Table 4 bands · above/below 0.50 threshold") rather than a verdict.

### Data Tokens
A three-cell definition row between top and bottom hairlines, cells divided by vertical hairlines: mono label above a tabular Title value.

### Passage Rows
An ordered list of rows split by hairlines: two-digit mono index, two-line excerpt, an 8px gold bar on a track that fills to its score (0.9s, expo-out), and a right-aligned mono percentage. Both animations stop under reduced motion.

### Error Notice
1px Notice Red stroke, Notice Red 14px text, 14px 16px padding, square. When the service is down it carries the start command in a mono code line in text colour.

## Do's and Don'ts

### Do:
- **Do** keep gold to the model's signal: the 80-100 rail segment, passage bars and the wordmark "or".
- **Do** use ink, paper and the text colour for every control, focus ring, caret and selection.
- **Do** keep every corner at 0px and every division at 1px.
- **Do** set readings in Geist with tabular numerals and labels in uppercase Geist Mono at 12px.
- **Do** show the score with its band and the Table 4 rail, and state the threshold relation as a muted mono line rather than a verdict.
- **Do** keep the 12-column grid drawn on desktop, inside the column area only.

### Don't:
- **Don't** put gold on buttons, links, focus outlines, selection, borders or decoration.
- **Don't** add shadows or rounded corners.
- **Don't** draw a box inside the paste panel; the panel is the field.
- **Don't** use Cinzel outside the wordmark.
- **Don't** use a circular gauge or purple and blue accents.
