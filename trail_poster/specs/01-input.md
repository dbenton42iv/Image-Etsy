# 01 — Input: read a local trail file

**Does one thing:** turns a local GPX, KML or KMZ file into one ordered trail line
plus a list of waypoints. No network access (D4).

## In
- A file path: `.gpx`, `.kml` or `.kmz`.

## Out
- `track.json` in the project folder:
  - `main`: ordered pieces of the trail (lat, lon, elevation or null); a piece is
    `dashed` if its name contains road, ferry, walk or alt.
  - `extras`: disconnected bits (side trails, alternates), always drawn dashed.
- A waypoint list (name, lat, lon, elevation, type hint) passed to `03-points`.

## Rules
- Reads GPX tracks, routes and waypoints; KML LineString, gx:Track and Point.
- Joins segments end to end when the ends are within 0.5 mi; the longest joined
  chain is the main trail.
- Elevation in meters is kept as-is here; feet conversion happens later.

## Done when
- [x] Parses one GPX and one KML of the same trail to the same length (±1%).
- [x] A multi-segment file comes out as one main line, in order.
- [x] Grepping the code for `urllib`, `requests`, `http` finds nothing.

Verified 2026-11-23 by `python tests/test_input.py` (13/13 pass) on a synthetic
trail: GPX, KML and KMZ, 5 out-of-order segments (one reversed), a bridged
0.15 mi gap, a dashed "Road Walk", and a spur over 0.5 mi away kept as a
separate dashed piece. No real trail data used yet.

## Built
- `tp_input.py`: reading, joining, `track.json` / `waypoints.json`, report.
  Run alone: `python tp_input.py <file> --out <project>`.
- `trail_poster.py`: all OpenStreetMap / network code removed; `new` takes
  `--file` only.
- Trail name: the file's own name (GPX metadata / KML Document) wins; a
  segment name is used only when every segment shares it.

## Decisions (confirmed 2026-11-23)
- [x] **V1.1** Gaps under 0.5 mi are joined; larger gaps start a separate piece,
      drawn dashed.
- [x] **V1.2** Pieces named road / ferry / walk / alt are dashed automatically;
      David can override any piece at Gate 2.
