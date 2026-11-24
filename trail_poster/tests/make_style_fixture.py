"""Build a local style-test project for the vertical layout (spec 04).

The trail line is synthetic (no real trail data, nothing downloaded). The labels
are the points and mileages printed on David's own Art Loeb poster, placed by
mile, so the result can be compared side by side with that poster.

    python tests/make_style_fixture.py      -> output/_style_test_vertical/

This is a TEST project: it is auto-approved so it can render. Real posters are
approved only by David at Gate 2.
"""
import shutil, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import tp_input as ti, tp_points as tp   # noqa: E401,E402

OUT = HERE / "output" / "_style_test_vertical"

ART_LOEB = [  # mile, name, type, elev (from the Art Loeb poster)
    (0.0, "CAMP DANIEL BOONE", "start", "3267"),
    (3.8, "DEEP GAP", "shelter", "5000"),
    (6.4, "SHINING ROCK GAP", "shelter", "5775"),
    (8.4, "IVESTOR GAP", "gap", ""),
    (9.0, "TENNENT MOUNTAIN", "peak", "6040"),
    (14.3, "DEEP GAP SHELTER", "shelter", ""),
    (15.0, "PILOT MOUNTAIN", "peak", "5084"),
    (17.8, "FS 475", "point", ""),
    (21.5, "BUTTER GAP SHELTER", "shelter", ""),
    (23.9, "CAT GAP", "gap", ""),
    (30.1, "DAVIDSON RIVER", "end", "2147"),
]

def synthetic_trail(n=4000, seed=7):
    """A wandering, jaggy ~30 mi line: north-south first half, then east."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, n)
    lat = 35.38 - 0.20 * np.clip(t * 1.6, 0, 1) + 0.012 * np.sin(t * 31)
    lon = -82.86 + 0.02 * np.sin(t * 9) + 0.16 * np.clip((t - 0.62) / 0.38, 0, 1) ** 1.3
    noise = rng.normal(0, 1, (n + 40, 2))
    noise = np.column_stack([np.convolve(noise[:, i], np.ones(40) / 40, mode="valid")[:n] for i in (0, 1)])
    jag = np.cumsum(noise, axis=0)
    jag -= np.linspace(0, 1, n)[:, None] * jag[-1]          # keep the ends where they are
    lat += jag[:, 0] * 0.0006; lon += jag[:, 1] * 0.0006
    ele = 1000 + 700 * np.exp(-((t - 0.2) / 0.15) ** 2) + 300 * np.sin(t * 13) ** 2
    return np.column_stack([lat, lon, ele])

def main():
    if OUT.exists():   # clear files, keep the folder (OneDrive can lock folders)
        for p in sorted(OUT.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            else:
                shutil.rmtree(p, ignore_errors=True)
    pts = synthetic_trail()
    gpx = HERE / "tests" / "_style_trail.gpx"
    w = ['<?xml version="1.0"?>', '<gpx version="1.1" creator="test" xmlns="x-test-namespace">',
         "<metadata><name>Test Trail</name></metadata><trk><name>Test Trail</name><trkseg>"]
    w += [f'<trkpt lat="{a:.6f}" lon="{b:.6f}"><ele>{c:.1f}</ele></trkpt>' for a, b, c in pts]
    w.append("</trkseg></trk></gpx>")
    gpx.write_text("\n".join(w), encoding="utf-8")
    trail = ti.read_trail(gpx)
    ti.save_track(trail, OUT)
    track_mi = trail["report"]["main_length_mi"]
    tp.draft(OUT, track_mi, "Camp Daniel Boone", "Davidson River", title="Test Trail", accept_length_diff=True)
    rows = [dict(show="y", table="y", name=n, type=typ, mile=m, lat="", lon="", elev_ft=e, side="auto")
            for m, n, typ, e in ART_LOEB]
    tp.write_pois(OUT, rows)
    cfg = tp.read_cfg(OUT); cfg["total_miles"] = 30.1; cfg["length_check"]["accepted_by_david"] = True
    cfg["test_fixture"] = "synthetic line, Art Loeb labels - not a real poster"
    tp.write_cfg(OUT, cfg)
    tp.approve(OUT, "vertical", "landscape")
    print(tp.review(OUT)[0])
    print(f"\nStyle-test project: {OUT}")

if __name__ == "__main__":
    main()
