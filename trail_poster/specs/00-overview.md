# Trail Poster Tool — Overview

## Real goal
Let David make **new trail-map designs for fixed Etsy listings** faster, in the
existing Beech Creek Naturals house style (Art Loeb, Bartram, Mountains-to-Sea).
The user asks Claude ("make a poster for the Benton MacKaye Trail"); Claude runs a
local tool and stops at approval gates. Output is **print-ready 300 dpi JPGs**
with no hand editing.

## Not in scope (v1)
- Customer custom or personalized orders.
- Adding listings to `build_listings.py` (see `later/listings.md`).
- Any map drawn, rendered or styled by an outside website or map service.

## Decision log (each confirmed by David, 2026-11-23)
| # | Decision | Answer |
|---|---|---|
| D1 | Who it's for | David, making catalog listings |
| D2 | Output finish | Print-ready JPGs, all sizes, 300 dpi |
| D3 | How it's run | A Claude Code skill, by asking Claude |
| D4 | Outside websites | **Maps are never generated on other websites.** The tool has **no network code**. |
| D5 | Trail data source | GPX/KML can come from outside sites **only if their terms of use allow it** |
| D6 | Who fetches data | Claude may download, after naming the source, quoting its terms and getting David's OK |
| D7 | Labels and elevations | Waypoints in the file plus what David supplies; nothing is looked up online |
| D8 | Mileage | David gives the official total; all mileages are scaled proportionally to match it |
| D9 | Layouts | Both from the start: vertical title (Art Loeb/Bartram) **and** banner with elevation profile (MST) |
| D10 | Fonts | Keep the local Montserrat and Source Sans 3 (OFL) in `trail_poster/fonts` |
| D11 | Output location | Staging at `trail_poster/output/<Trail>/` first |
| D12 | Approval gates | (1) data source, (2) point list, (3) preview, (4) copy to `4_Print_Sizes` |
| D13 | v1 acceptance test | A brand-new trail: **Benton MacKaye Trail** |
| D14 | Listings integration | Later, as its own spec |
| D15 | Spec format | One small markdown file per component, here |

All component-level decisions (V1.1–V8.2) were confirmed on 2026-11-23 and are
recorded in each spec. Deferred to later specs: numbered segment markers (V5.2)
and listings (D14). Rejected: attribution-required sources (V2.1), trail-map
stickers (V6.2).

## Components (each spec stands alone)
1. `01-input.md` — read local GPX/KML/KMZ into one ordered track
2. `02-data-sourcing.md` — rules for Claude downloading trail files
3. `03-points.md` — point list CSV, official-length scaling, gate 2
4. `04-layout-vertical.md` — Art Loeb / Bartram layout
5. `05-layout-banner.md` — MST layout with elevation profile
6. `06-print-output.md` — sizes, margins, staging, gate 4
7. `07-skill.md` — the Claude workflow tying it together
8. `08-acceptance.md` — Benton MacKaye test
- `later/listings.md` — Etsy CSV integration (deferred)

## Existing draft code
`trail_poster.py` was drafted before this interview. It **must be changed** to meet
D4 and D7: remove every OpenStreetMap / Overpass function and all `urllib` use.
Nothing has been rendered yet.
