# 07 — Claude skill: "make a trail poster"

**Does one thing:** the Claude Code skill that runs specs 01–06 in order, with
the four gates. Lives at `Etsy/.claude/skills/trail-poster/SKILL.md`.

## Trigger
Requests like "make a poster for the ___ Trail" or "here's a GPX, make a poster."

## Flow
1. **Get the file.** A path from David, or a candidate download → **Gate 1**
   (`02-data-sourcing`).
2. **Read it** (`01-input`). Report the measured length, segment count and
   whether it has elevation.
3. **Ask David** for the official length, the start and end names, and any
   missing point names or elevations.
4. **Draft the points** (`03-points`) and suggest a layout → **Gate 2**: the point
   table, the layout and the scale factor.
5. **Preview** → Claude looks at it for collisions, then shows it → **Gate 3**.
   Edits loop back to 4 or 5.
6. **Render all sizes** to staging (`06-print-output`).
7. **Gate 4** → copy into `4_Print_Sizes`.

## Rules
- Each gate is a direct question with a clear yes; silence is not a yes.
- Claude never visits a map website to draw or style anything.
- Claude reports any unplaced labels or warnings instead of hiding them.

## Done when
- [ ] One full run on Benton MacKaye goes through all four gates in order.

## Decisions (confirmed 2026-11-23)
- [x] **V7.1** Skill name: `trail-poster` (`/trail-poster`).
