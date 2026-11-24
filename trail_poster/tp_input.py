#!/usr/bin/env python3
"""Spec 01 - Input: read a local GPX / KML / KMZ file into one ordered trail.

Local files only. This module has no network code (spec 00, D4).

    python tp_input.py "C:/path/trail.gpx" --out output/My_Trail

Writes <out>/track.json and <out>/waypoints.json and prints a short report.
"""
import argparse, json, math, re, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

JOIN_GAP_MI = 0.5          # V1.1: gaps under this are bridged
DASH_RE = re.compile(r"\b(road|ferry|walk|alt|alternate)\b", re.I)   # V1.2
R_MI = 3958.8

# ------------------------------------------------------------------ distance
def hav_miles(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    dla, dlo = np.diff(la), np.diff(lo)
    a = np.sin(dla / 2) ** 2 + np.cos(la[:-1]) * np.cos(la[1:]) * np.sin(dlo / 2) ** 2
    return 2 * R_MI * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

def cum_miles(pts):
    if len(pts) < 2:
        return np.zeros(len(pts))
    return np.concatenate([[0.0], np.cumsum(hav_miles(pts[:, 0], pts[:, 1]))])

def point_gap(p, q):
    return float(hav_miles(np.array([p[0], q[0]]), np.array([p[1], q[1]]))[0])

# ------------------------------------------------------------------ XML helpers
def _ln(tag):
    return tag.rsplit("}", 1)[-1]

def _child(el, name):
    for c in el:
        if _ln(c.tag) == name:
            return c
    return None

def _text(el, name):
    c = _child(el, name)
    return (c.text or "").strip() if c is not None and c.text else ""

def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return np.nan

# ------------------------------------------------------------------ GPX
def parse_gpx(data):
    root = ET.fromstring(data)
    segs, wpts = [], []
    md = next((e for e in root.iter() if _ln(e.tag) == "metadata"), None)
    name = _text(md, "name") if md is not None else ""     # the file's own name wins
    track_names = []
    for el in root.iter():
        t = _ln(el.tag)
        if t in ("trk", "rte"):
            tname = _text(el, "name")
            track_names.append(tname)
            groups = [g for g in el if _ln(g.tag) == "trkseg"] if t == "trk" else [el]
            for g in groups:
                pts = [(float(p.get("lat")), float(p.get("lon")), _num(_text(p, "ele")))
                       for p in g if _ln(p.tag) in ("trkpt", "rtept")]
                if len(pts) > 1:
                    segs.append({"name": tname, "pts": np.array(pts, float)})
        elif t == "wpt":
            e = _num(_text(el, "ele"))
            wpts.append({"name": _text(el, "name"), "lat": float(el.get("lat")), "lon": float(el.get("lon")),
                         "ele_m": None if np.isnan(e) else e,
                         "hint": " ".join(x for x in (_text(el, "type"), _text(el, "sym"), _text(el, "desc")) if x)})
    if not name and len(set(n for n in track_names if n)) == 1:   # one consistent track name
        name = next(n for n in track_names if n)
    return segs, wpts, name

# ------------------------------------------------------------------ KML / KMZ
def _kml_coords(txt):
    out = []
    for tok in (txt or "").split():
        v = tok.split(",")
        if len(v) >= 2:
            out.append((float(v[1]), float(v[0]), _num(v[2]) if len(v) > 2 else np.nan))
    return out

def parse_kml(data):
    root = ET.fromstring(data)
    segs, wpts = [], []
    doc = next((e for e in root.iter() if _ln(e.tag) == "Document"), None)
    name = _text(doc, "name") if doc is not None else ""
    for pm in (e for e in root.iter() if _ln(e.tag) == "Placemark"):
        pname = _text(pm, "name")
        for el in pm.iter():
            t = _ln(el.tag)
            if t == "LineString":
                c = _child(el, "coordinates")
                pts = _kml_coords(c.text if c is not None else "")
                if len(pts) > 1:
                    segs.append({"name": pname, "pts": np.array(pts, float)})
            elif t == "Track":   # gx:Track
                pts = []
                for c in el:
                    if _ln(c.tag) == "coord" and c.text:
                        v = c.text.split()
                        pts.append((float(v[1]), float(v[0]), _num(v[2]) if len(v) > 2 else np.nan))
                if len(pts) > 1:
                    segs.append({"name": pname, "pts": np.array(pts, float)})
            elif t == "Point":
                c = _child(el, "coordinates")
                pts = _kml_coords(c.text if c is not None else "")
                if pts:
                    lat, lon, e = pts[0]
                    wpts.append({"name": pname, "lat": lat, "lon": lon,
                                 "ele_m": None if np.isnan(e) or e == 0 else e,
                                 "hint": _text(pm, "description")[:60]})
    seg_names = set(s["name"] for s in segs if s["name"])
    if not name and len(seg_names) == 1:
        name = seg_names.pop()
    return segs, wpts, name

def load_file(path):
    """Return (segments, waypoints, name) from a local GPX, KML or KMZ file."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".kmz":
        with zipfile.ZipFile(path) as z:
            kml = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
            if kml is None:
                raise ValueError("KMZ contains no .kml file")
            return parse_kml(z.read(kml))
    data = path.read_bytes()
    if ext == ".kml" or b"<kml" in data[:4000]:
        return parse_kml(data)
    if ext == ".gpx" or b"<gpx" in data[:4000]:
        return parse_gpx(data)
    raise ValueError(f"Not a GPX, KML or KMZ file: {path.name}")

# ------------------------------------------------------------------ assembly
def _seg_len(s):
    return cum_miles(s["pts"])[-1]

def chain_segments(segs, tol_mi=JOIN_GAP_MI):
    """Join segments end to end when the gap is under tol_mi.

    The longest joined chain is the main trail; every other chain is an extra
    piece, always drawn dashed. Inside the main chain a piece is dashed when
    its name matches DASH_RE (road walk, ferry, alternate ...).
    Returns (main, extras, gaps_bridged) where pieces are {'pts', 'dashed', 'name'}.
    """
    pool = sorted(segs, key=_seg_len, reverse=True)
    chains, bridged = [], []
    while pool:
        chain = [pool.pop(0)]
        while pool:
            a, z = chain[0]["pts"][0], chain[-1]["pts"][-1]
            best = None
            for i, s in enumerate(pool):
                p0, p1 = s["pts"][0], s["pts"][-1]
                for d, where, rev in ((point_gap(z, p0), "end", False), (point_gap(z, p1), "end", True),
                                      (point_gap(a, p1), "start", False), (point_gap(a, p0), "start", True)):
                    if best is None or d < best[0]:
                        best = (d, i, where, rev)
            if best[0] > tol_mi:
                break
            d, i, where, rev = best
            s = dict(pool.pop(i))
            if rev:
                s["pts"] = s["pts"][::-1]
            if d > 0.01:
                bridged.append(round(d, 3))
            if where == "start":
                chain.insert(0, s)
            else:
                chain.append(s)
        chains.append(chain)
    if not chains:
        raise ValueError("No track or route lines found in the file.")
    chains.sort(key=lambda ch: sum(_seg_len(s) for s in ch), reverse=True)
    main = [{"pts": s["pts"], "dashed": bool(DASH_RE.search(s.get("name") or "")), "name": s.get("name") or ""}
            for s in chains[0]]
    extras = [{"pts": s["pts"], "dashed": True, "name": s.get("name") or ""}
              for ch in chains[1:] for s in ch]
    return main, extras, bridged

def main_points(main):
    return np.concatenate([p["pts"] for p in main])

def read_trail(path):
    """Spec 01 entry point: file -> dict(main, extras, waypoints, name, report)."""
    segs, wpts, name = load_file(path)
    if not segs:
        raise ValueError("No track or route lines found in the file.")
    main, extras, bridged = chain_segments(segs)
    pts = main_points(main)
    ele_cov = float(np.isfinite(pts[:, 2]).mean())
    report = {
        "file": str(Path(path).resolve()),
        "name": name,
        "segments_in_file": len(segs),
        "main_pieces": len(main),
        "extra_pieces": len(extras),
        "gaps_bridged_mi": bridged,
        "main_length_mi": round(float(cum_miles(pts)[-1]), 2),
        "extras_length_mi": round(sum(float(cum_miles(p["pts"])[-1]) for p in extras), 2),
        "dashed_main_pieces": [p["name"] for p in main if p["dashed"]],
        "elevation_coverage": round(ele_cov, 3),
        "waypoints": len(wpts),
    }
    return {"main": main, "extras": extras, "waypoints": wpts, "name": name, "report": report}

# ------------------------------------------------------------------ files
def _pts_json(a):
    return [[round(float(la), 6), round(float(lo), 6), None if not np.isfinite(e) else round(float(e), 1)]
            for la, lo, e in a]

def save_track(trail, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = {k: [{"pts": _pts_json(p["pts"]), "dashed": p["dashed"], "name": p["name"]} for p in trail[k]]
            for k in ("main", "extras")}
    (out / "track.json").write_text(json.dumps(data), encoding="utf-8")
    (out / "waypoints.json").write_text(json.dumps(trail["waypoints"], indent=1), encoding="utf-8")
    return out / "track.json"

def load_track(project):
    data = json.loads((Path(project) / "track.json").read_text(encoding="utf-8"))
    return {k: [{"pts": np.array([[a, b, np.nan if c is None else c] for a, b, c in p["pts"]], float),
                 "dashed": p["dashed"], "name": p.get("name", "")} for p in data[k]] for k in ("main", "extras")}

def format_report(r):
    lines = [f"File: {r['file']}",
             f"Name in file: {r['name'] or '(none)'}",
             f"Main trail: {r['main_length_mi']} mi in {r['main_pieces']} piece(s) "
             f"from {r['segments_in_file']} segment(s) in the file"]
    if r["gaps_bridged_mi"]:
        lines.append(f"Gaps bridged (under {JOIN_GAP_MI} mi): {r['gaps_bridged_mi']}")
    if r["extra_pieces"]:
        lines.append(f"Separate dashed pieces: {r['extra_pieces']} ({r['extras_length_mi']} mi) - gaps over {JOIN_GAP_MI} mi or side trails")
    if r["dashed_main_pieces"]:
        lines.append(f"Dashed by name: {r['dashed_main_pieces']}")
    lines.append(f"Elevation data: {r['elevation_coverage'] * 100:.0f}% of points")
    lines.append(f"Waypoints: {r['waypoints']}")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="Read a local GPX/KML/KMZ into track.json (spec 01)")
    ap.add_argument("file")
    ap.add_argument("--out", help="project folder to write track.json / waypoints.json into")
    a = ap.parse_args()
    try:
        trail = read_trail(a.file)
    except (ValueError, ET.ParseError, OSError) as e:
        sys.exit(f"Could not read {a.file}: {e}")
    print(format_report(trail["report"]))
    if a.out:
        print(f"Wrote {save_track(trail, a.out)}")

if __name__ == "__main__":
    main()
