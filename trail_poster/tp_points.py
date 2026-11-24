#!/usr/bin/env python3
"""Spec 03 - Points of interest and mileage, with Gate 2.

Local only: points come from the file's waypoints plus what David supplies.
No online lookups (D7) and no network code (D4).

  1. Draft (after tp_input.py has written track.json / waypoints.json):
       python tp_points.py draft output/X --official-miles 288.0 \
              --start "Springer Mountain" --end "Big Creek" [--title "..."]
     Stops if the track and official length differ by more than 2% (V3.1);
     re-run with --accept-length-diff only after David has agreed.
  2. Edit output/X/pois.csv (and poster.json) as needed, then review:
       python tp_points.py review output/X
  3. Gate 2 - only after David says yes to the review:
       python tp_points.py approve output/X --layout banner --orientation landscape
     Any later edit to pois.csv or poster.json cancels the approval.
"""
import argparse, csv, hashlib, json, math, re, sys, datetime
from pathlib import Path

import numpy as np

from tp_input import load_track, cum_miles, main_points

LENGTH_TOLERANCE = 0.02     # V3.1
MAX_LABELS = 20             # V3.2
OFF_TRAIL_WARN_MI = 0.25    # waypoints farther than this are flagged at review
OFF_TRAIL_DROP_MI = 1.0     # ... and farther than this are left out of the draft
POI_FIELDS = ["show", "table", "name", "label", "type", "mile", "lat", "lon", "elev_ft", "side"]
TYPES = ["start", "end", "peak", "gap", "shelter", "camp", "waterfall", "trailhead", "point"]
APPROVAL_KEYS = ["title", "subtitle", "total_miles", "template", "orientation", "reverse"]

# ------------------------------------------------------------------ geometry
class Proj:
    """Local equirectangular projection to miles (north up)."""
    def __init__(self, lat0, lon0):
        self.kx = 69.172 * math.cos(math.radians(lat0))
        self.lat0, self.lon0 = lat0, lon0
    def __call__(self, lat, lon):
        return np.column_stack([(np.asarray(lon, float) - self.lon0) * self.kx,
                                (np.asarray(lat, float) - self.lat0) * 69.0])

def nearest_on_line(xy_line, pxy):
    """Index of the nearest track point and its distance (miles)."""
    step = max(1, len(xy_line) // 20000)
    sub = xy_line[::step]
    k = int(np.argmin(np.hypot(sub[:, 0] - pxy[0], sub[:, 1] - pxy[1]))) * step
    lo, hi = max(0, k - step), min(len(xy_line), k + step + 1)
    d = np.hypot(xy_line[lo:hi, 0] - pxy[0], xy_line[lo:hi, 1] - pxy[1])
    j = lo + int(np.argmin(d))
    return j, float(d.min())

# ------------------------------------------------------------------ type guess
_TYPE_RULES = [  # first match wins; tested against name + GPX type/sym/desc
    ("shelter", r"\bshelter|lean-?to|\bhut\b"),
    ("camp", r"\bcamp(site|ground)?s?\b|campsite|campground"),
    ("waterfall", r"\bfalls?\b|waterfall|cascade"),
    ("trailhead", r"trail ?head|\bparking\b|\bth\b"),
    ("gap", r"\bgap\b|\bnotch\b|\bsaddle\b|\bpass\b"),
    ("peak", r"\bsummit\b|\bpeak\b|\bmountain\b|\bmtn?\b|\bmt\.?\s|\bbald\b|\bknob\b|\bdome\b|\bhigh ?point\b"),
]

def guess_type(name, hint=""):
    text = f"{name} {hint}".lower()
    for typ, pat in _TYPE_RULES:
        if re.search(pat, text):
            return typ
    return "point"

# ------------------------------------------------------------------ project files
def _p(project, name):
    return Path(project) / name

def read_cfg(project):
    return json.loads(_p(project, "poster.json").read_text(encoding="utf-8"))

def write_cfg(project, cfg):
    _p(project, "poster.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def read_pois(project):
    with open(_p(project, "pois.csv"), newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write_pois(project, rows):
    with open(_p(project, "pois.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=POI_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in POI_FIELDS})

def _yes(v):
    return str(v or "y").strip().lower().startswith("y")

def _fmt_elev(v):
    s = str(v or "").strip().replace(",", "").rstrip("'").strip()
    if not s:
        return ""
    try:
        return str(int(round(float(s))))
    except ValueError:
        return s

def label_text(r):
    """Map label: override, else NAME plus elevation when present (V3.3)."""
    if (r.get("label") or "").strip():
        return r["label"].strip().upper()
    t = r["name"].strip().upper()
    e = _fmt_elev(r.get("elev_ft"))
    return f"{t} {e}'" if e else t

# ------------------------------------------------------------------ the trail
def trail_geometry(project, reverse=False):
    track = load_track(project)
    if reverse:
        track["main"] = [dict(p, pts=p["pts"][::-1]) for p in track["main"][::-1]]
    pts = main_points(track["main"])
    proj = Proj(pts[:, 0].mean(), pts[:, 1].mean())
    return track, pts, proj, proj(pts[:, 0], pts[:, 1]), cum_miles(pts)

def length_check(track_mi, official_mi):
    diff = abs(track_mi - official_mi) / official_mi
    return {"track_miles": round(track_mi, 2), "official_miles": official_mi,
            "difference_pct": round(diff * 100, 2), "scale_factor": round(official_mi / track_mi, 5),
            "within_tolerance": diff <= LENGTH_TOLERANCE}

# ------------------------------------------------------------------ draft
def draft(project, official_miles, start_name, end_name, title=None, subtitle="",
          accept_length_diff=False, year=None):
    project = Path(project)
    if _p(project, "pois.csv").exists():
        raise FileExistsError(f"{project / 'pois.csv'} already exists; edit it, or delete it to re-draft.")
    track, pts, proj, xy, cum = trail_geometry(project)
    lc = length_check(float(cum[-1]), float(official_miles))
    if not lc["within_tolerance"] and not accept_length_diff:
        raise LengthMismatch(lc)
    k = lc["official_miles"] / cum[-1]
    wpts = json.loads(_p(project, "waypoints.json").read_text(encoding="utf-8"))
    rows = [dict(show="y", table="y", name=start_name.upper(), type="start", mile=0.0,
                 lat=round(pts[0, 0], 6), lon=round(pts[0, 1], 6), side="auto"),
            dict(show="y", table="y", name=end_name.upper(), type="end", mile=float(official_miles),
                 lat=round(pts[-1, 0], 6), lon=round(pts[-1, 1], 6), side="auto")]
    seen, dropped, mid = {start_name.upper(), end_name.upper()}, [], []
    for w in wpts:
        name = (w.get("name") or "").strip()
        if not name or name.upper() in seen:
            continue
        j, dist = nearest_on_line(xy, proj([w["lat"]], [w["lon"]])[0])
        if dist > OFF_TRAIL_DROP_MI:
            dropped.append(f"{name} ({dist:.1f} mi off trail)")
            continue
        seen.add(name.upper())
        elev = round(w["ele_m"] * 3.28084) if w.get("ele_m") else ""
        mid.append(dict(show="y", table="y", name=name.upper(), type=guess_type(name, w.get("hint", "")),
                        mile=round(cum[j] * k, 1), lat=round(w["lat"], 6), lon=round(w["lon"], 6),
                        elev_ft=elev, side="auto"))
    mid.sort(key=lambda r: r["mile"])
    write_pois(project, rows[:1] + mid + rows[1:])
    span = np.ptp(xy, axis=0)
    aspect = float(span[0] / max(span[1], 1e-9))
    suggest_orient = "portrait" if aspect < 0.45 else "landscape"
    suggest_tpl = "banner" if (suggest_orient == "landscape" and aspect > 2.0) else "vertical"
    has_ele = bool(np.isfinite(pts[:, 2]).mean() > 0.8)
    cfg_path = _p(project, "poster.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cfg.update({"title": title or cfg.get("title") or "", "subtitle": subtitle or cfg.get("subtitle", ""),
                "total_miles": float(official_miles), "template": "unconfirmed", "orientation": "unconfirmed",
                "reverse": cfg.get("reverse", False), "year": year or cfg.get("year") or datetime.date.today().year,
                "suggested": {"template": suggest_tpl, "orientation": suggest_orient,
                              "aspect_w_over_h": round(aspect, 2), "has_elevation": has_ele},
                "length_check": dict(lc, accepted_by_david=bool(accept_length_diff and not lc["within_tolerance"])),
                "dropped_waypoints": dropped, "approval": None})
    write_cfg(project, cfg)
    return cfg

class LengthMismatch(Exception):
    def __init__(self, lc):
        self.lc = lc
        super().__init__(
            f"Track measures {lc['track_miles']} mi but the official length is {lc['official_miles']} mi "
            f"({lc['difference_pct']}% apart, limit {LENGTH_TOLERANCE * 100:.0f}%). This usually means a wrong or "
            f"partial file; a very twisty trail can also do it through GPS jitter. Ask David before re-running "
            f"with --accept-length-diff.")

# ------------------------------------------------------------------ compute (used by the renderer)
def compute_points(project, cfg=None):
    """Mileage for every row, scaled to the official total (D8).

    Returns dict: rows (all rows, each with _mile, _left, _ll, _off_trail), shown, table,
    total, scale, pts, xy, cum, proj, track, start_name, end_name.
    """
    cfg = cfg or read_cfg(project)
    track, pts, proj, xy, cum = trail_geometry(project, cfg.get("reverse", False))
    total = float(cfg.get("total_miles") or cum[-1])
    k = total / cum[-1]
    rows = read_pois(project)
    for r in rows:
        r["type"] = (r.get("type") or "point").strip().lower()
        off = 0.0
        if r["type"] == "start":
            j = 0
        elif r["type"] == "end":
            j = len(pts) - 1
        elif (r.get("lat") or "").strip() and (r.get("lon") or "").strip():
            ll = (float(r["lat"]), float(r["lon"]))
            j, off = nearest_on_line(xy, proj([ll[0]], [ll[1]])[0])
        else:   # no position given: place it by the mile David typed
            j = min(int(np.searchsorted(cum * k, float(r.get("mile") or 0))), len(pts) - 1)
        r["_mile"] = total if r["type"] == "end" else round(float(cum[j] * k), 1)
        r["_left"] = round(total - r["_mile"], 1)
        r["_off_trail"] = off
        if r["type"] in ("start", "end") or not (r.get("lat") or "").strip():
            r["_ll"] = (float(pts[j, 0]), float(pts[j, 1]))
        else:
            r["_ll"] = (float(r["lat"]), float(r["lon"]))
    rows.sort(key=lambda r: (r["_mile"], r["type"] == "end"))
    shown = [r for r in rows if _yes(r.get("show"))]
    table = [r for r in shown if _yes(r.get("table"))]
    name = lambda t, d: next((r["name"].strip().upper() for r in rows if r["type"] == t), d)
    return {"rows": rows, "shown": shown, "table": table, "total": total, "scale": k, "pts": pts,
            "xy": xy, "cum": cum, "proj": proj, "track": track,
            "start_name": name("start", "START"), "end_name": name("end", "END")}

# ------------------------------------------------------------------ review (Gate 2)
def review(project):
    cfg = read_cfg(project)
    P = compute_points(project, cfg)
    lc = cfg.get("length_check", {})
    out, warn = [], []
    out.append(f"TRAIL: {cfg.get('title') or '(no title)'}")
    out.append(f"Official length: {P['total']:.1f} mi   track measured: {lc.get('track_miles')} mi   "
               f"scale factor: {P['scale']:.4f} ({lc.get('difference_pct')}% apart)")
    s = cfg.get("suggested", {})
    out.append(f"Layout: {cfg.get('template')} (suggested {s.get('template')})   "
               f"orientation: {cfg.get('orientation')} (suggested {s.get('orientation')})   "
               f"elevation in file: {'yes' if s.get('has_elevation') else 'no'}")
    out.append(f"Subtitle: {cfg.get('subtitle') or '(none)'}   reverse direction: {cfg.get('reverse', False)}")
    out.append("")
    hdr = f"{'MILE':>7}  {'TO END':>7}  {'NAME':<30} {'TYPE':<10} {'ELEV':>6}  MAP  TABLE  MAP LABEL"
    out.append(hdr); out.append("-" * len(hdr))
    for r in P["rows"]:
        out.append(f"{r['_mile']:>7.1f}  {r['_left']:>7.1f}  {r['name'].strip().upper()[:30]:<30} {r['type']:<10} "
                   f"{_fmt_elev(r.get('elev_ft')):>6}  {'yes' if _yes(r.get('show')) else ' - ':<4} "
                   f"{'yes' if _yes(r.get('show')) and _yes(r.get('table')) else ' - ':<5}  "
                   f"{label_text(r) if _yes(r.get('show')) else ''}")
    # checks
    if len(P["shown"]) > MAX_LABELS:
        warn.append(f"{len(P['shown'])} labels on the map (limit {MAX_LABELS}); it may look crowded.")
    for r in P["rows"]:
        if r["type"] not in TYPES:
            warn.append(f"'{r['name']}' has unknown type '{r['type']}' (use: {', '.join(TYPES)}).")
        if r["type"] == "peak" and not _fmt_elev(r.get("elev_ft")) and _yes(r.get("show")):
            warn.append(f"Peak '{r['name']}' has no elevation.")
        if r["_off_trail"] > OFF_TRAIL_WARN_MI:
            warn.append(f"'{r['name']}' is {r['_off_trail']:.2f} mi off the trail; its mile is the nearest trail point.")
        if r["name"].strip().upper() in ("START", "END", ""):
            warn.append(f"The {r['type']} point needs a real name.")
    names = [r["name"].strip().upper() for r in P["rows"]]
    for n in sorted({n for n in names if names.count(n) > 1}):
        warn.append(f"'{n}' appears more than once.")
    if sum(r["type"] == "start" for r in P["rows"]) != 1 or sum(r["type"] == "end" for r in P["rows"]) != 1:
        warn.append("There must be exactly one start row and one end row.")
    if cfg.get("dropped_waypoints"):
        warn.append(f"Left out (over {OFF_TRAIL_DROP_MI:.0f} mi off trail): {', '.join(cfg['dropped_waypoints'])}")
    if not lc.get("within_tolerance", True):
        warn.append(f"Track and official length differ by {lc.get('difference_pct')}% (over 2%); "
                    f"accepted by David: {lc.get('accepted_by_david')}.")
    if cfg.get("template") == "banner" and not cfg.get("subtitle"):
        warn.append("Banner layout needs a subtitle (wording chosen per trail).")
    status = approval_status(project, cfg)
    out.append("")
    out += [f"WARNING: {w}" for w in warn] or ["No warnings."]
    out.append(f"Approval: {status}")
    return "\n".join(out), warn

# ------------------------------------------------------------------ approval
def _fingerprint(project, cfg):
    h = hashlib.sha256(_p(project, "pois.csv").read_bytes())
    h.update(json.dumps({k: cfg.get(k) for k in APPROVAL_KEYS}, sort_keys=True).encode())
    return h.hexdigest()

def approve(project, layout, orientation):
    cfg = read_cfg(project)
    if layout not in ("vertical", "banner") or orientation not in ("landscape", "portrait"):
        raise ValueError("Give --layout vertical|banner and --orientation landscape|portrait.")
    if layout == "banner" and orientation != "landscape":
        raise ValueError("The banner layout is landscape only.")
    cfg["template"], cfg["orientation"] = layout, orientation
    if layout == "banner" and not cfg.get("subtitle"):
        raise ValueError("Set a subtitle in poster.json first (banner layout).")
    lc = cfg.get("length_check", {})
    if not lc.get("within_tolerance", True) and not lc.get("accepted_by_david"):
        raise ValueError("Length difference over 2% has not been accepted.")
    P = compute_points(project, cfg)
    if sum(r["type"] == "start" for r in P["rows"]) != 1 or sum(r["type"] == "end" for r in P["rows"]) != 1:
        raise ValueError("There must be exactly one start row and one end row.")
    cfg["approval"] = {"approved_at": datetime.datetime.now().isoformat(timespec="seconds"),
                       "fingerprint": None}
    write_cfg(project, cfg)        # write first so the fingerprint covers the saved settings
    cfg["approval"]["fingerprint"] = _fingerprint(project, cfg)
    write_cfg(project, cfg)
    return cfg

def approval_status(project, cfg=None):
    cfg = cfg or read_cfg(project)
    a = cfg.get("approval")
    if not a:
        return "NOT APPROVED"
    if a.get("fingerprint") != _fingerprint(project, cfg):
        return "CHANGED SINCE APPROVAL - needs review and approval again"
    return f"approved {a['approved_at']}"

def is_approved(project):
    return approval_status(project).startswith("approved")

# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="Points and mileage (spec 03)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft"); d.add_argument("project")
    d.add_argument("--official-miles", type=float, required=True)
    d.add_argument("--start", required=True); d.add_argument("--end", required=True)
    d.add_argument("--title"); d.add_argument("--subtitle", default="")
    d.add_argument("--year", type=int)
    d.add_argument("--accept-length-diff", action="store_true",
                   help="only after David agrees to a >2%% length difference")
    r = sub.add_parser("review"); r.add_argument("project")
    a = sub.add_parser("approve"); a.add_argument("project")
    a.add_argument("--layout", required=True, choices=["vertical", "banner"])
    a.add_argument("--orientation", required=True, choices=["landscape", "portrait"])
    args = ap.parse_args()
    try:
        if args.cmd == "draft":
            draft(args.project, args.official_miles, args.start, args.end, args.title, args.subtitle,
                  args.accept_length_diff, args.year)
            print(review(args.project)[0])
        elif args.cmd == "review":
            print(review(args.project)[0])
        else:
            approve(args.project, args.layout, args.orientation)
            print(f"Gate 2 approved: {approval_status(args.project)}")
    except (LengthMismatch, ValueError, FileExistsError, FileNotFoundError) as e:
        sys.exit(f"STOPPED: {e}")

if __name__ == "__main__":
    main()
