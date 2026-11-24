# 02 — Data sourcing: getting a GPX/KML file

**Does one thing:** sets the rules for how Claude gets a trail file. This is a
Claude-behavior spec, not code. The tool itself never downloads anything (D4).

## Rules
1. If David gives a file path, use it. No gate needed.
2. If Claude finds a file online (D6), **before downloading** it posts:
   - the source site and the exact file URL,
   - the file name and approximate size,
   - a short quote from the site's terms of use or license that allows reuse
     in a commercial product, with a link to those terms.
3. **Gate 1:** Claude waits for David's explicit "yes". No yes, no download.
4. If the terms are unclear or silent on commercial use, Claude says so and
   does not use the source. **Sources that require attribution are off-limits**
   (V2.1): posters carry only the Beech Creek Naturals line. Claude never
   guesses that something is allowed.
5. Downloaded files go to `trail_poster/sources/<Trail>/`, next to a
   `SOURCE.md` that records the URL, the date, the terms quote and David's OK.
6. Only the trail geometry is taken from the source. The map is always drawn
   by the local tool.

## Done when
- [ ] Every project built from a downloaded file has a `SOURCE.md`.
- [ ] No download happens without a recorded "yes".

## Exceptions
- **Benton MacKaye Trail (2026-11-23):** David chose to use an OpenStreetMap (ODbL)
  file with no credit line, after being told the license asks for one. Recorded in
  `sources/Benton_MacKaye_Trail/SOURCE.md`. The V2.1 rule still applies to other trails.

## Decisions (confirmed 2026-11-23)
- [x] **V2.1** Sources that require attribution are off-limits.
- [x] **V2.2** Downloads and `SOURCE.md` go in `trail_poster/sources/<Trail>/`.
