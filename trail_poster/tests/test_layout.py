"""Spec 04 layout checks. Run:  python tests/test_layout.py

Builds the style-test project (synthetic line, Art Loeb labels, titled TEST TRAIL)
and checks the vertical layout for collisions:
  - no label overlaps another label, the table, the title band or the page edge
  - no label text crosses the trail line
  - the tool reports a problem when a label can't be placed (forced bad case)
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import trail_poster as T, tp_points as tp   # noqa: E401,E402

results = []

def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' - ' + str(detail)) if detail else ''}")

def main():
    subprocess.run([sys.executable, str(HERE / "tests" / "make_style_fixture.py")], check=True, capture_output=True)
    proj = HERE / "output" / "_style_test_vertical"
    P = T.Poster(proj)
    rects = [(P.rows[i]["name"], g["rect"], g["text_rect"]) for i, g, _ in P.labels]
    pairs = [(a[0], b[0]) for n, a in enumerate(rects) for b in rects[n + 1:] if T.rects_overlap(a[1], b[1])]
    check("No two labels overlap", not pairs, pairs)
    hit_obs = [n for n, r, _ in rects if any(T.rects_overlap(r, o) for o in P.obstacles)]
    check("No label overlaps the table, title band or (c) line", not hit_obs, hit_obs)
    b = P.bounds
    out = [n for n, r, _ in rects if r[0] < b[0] or r[1] < b[1] or r[2] > b[2] or r[3] > b[3]]
    check("Every label is inside the page", not out, out)
    cross = [n for n, _, tr in rects if T.pts_in(tr, P.trail_pts, 0.0)]
    check("No label text crosses the trail", not cross, cross)
    check("Every shown point got a label", len(P.labels) == len(P.rows), f"{len(P.labels)}/{len(P.rows)}")
    check("Tool reports no warnings", not P.warnings, P.warnings)
    tr = P.table_rect
    trail_in_table = T.pts_in(tr, P.trail_pts, 0.0)
    check("Trail line stays out of the mileage table", trail_in_table == 0, trail_in_table)

    # forced bad case: a very long label pinned to the crowded side must be reported, not hidden
    rows = tp.read_pois(proj)
    for r in rows:
        if r["name"] == "IVESTOR GAP":
            r["label"] = "IVESTOR GAP AND A VERY LONG LABEL THAT CANNOT POSSIBLY FIT ANYWHERE NICE"; r["side"] = "left"
    tp.write_pois(proj, rows)
    P2 = T.Poster(proj)
    check("An unplaceable label is reported as a warning", any("IVESTOR GAP" in w for w in P2.warnings), P2.warnings[:1])
    subprocess.run([sys.executable, str(HERE / "tests" / "make_style_fixture.py")], check=True, capture_output=True)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
