"""Spec 03 checks. Run:  python tests/test_points.py

Uses the same synthetic trail as test_input.py (no real data, nothing downloaded),
plus extra waypoints: one 0.3 mi off trail (flagged) and one 3 mi off (dropped).
"""
import csv, json, re, subprocess, sys, tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tests"))
import tp_input as ti        # noqa: E402
import tp_points as tp       # noqa: E402
from test_input import reference_line, build_segments, write_gpx   # noqa: E402

results = []

def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' - ' + str(detail)) if detail else ''}")

def make_project(td, name="proj"):
    ref = reference_line()
    segs, wpts = build_segments(ref)
    wpts = wpts + [("Rabun Bald", ref[1000] + [0, 0, 0]),                         # peak, has elevation
                   ("Overlook Spur Viewpoint", ref[1600] + [0.0, -0.012, 0]),     # 0.62 mi off trail
                   ("Far Away Lake", ref[1600] + [0.0, 0.06, 0])]                 # ~3 mi off trail
    gpx = td / f"{name}.gpx"
    write_gpx(gpx, segs, wpts)
    proj = td / name
    ti.save_track(ti.read_trail(gpx), proj)
    return proj, ref

def rows_by_name(P):
    return {r["name"].strip().upper(): r for r in P["rows"]}

def set_row(proj, row_name, **changes):
    rows = tp.read_pois(proj)
    for r in rows:
        if r["name"].strip().upper() == row_name:
            r.update(changes)
    tp.write_pois(proj, rows)

def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        proj, ref = make_project(td)
        track_mi = ti.cum_miles(ti.main_points(ti.load_track(proj)["main"]))[-1]

        # --- 2% length check (V3.1)
        far = round(track_mi * 1.05, 1)
        try:
            tp.draft(proj, far, "Camp Daniel Boone", "Davidson River"); stopped = False
        except tp.LengthMismatch as e:
            stopped = True; msg = str(e)
        check("Draft stops when official length is 5% off the track", stopped and not (proj / "pois.csv").exists(),
              msg[:90] + "..." if stopped else "did not stop")
        near = round(track_mi * 1.015, 1)
        cfg = tp.draft(proj, near, "Camp Daniel Boone", "Davidson River", title="Test Trail")
        check("Draft proceeds when 1.5% off (inside 2%)", (proj / "pois.csv").exists(),
              f"scale {cfg['length_check']['scale_factor']}")
        proj2, _ = make_project(td, "proj2")
        cfg2 = tp.draft(proj2, far, "A", "B", accept_length_diff=True)
        check("--accept-length-diff drafts and records that David accepted it",
              cfg2["length_check"]["accepted_by_david"] is True)

        # --- start/end and scaling (D8)
        P = tp.compute_points(proj)
        start = next(r for r in P["rows"] if r["type"] == "start")
        end = next(r for r in P["rows"] if r["type"] == "end")
        check("Start is exactly 0.0 and end is exactly the official total",
              start["_mile"] == 0.0 and end["_mile"] == near and end["_left"] == 0.0,
              f"start {start['_mile']}, end {end['_mile']} vs official {near}")
        k = near / track_mi
        ref_cum = ti.cum_miles(ref)
        dg = rows_by_name(P)["DEEP GAP"]
        expect = ref_cum[700] * k
        check("A waypoint's mile is its distance along the trail x scale factor (+-0.15 mi)",
              abs(dg["_mile"] - expect) < 0.15, f"{dg['_mile']} vs {expect:.2f}")
        check("Miles from start + miles to end = official total for every row",
              all(abs(r["_mile"] + r["_left"] - near) < 0.051 for r in P["rows"]))

        # --- draft contents: only file waypoints (D7), types, elevation, off-trail
        names = [r["name"] for r in tp.read_pois(proj)]
        check("Draft rows are start, end and the file's waypoints only",
              set(names) == {"CAMP DANIEL BOONE", "DAVIDSON RIVER", "DEEP GAP", "BUTTER GAP SHELTER",
                             "RABUN BALD", "OVERLOOK SPUR VIEWPOINT"}, names)
        check("Waypoint 3 mi off trail is left out and listed",
              any("FAR AWAY LAKE" in d.upper() for d in tp.read_cfg(proj)["dropped_waypoints"]))
        text, warn = tp.review(proj)
        check("Waypoint 0.3 mi off trail is flagged at review", any("OVERLOOK SPUR" in w.upper() and "off the trail" in w for w in warn))
        check("CSV has exactly the spec's 10 columns",
              list(csv.reader(open(proj / "pois.csv", encoding="utf-8")))[0] == tp.POI_FIELDS)
        guesses = {n: tp.guess_type(n) for n in ["Cold Mountain", "Mt. Mitchell", "Rabun Bald", "Tennent Mountain",
                   "Deep Gap", "Butter Gap Shelter", "Deep Gap Shelter", "Looking Glass Falls",
                   "Davidson River Campground", "FS 475 Trailhead", "Pisgah Inn", "Shining Rock Gap"]}
        expected = {"Cold Mountain": "peak", "Mt. Mitchell": "peak", "Rabun Bald": "peak", "Tennent Mountain": "peak",
                    "Deep Gap": "gap", "Butter Gap Shelter": "shelter", "Deep Gap Shelter": "shelter",
                    "Looking Glass Falls": "waterfall", "Davidson River Campground": "camp",
                    "FS 475 Trailhead": "trailhead", "Pisgah Inn": "point", "Shining Rock Gap": "gap"}
        wrong = {n: g for n, g in guesses.items() if g != expected[n]}
        check("Type guesses from names", not wrong, wrong or "12/12")
        check("GPX symbol hint is used too", tp.guess_type("Ivestor", "Summit") == "peak")

        # --- elevation on any point that has one (V3.3)
        set_row(proj, "DEEP GAP", elev_ft="5000")
        set_row(proj, "BUTTER GAP SHELTER", elev_ft="")       # David blanks an elevation to hide it
        P = tp.compute_points(proj); rb = rows_by_name(P)
        check("Gap with elevation is labeled NAME 5000'", tp.label_text(rb["DEEP GAP"]) == "DEEP GAP 5000'",
              tp.label_text(rb["DEEP GAP"]))
        check("Point without elevation has a plain label", tp.label_text(rb["BUTTER GAP SHELTER"]) == "BUTTER GAP SHELTER")
        check("Label override wins", tp.label_text(dict(name="X", label="Road Walk", elev_ft="100")) == "ROAD WALK")

        # --- changing one row changes only that row
        before = {n: (r["_mile"], tp.label_text(r)) for n, r in rows_by_name(tp.compute_points(proj)).items()}
        set_row(proj, "RABUN BALD", elev_ft="4696")
        after = {n: (r["_mile"], tp.label_text(r)) for n, r in rows_by_name(tp.compute_points(proj)).items()}
        changed = [n for n in before if before[n] != after[n]]
        check("Editing one row in pois.csv changes only that row's label", changed == ["RABUN BALD"], changed)

        # --- >20 labels warning (V3.2)
        rows = tp.read_pois(proj)
        extra = [dict(show="y", table="y", name=f"EXTRA {i}", type="point", mile="", lat=round(ref[100 + i * 100, 0], 6),
                      lon=round(ref[100 + i * 100, 1], 6), elev_ft="", side="auto") for i in range(16)]
        tp.write_pois(proj, rows + extra)
        check("More than 20 labels triggers a warning", any("labels on the map" in w for w in tp.review(proj)[1]))
        tp.write_pois(proj, rows)

        # --- reverse direction
        cfg = tp.read_cfg(proj); cfg["reverse"] = True; tp.write_cfg(proj, cfg)
        Pr = tp.compute_points(proj); rr = rows_by_name(Pr)
        fwd = rows_by_name(tp.compute_points(proj, dict(cfg, reverse=False)))
        check("Reverse: start 0.0, end official, and a midpoint's mile flips",
              next(r for r in Pr["rows"] if r["type"] == "start")["_mile"] == 0.0
              and abs(rr["DEEP GAP"]["_mile"] - (near - fwd["DEEP GAP"]["_mile"])) < 0.15,
              f"{fwd['DEEP GAP']['_mile']} -> {rr['DEEP GAP']['_mile']}")
        cfg["reverse"] = False; tp.write_cfg(proj, cfg)

        # --- Gate 2: approval
        render = [sys.executable, str(HERE / "trail_poster.py"), "render", str(proj)]
        r = subprocess.run(render, capture_output=True, text=True)
        check("Renderer refuses before Gate 2", r.returncode != 0 and "NOT APPROVED" in (r.stderr + r.stdout),
              (r.stderr + r.stdout).strip()[:80])
        try:
            tp.approve(proj, "banner", "landscape"); ok = False
        except ValueError:
            ok = True
        check("Banner approval refused without a subtitle", ok)
        try:
            tp.approve(proj, "banner", "portrait"); ok = False
        except ValueError:
            ok = True
        check("Banner + portrait refused", ok)
        tp.approve(proj, "vertical", "landscape")
        check("Approved after approve()", tp.is_approved(proj), tp.approval_status(proj))
        check("Approval records the confirmed layout and orientation",
              tp.read_cfg(proj)["template"] == "vertical" and tp.read_cfg(proj)["orientation"] == "landscape")
        set_row(proj, "DEEP GAP", name="DEEP GAP NORTH")
        check("Editing pois.csv after approval cancels it", not tp.is_approved(proj), tp.approval_status(proj))
        tp.approve(proj, "vertical", "landscape")
        cfg = tp.read_cfg(proj); cfg["subtitle"] = "CHANGED"; tp.write_cfg(proj, cfg)
        check("Editing the title/subtitle/length after approval cancels it", not tp.is_approved(proj))
        try:
            tp.draft(proj, near, "A", "B"); ok = False
        except FileExistsError:
            ok = True
        check("Draft never overwrites an edited pois.csv", ok)

    pat = re.compile(r"urllib|requests|http|socket|overpass|openstreetmap", re.I)
    hits = [n for n, line in enumerate((HERE / "tp_points.py").read_text(encoding="utf-8").splitlines(), 1) if pat.search(line)]
    check("No network code in tp_points.py", not hits, hits)

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
