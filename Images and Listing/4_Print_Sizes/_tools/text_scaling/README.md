# Per-size text scaling (Bartram, Art Loeb, Mountains-to-Sea)

Builds the print files from the vector masters in `_Masters_2026`, enlarging the mileage
table and copyright line per file so they read at ~6 pt / ~5 pt at the smallest print each
file is sold for, without overlapping the trail or labels.

- `lay.py`    splits each master's traced paths and finds the mileage-table region
- `table.py`  column/row-aware table re-layout (glyph scale f, column gaps, leading) + collision search
- `plan.py`   per-candidate layout, copyright placement, text size at each file's smallest print
- `final.py`  chosen scale per file (CHOICE), home-print darkening, margin fit (printable-margins rule)
- `gen_all.py` writes drop-ship and _Home_Print JPGs

Paths in the scripts point at a staged copy of this folder; adjust before re-running.
