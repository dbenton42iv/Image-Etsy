"""Spec 01 checks. Run:  python tests/test_input.py

Builds a synthetic ~30 mi trail (no real trail data, nothing downloaded) and
writes it as GPX, KML and KMZ with the awkward cases real files have:
  - the trail split into 5 segments, stored out of order, one stored backwards
  - a 0.2 mi recording gap (must be bridged)
  - a segment named "Road Walk" (must be dashed)
  - a 1.5 mi-away spur (gap > 0.5 mi: must become a separate dashed piece)
  - two waypoints
Then checks every "Done when" box in specs/01-input.md.
"""
import re, sys, tempfile, zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import tp_input as ti  # noqa: E402


def reference_line(n=3000):
    t = np.linspace(0, 1, n)
    lat = 35.30 + 0.35 * t + 0.02 * np.sin(t * 40)
    lon = -82.90 + 0.12 * np.sin(t * 6) + 0.01 * np.cos(t * 55)
    ele = 900 + 600 * np.sin(t * 9) ** 2
    return np.column_stack([lat, lon, ele])


def build_segments(ref):
    cuts = [0, 600, 1200, 1800, 2400, len(ref)]
    segs = [ref[a:b + 1] for a, b in zip(cuts[:-1], cuts[1:])]
    segs[1] = segs[1][1:]                       # tiny join gap
    segs[2] = segs[2][12:]                      # ~0.2 mi recording gap
    names = ["Section 1", "Section 2", "Section 3", "Road Walk", "Section 5"]
    order = [3, 0, 4, 2, 1]                     # stored out of order
    out = []
    for i in order:
        pts = segs[i][::-1] if i == 4 else segs[i]   # one stored backwards
        out.append((names[i], pts))
    spur_start = ref[1500] + np.array([0.0, 0.03, 0])      # ~1.5 mi east of the trail
    spur = np.array([spur_start + [k * 0.001, k * 0.0005, 0] for k in range(40)])
    out.append(("Spur to Overlook", spur))
    wpts = [("Deep Gap", ref[700]), ("Butter Gap Shelter", ref[2100])]
    return out, wpts


def write_gpx(path, segs, wpts):
    w = ['<?xml version="1.0"?>', '<gpx version="1.1" creator="test" xmlns="x-test-namespace">',
         "<metadata><name>Test Trail</name></metadata>"]
    for name, p in wpts:
        w.append(f'<wpt lat="{p[0]}" lon="{p[1]}"><ele>{p[2]}</ele><name>{name}</name></wpt>')
    for name, pts in segs:
        w.append(f"<trk><name>{name}</name><trkseg>")
        w += [f'<trkpt lat="{a}" lon="{b}"><ele>{c}</ele></trkpt>' for a, b, c in pts]
        w.append("</trkseg></trk>")
    w.append("</gpx>")
    path.write_text("\n".join(w), encoding="utf-8")


def kml_text(segs, wpts):
    w = ['<?xml version="1.0"?>', '<kml xmlns="x-test-namespace"><Document><name>Test Trail</name>']
    for name, p in wpts:
        w.append(f"<Placemark><name>{name}</name><Point><coordinates>{p[1]},{p[0]},{p[2]}</coordinates></Point></Placemark>")
    for name, pts in segs:
        coords = " ".join(f"{b},{a},{c}" for a, b, c in pts)
        w.append(f"<Placemark><name>{name}</name><LineString><coordinates>{coords}</coordinates></LineString></Placemark>")
    w.append("</Document></kml>")
    return "\n".join(w)


results = []

def check(label, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' - ' + detail) if detail else ''}")


def main():
    ref = reference_line()
    ref_len = ti.cum_miles(ref)[-1]
    segs, wpts = build_segments(ref)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        gpx, kml, kmz = td / "t.gpx", td / "t.kml", td / "t.kmz"
        write_gpx(gpx, segs, wpts)
        kml.write_text(kml_text(segs, wpts), encoding="utf-8")
        with zipfile.ZipFile(kmz, "w") as z:
            z.writestr("doc.kml", kml_text(segs, wpts))

        g, k, z = ti.read_trail(gpx), ti.read_trail(kml), ti.read_trail(kmz)
        print(ti.format_report(g["report"]), "\n")
        lg, lk, lz = (t["report"]["main_length_mi"] for t in (g, k, z))

        # Done when 1: GPX and KML of the same trail give the same length (+-1%)
        check("GPX, KML and KMZ lengths agree within 1%",
              abs(lg - lk) / lg < 0.01 and abs(lg - lz) / lg < 0.01, f"GPX {lg}, KML {lk}, KMZ {lz} mi")
        check("Main length matches the reference trail within 1%",
              abs(lg - ref_len) / ref_len < 0.01, f"{lg} vs reference {ref_len:.2f} mi")

        # Done when 2: multi-segment file comes out as one main line, in order
        for label, t in (("GPX", g), ("KML", k)):
            pts = ti.main_points(t["main"])
            idx = np.array([int(np.argmin((ref[:, 0] - a) ** 2 + (ref[:, 1] - b) ** 2)) for a, b, _ in pts[::5]])
            d = np.diff(idx)
            mono = (d >= -2).all() or (d <= 2).all()
            check(f"{label}: 5 out-of-order segments joined into one ordered main line",
                  len(t["main"]) == 5 and mono, f"{len(t['main'])} pieces, ordered={mono}")
        check("0.2 mi gap was bridged", any(0.1 < x < 0.5 for x in g["report"]["gaps_bridged_mi"]),
              f"bridged {g['report']['gaps_bridged_mi']}")
        check("Spur more than 0.5 mi away became a separate dashed piece",
              g["report"]["extra_pieces"] == 1 and all(p["dashed"] for p in g["extras"]))
        check("'Road Walk' piece is dashed, other main pieces solid",
              [p["name"] for p in g["main"] if p["dashed"]] == ["Road Walk"])
        check("Elevation read", g["report"]["elevation_coverage"] == 1.0)
        check("Both waypoints read (GPX and KML)", len(g["waypoints"]) == 2 and len(k["waypoints"]) == 2)

        # track.json round trip
        ti.save_track(g, td / "proj")
        back = ti.load_track(td / "proj")
        a, b = ti.main_points(back["main"]), ti.main_points(g["main"])
        check("track.json round-trips (lat/lon to 6 places, elevation to 0.1 m)",
              np.allclose(a[:, :2], b[:, :2], atol=1e-6) and np.allclose(a[:, 2], b[:, 2], atol=0.051)
              and [p["dashed"] for p in back["main"]] == [p["dashed"] for p in g["main"]])
        check("Trail name comes from the file's own name, not the first segment",
              g["name"] == "Test Trail" and k["name"] == "Test Trail", f"GPX '{g['name']}', KML '{k['name']}'")

        # bad input is rejected cleanly
        bad = td / "bad.txt"; bad.write_text("hello")
        try:
            ti.read_trail(bad); ok = False
        except ValueError:
            ok = True
        check("Non-trail file is rejected with a clear error", ok)

    # Done when 3: no network code anywhere in the tool
    pat = re.compile(r"urllib|requests|http|socket|overpass|openstreetmap", re.I)
    hits = [f"{p.name}:{n}" for p in (HERE / "tp_input.py", HERE / "trail_poster.py")
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pat.search(line)]
    check("No network code in tp_input.py or trail_poster.py", not hits, ", ".join(hits))

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
