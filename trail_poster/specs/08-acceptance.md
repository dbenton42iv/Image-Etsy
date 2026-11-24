# 08 — Acceptance test: Benton MacKaye Trail

**Does one thing:** defines how we know v1 is done (D13).

## Setup
- A Benton MacKaye Trail GPX/KML with elevation, obtained under Gate 1.
- Official length and point list confirmed by David at Gate 2. (About 288 mi,
  Springer Mountain GA to Big Creek in the Smokies; David confirms the exact figure.)

## Pass criteria
- [ ] Banner layout with an elevation profile renders without label collisions.
- [ ] The same trail also renders in the vertical layout (proves both layouts, D9).
- [ ] Table starts at 0.0 and ends at the confirmed official length.
- [ ] All 6 print sizes exist in staging at 300 dpi with a 7% margin.
- [ ] David, viewing it next to Art Loeb and MST, says it belongs to the same set.
- [ ] No network calls were made by the tool during the run.
- [ ] Files reach `4_Print_Sizes` only after Gate 4.

## Decisions (confirmed 2026-11-23)
- [x] **V8.1** Full trail, Springer Mountain → Big Creek, mileage from the south end.
- [x] **V8.2** David alone signs off; his yes at Gate 3 is the sign-off.
