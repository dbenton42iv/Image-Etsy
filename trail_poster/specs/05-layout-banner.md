# 05 — Layout B: banner with elevation profile (Mountains-to-Sea)

**Does one thing:** draws a poster in the MST style for long, wide trails.

## Look (matched to the MST poster)
- Trail map across the top of the page.
- Bottom left: elevation profile (gray fill `#d1d3d4`, thin black line,
  elevation ticks in feet, mile ticks, "MILES" label); below it the compass
  beside the title in **Montserrat ExtraBold**, uppercase, one or two lines;
  then a gray subtitle. Its wording depends on the map: Claude proposes one
  (states, a region, or miles only) and David confirms it at Gate 2.
- Bottom right: mileage table, same style as layout A.
- Optional numbered segment markers (as on MST) are **not** in v1.

## Rules
- The profile needs elevation in the file. With no elevation, the profile is
  left out and the title block moves up. Claude tells David before rendering.
- Layout choice: the tool suggests banner when the trail is more than about 2×
  wider than tall. **David confirms the layout at Gate 2.**

## Done when
- [ ] Benton MacKaye renders cleanly in this layout (see `08-acceptance.md`).

## Decisions (confirmed 2026-11-23)
- [x] **V5.1** Profile lightly smoothed, like MST: GPS jitter removed, real
      climbs kept.
- [x] **V5.2** Numbered segment markers come in a later version, as their own spec.
- [x] **V5.3** Subtitle wording is chosen per trail at Gate 2.
