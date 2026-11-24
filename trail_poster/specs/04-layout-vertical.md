# 04 — Layout A: vertical title (Art Loeb / Bartram)

**Does one thing:** draws a poster in the vertical-title style from the track
and approved points.

## Look (matched to existing posters)
- Left band: gray compass (ring, "N", half-filled needle) at top; trail name
  below it in **Montserrat Black**, uppercase, widely letter-spaced, rotated to
  read top to bottom.
- Trail: black line about 1.8 pt on the 14×10 in master; dashed pieces as in
  `01-input`.
- Labels: **Montserrat Regular**, uppercase, letter-spaced, gray `#6d6e71`.
- Icons in gray `#939598`: hiker at start and end, tent at shelters and camps,
  waterfall lines, a thin black ridgeline beside peaks, an open circle for
  generic points.
- Mileage table: **Source Sans 3** (SemiBold headers, Regular rows), gray,
  placed in whichever corner the trail leaves empty.
- `© Beech Creek Naturals <year>` small, bottom right.
- White background.

## Rules
- North is always up; no rotation.
- Labels never overlap each other, the table, the title or the trail text area.
  Any label that can't be placed cleanly is reported, not hidden silently.
- Master canvas is 14×10 in landscape. For very tall, narrow trails the tool
  may **suggest** 10×14 portrait; David confirms it at Gate 2.

## Done when
- [ ] Shown next to the Art Loeb poster, a stranger would call them a set.
      (David judges at Gate 3 on the first real poster.)
- [x] No label collisions in the preview. `python tests/test_layout.py` (8/8):
      no overlaps, nothing off the page, no label crossing the trail, trail kept
      out of the table, and an unplaceable label is reported, not hidden.

## Built (2026-11-23)
- Labels try left, right, above and below. If any label still crosses the trail
  or collides, the map shrinks a step to make room (up to 3 times); anything
  still wrong is reported as a warning.
- Tuned against the Art Loeb poster: labels 9.5 pt, table 12 pt with tighter
  rows and one-line headers up to 15 characters, wider letter-spacing, title
  max 38 pt, compass a little larger with a thicker ring, trail line 1.2 pt.
- The style-test map (`tests/make_style_fixture.py`) uses a made-up line and is
  titled TEST TRAIL so it can't be mistaken for a real trail map.

## Decisions (confirmed 2026-11-23)
- [x] **V4.1** Fonts confirmed: Montserrat for the title and labels, Source Sans 3
      for the table and © line.
- [x] **V4.2** Portrait is suggested by the tool, never chosen on its own.
