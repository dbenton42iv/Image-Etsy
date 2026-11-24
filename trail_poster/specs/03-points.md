# 03 — Points of interest and mileage

**Does one thing:** builds the editable list of labeled points and the mileage
table data, then stops for David's approval (Gate 2).

## In
- The track and waypoints from `01-input`.
- From David: official total length (D8), missing names and elevations, and
  the start and end names.

## Out
- `pois.csv`, one row per point:
  `show, table, name, label, type, mile, lat, lon, elev_ft, side`
  - `type`: start, end, peak, gap, shelter, camp, waterfall, trailhead, point
  - `label`: optional override of the map text
  - `side`: auto / left / right
- `poster.json`: title, subtitle, `total_miles`, layout, `reverse`, year.

## Rules
- Draft rows come **only** from file waypoints plus David's input (D7). No
  online lookup.
- Waypoint type is guessed from its name or symbol (shelter, falls, bald,
  knob, gap...). David corrects it in review.
- Mile = distance along the track to the nearest point, then **scaled** by
  `official_total / track_total` (D8). Start = 0.0, end = official total.
- Any point with `elev_ft` filled in shows it on the map (`NAME 5062'`),
  whatever its type; blank it to hide. The table shows names without elevation.
- If the measured track and official length differ by **more than 2%**, Claude
  stops and flags it before drafting points (likely a wrong or partial file).
- More than **20** labels shown → Claude warns that the map may be crowded.
- Gate 2 also confirms the **layout** (vertical or banner), **orientation**
  (portrait is only suggested, never automatic) and, for the banner layout,
  the **subtitle wording**, which Claude proposes to fit each trail.
- Table columns: miles from start | POINT OF INTEREST | miles to end, as on
  Art Loeb.
- **Gate 2:** Claude shows the list as a readable table (mile, name, type,
  elevation, map yes/no, table yes/no) and the scale factor. Nothing renders
  until David says yes.

## Done when
- [x] Start and end are 0.0 and the official total exactly.
- [x] Changing one row in `pois.csv` changes only that row's mileage and label
      (checked at the data level; on the rendered map, neighbouring labels may
      shift to make room. That's checked again in spec 04/05).

Verified 2026-11-23 by `python tests/test_points.py` (27/27 pass) on the
synthetic trail from spec 01. No real trail data used yet.

## Built
- `tp_points.py`, three commands:
  - `draft <project> --official-miles N --start "..." --end "..."`: stops if the
    track is more than 2% off (`--accept-length-diff` only after David agrees);
    never overwrites an existing `pois.csv`.
  - `review <project>`: the Gate 2 table, plus warnings (over 20 labels, peaks
    without elevation, points off the trail, duplicates, missing banner subtitle).
  - `approve <project> --layout vertical|banner --orientation landscape|portrait`:
    records Gate 2. Any later edit to `pois.csv`, or to the title, subtitle, length,
    layout, orientation or direction, cancels the approval.
- `trail_poster.py render` refuses to run until Gate 2 is approved. Its own
  mileage code was removed; it uses `tp_points.compute_points`.
- Waypoints more than 1 mi off the trail are left out and listed; those over
  0.25 mi are flagged.
- `poster.json` keeps `reverse`: mileage counted from the other end.

## Draft look before Gate 2 (added 2026-11-23, at David's request)
`python trail_poster.py render <project> --draft` writes only `draft_preview.png`,
stamped DRAFT / not approved / not for sale, using the suggested layout. It never
writes masters or print files; those still need Gate 2.

## Note for Gate 2
Elevations in GPX/KML waypoints come along automatically, so by default most
labels show one. Blank `elev_ft` on any row to hide it (V3.3).

## Decisions (confirmed 2026-11-23)
- [x] **V3.1** Flag when the track and official length differ by more than 2%.
      (Strict: twisty trails may trip it from GPS noise alone. Claude explains
      which case it is when it flags.)
- [x] **V3.2** Up to 20 labels; Claude warns above that.
- [x] **V3.3** Elevation shows on any point that has one.
