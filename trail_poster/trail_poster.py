#!/usr/bin/env python3
"""Beech Creek Naturals trail poster generator.

Turns a local GPX / KML / KMZ file into a minimalist trail-map poster in the
house style (Art Loeb / Bartram / MST look): black trail line, gray uppercase
Montserrat labels, peak ridgelines, tent / waterfall / hiker icons, a compass, a
three-column mileage table, an optional elevation profile, and the
(c) Beech Creek Naturals line.

Local files only: this tool contains no network code (specs/00-overview.md, D4).

  1. Read the file (spec 01):     python tp_input.py "C:/path/track.gpx" --out output/My_Trail
  2. Draft points (spec 03):      python tp_points.py draft output/My_Trail --official-miles 30.1 --start "..." --end "..."
  3. Review, then approve (Gate 2): python tp_points.py review / approve output/My_Trail ...
  4. Render (refuses until Gate 2 is approved):
       python trail_poster.py render output/My_Trail             (preview + masters)
       python trail_poster.py render output/My_Trail --sizes all (all print sizes, 300 dpi)

A project folder holds: track.json (the trail), pois.csv (labels: edit freely),
poster.json (title, layout options), preview.png, masters (SVG/PDF) and print JPGs.
"""
import argparse, csv, io, json, math, re, sys, datetime
from pathlib import Path

from tp_points import compute_points, label_text, is_approved, approval_status, read_cfg

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.patches import Polygon, Wedge, Circle, FancyBboxPatch
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "path"

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / "fonts"
SHOP = "Beech Creek Naturals"

# ------------------------------------------------------------------ style
INK = "#111111"          # trail line, vertical title
TITLE_INK = "#2b2d31"    # banner title
GRAY = "#6d6e71"         # labels, table
ICON = "#939598"         # compass, tents, hikers, waterfalls
FILL = "#d1d3d4"         # elevation profile fill
MASTER = {"landscape": (14.0, 10.0), "portrait": (10.0, 14.0)}
MARGIN = 0.07            # white margin on every print, per side
DPI = 300

SIZES = {  # name: (w, h) inches; same set as 4_Print_Sizes/SIZE_GUIDE.txt
    "landscape": {"36x24": (36, 24), "24x18": (24, 18), "20x16": (20, 16), "14x11": (14, 11),
                  "7x5": (7, 5), "A1_landscape": (33.11, 23.39)},
    "portrait": {"24x36": (24, 36), "18x24": (18, 24), "16x20": (16, 20), "11x14": (11, 14),
                 "5x7": (5, 7), "A1": (23.39, 33.11)},
}

def _font(name, fallback="sans-serif"):
    p = FONT_DIR / f"{name}.ttf"
    if p.exists():
        return FontProperties(fname=str(p))
    print(f"  ! font {p.name} missing, using {fallback}", file=sys.stderr)
    return FontProperties(family=fallback)

F_TITLE = _font("Montserrat-Black")
F_BANNER = _font("Montserrat-ExtraBold")
F_LABEL = _font("Montserrat-Regular")
F_N = _font("Montserrat-Medium")
F_TABLE = _font("SourceSans3-Regular")
F_TABLE_B = _font("SourceSans3-SemiBold")

HAIR = "\u200a"

def track(s, n=2):
    """Letter-space a string with hair spaces (matplotlib has no tracking)."""
    return (HAIR * n).join(s)

_RENDERER = RendererAgg(10, 10, 72)  # 72 dpi -> pixels == points

def measure(text, fp, size):
    """(width, height) in inches of a single-line string."""
    fp = fp.copy(); fp.set_size(size)
    w, h, d = _RENDERER.get_text_width_height_descent(text, fp, ismath=False)
    return w / 72.0, h / 72.0

# ------------------------------------------------------------------ geometry
def rdp(pts, eps):
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, bool); keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = b - a; L = math.hypot(*seg); p = pts[i + 1:j]
        if L == 0:
            d = np.hypot(*(p - a).T)
        else:
            d = np.abs(seg[0] * (p[:, 1] - a[1]) - seg[1] * (p[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            m = i + 1 + k; keep[m] = True
            stack += [(i, m), (m, j)]
    return pts[keep]

def resample(xy, step):
    if len(xy) < 2:
        return xy
    d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    t = np.arange(0, d[-1] + step, step)
    return np.column_stack([np.interp(t, d, xy[:, 0]), np.interp(t, d, xy[:, 1])])

# ------------------------------------------------------------------ points (spec 03 lives in tp_points.py)
TYPE_PRIORITY = {"start": 0, "end": 0, "peak": 1, "shelter": 1, "waterfall": 1, "camp": 2,
                 "gap": 2, "trailhead": 3, "point": 3}

# ------------------------------------------------------------------ icons (data units = master inches)
def draw_tent(ax, x, y, w):
    h = w * 0.62
    ax.add_patch(Polygon([(x - w / 2, y), (x + w / 2, y), (x + w * 0.04, y + h)], closed=True, fc=ICON, ec="none", zorder=4))
    ax.add_patch(Polygon([(x - w * 0.02, y), (x + w * 0.2, y), (x + w * 0.02, y + h * 0.78)], closed=True, fc="white", ec="none", zorder=5))

def draw_waterfall(ax, x, y, h, s):
    w = h * 0.7
    for i in range(5):
        xx = x - w / 2 + i * w / 4
        t = np.linspace(0, 1, 30)
        ax.plot(xx + 0.012 * h * np.sin(t * 9 + i), y + h * 0.15 + t * h * 0.85, color=ICON, lw=0.9 * s, zorder=4,
                solid_capstyle="round")
    t = np.linspace(-1, 1, 40)
    ax.plot(x + t * w * 0.62, y + h * 0.08 + 0.03 * h * np.cos(t * 12), color=ICON, lw=0.7 * s, zorder=4)

def draw_hiker(ax, x, y, h):
    """Gray hiker silhouette facing right, standing on (x, y)."""
    u = h
    P = lambda pts: ax.add_patch(Polygon([(x + a * u, y + b * u) for a, b in pts], closed=True, fc=ICON, ec="none", zorder=4))
    ax.add_patch(Circle((x + 0.05 * u, y + 0.90 * u), 0.085 * u, fc=ICON, ec="none", zorder=4))
    ax.add_patch(FancyBboxPatch((x - 0.30 * u, y + 0.44 * u), 0.2 * u, 0.36 * u,
                                boxstyle=f"round,pad=0,rounding_size={0.06 * u}", fc=ICON, ec="none", zorder=4))
    P([(-0.10, 0.80), (0.12, 0.80), (0.10, 0.46), (-0.08, 0.46)])                     # torso
    P([(-0.07, 0.48), (0.03, 0.48), (-0.05, 0.0), (-0.14, 0.0)])                       # back leg
    P([(0.01, 0.48), (0.10, 0.48), (0.17, 0.0), (0.08, 0.0)])                          # front leg
    P([(0.08, 0.76), (0.13, 0.72), (0.27, 0.60), (0.24, 0.55)])                        # arm
    ax.plot([x + 0.27 * u, x + 0.30 * u], [y + 0.82 * u, y], color=ICON, lw=max(0.6, u * 72 * 0.035), zorder=4,
            solid_capstyle="round")

def draw_ridge(ax, x0, y, w, s, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, 120)
    bump = np.sin(np.pi * t) ** 1.6
    jag = np.convolve(rng.normal(0, 1, 120), np.ones(4) / 4, mode="same")
    yy = y + w * 0.13 * bump + w * 0.008 * jag * bump
    ax.plot(x0 + t * w, yy, color=INK, lw=0.55 * s, zorder=4, solid_capstyle="round")

def draw_compass(ax, cx, cy, r, s):
    ring = r * 0.16
    ax.add_patch(Wedge((cx, cy), r, 104, 436, width=ring, fc=ICON, ec="none", zorder=4))
    apex, bl, br, mid = (cx, cy + r * 0.66), (cx - r * 0.42, cy - r * 0.5), (cx + r * 0.42, cy - r * 0.5), (cx, cy - r * 0.32)
    ax.add_patch(Polygon([apex, mid, br], closed=True, fc=ICON, ec=ICON, lw=0.8 * s, zorder=4))
    ax.add_patch(Polygon([apex, bl, mid], closed=True, fc="none", ec=ICON, lw=1.0 * s, zorder=4, joinstyle="round"))
    ax.text(cx, cy + r * 0.985, "N", fontproperties=F_N, fontsize=r * 72 * 0.42 * s, color=ICON,
            ha="center", va="center", zorder=5)

# ------------------------------------------------------------------ layout
LABEL_PT = 9.5
TABLE_PT = 12.0
ICON_SIZE = {"peak": (0.55, 0.09), "shelter": (0.30, 0.19), "camp": (0.30, 0.19), "waterfall": (0.20, 0.26),
             "start": (0.30, 0.42), "end": (0.30, 0.42), "trailhead": (0.30, 0.42)}

def rects_overlap(a, b, pad=0.0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])

def pts_in(rect, pts, pad=0.03):
    return int(np.count_nonzero((pts[:, 0] > rect[0] - pad) & (pts[:, 0] < rect[2] + pad) &
                                (pts[:, 1] > rect[1] - pad) & (pts[:, 1] < rect[3] + pad)))

def group_geometry(r, ax_, ay_, side, dy, label_pt):
    """Icon + text block for one POI. Returns dict(rect, text=(x,y,ha), icon=(x,y) or None)."""
    text = track(label_text(r))
    tw, th = measure(text, F_LABEL, label_pt)
    typ = r["type"]
    iw, ih = ICON_SIZE.get(typ, (0.0, 0.0))
    gap0 = 0.08 if typ in ICON_SIZE else 0.09
    y = ay_ + dy
    if typ in ("start", "end", "trailhead"):
        y_text = y + ih * 0.35
    else:
        y_text = y
    if side == "right":
        ix = ax_ + gap0
        tx = ix + iw + (0.07 if iw else 0)
        rect = [ax_ + gap0 * 0.5, min(y - ih / 2 if typ != "peak" else y - 0.02, y_text - th / 2), tx + tw, max(y + ih / 2, y_text + th / 2)]
        ha = "left"
    else:
        ix = ax_ - gap0 - iw
        tx = ix - (0.07 if iw else 0)
        rect = [tx - tw, min(y - ih / 2 if typ != "peak" else y - 0.02, y_text - th / 2), ax_ - gap0 * 0.5, max(y + ih / 2, y_text + th / 2)]
        ha = "right"
    if typ in ("start", "end", "trailhead"):
        rect[1] = min(rect[1], y - 0.02); rect[3] = max(rect[3], y + ih)
    text_rect = [tx, y_text - th / 2, tx + tw, y_text + th / 2] if ha == "left" else [tx - tw, y_text - th / 2, tx, y_text + th / 2]
    return dict(rect=rect, text_rect=text_rect, text=(tx, y_text, ha, text), icon=(ix, y, iw, ih) if iw else None, side=side)

def group_geometry_any(r, ax_, ay_, side, dy, label_pt):
    """Like group_geometry, plus 'above'/'below': the whole group centered over the point."""
    if side in ("left", "right"):
        return group_geometry(r, ax_, ay_, side, dy, label_pt)
    g = group_geometry(r, ax_, ay_, "right", dy, label_pt)
    rc = g["rect"]
    dx = ax_ - (rc[0] + rc[2]) / 2
    g["rect"] = [rc[0] + dx, rc[1], rc[2] + dx, rc[3]]
    g["text_rect"] = [g["text_rect"][0] + dx, g["text_rect"][1], g["text_rect"][2] + dx, g["text_rect"][3]]
    tx, ty, ha, text = g["text"]
    g["text"] = (tx + dx, ty, ha, text)
    if g["icon"]:
        ix, iy, iw, ih = g["icon"]
        g["icon"] = (ix + dx, iy, iw, ih)
    g["side"] = side
    return g

def place_labels(rows, trail_pts, obstacles, bounds, label_pt):
    placed, out = [], []
    order = sorted(range(len(rows)), key=lambda i: (TYPE_PRIORITY.get(rows[i]["type"], 3), rows[i]["_mile"]))
    for i in order:
        r = rows[i]
        ax_, ay_ = r["_xy"]
        near = trail_pts[np.hypot(trail_pts[:, 0] - ax_, trail_pts[:, 1] - ay_) < 1.2]
        pref = "left" if np.count_nonzero(near[:, 0] > ax_ + 0.05) > np.count_nonzero(near[:, 0] < ax_ - 0.05) else "right"
        forced = (r.get("side") or "auto").lower()
        if forced in ("left", "right", "above", "below"):
            cands = [(forced, dy) for dy in ((0.3, 0.45, 0.6) if forced == "above" else (-0.3, -0.45, -0.6)
                                             if forced == "below" else (0, 0.13, -0.13, 0.26, -0.26, 0.4, -0.4))]
        else:
            other = "left" if pref == "right" else "right"
            cands = ([(pref, dy) for dy in (0, 0.13, -0.13, 0.26, -0.26, 0.4, -0.4, 0.55, -0.55)] +
                     [(other, dy) for dy in (0, 0.13, -0.13, 0.26, -0.26, 0.4, -0.4, 0.55, -0.55)] +
                     [("above", dy) for dy in (0.3, 0.45, 0.6)] + [("below", dy) for dy in (-0.3, -0.45, -0.6)])
        best = None
        for side, dy in cands:
            g = group_geometry_any(r, ax_, ay_, side, dy, label_pt)
            rc, tr = g["rect"], g["text_rect"]
            cross = pts_in(tr, trail_pts, 0.035)
            hard = (sum(1 for p in placed if rects_overlap(rc, p, 0.05)) +
                    sum(1 for o in obstacles if rects_overlap(rc, o, 0.08)) +
                    int(rc[0] < bounds[0] or rc[1] < bounds[1] or rc[2] > bounds[2] or rc[3] > bounds[3]))
            score = 1000 * hard + 25 * cross + 6 * pts_in(rc, trail_pts, 0.0)
            score += abs(dy) * 30 + (0 if side == pref else 8 if side in ("left", "right") else 14)
            if best is None or score < best[0]:
                best = (score, g, cross, hard)
        score, g, cross, hard = best
        g["crossings"], g["collisions"] = cross, hard
        placed.append(g["rect"])
        out.append((i, g, score))
    return out

def fit_transform(xy_all, rect):
    x0, y0, x1, y1 = rect
    mn, mx = xy_all.min(0), xy_all.max(0)
    span = np.maximum(mx - mn, 1e-6)
    k = min((x1 - x0) / span[0], (y1 - y0) / span[1])
    off = np.array([(x0 + x1) / 2, (y0 + y1) / 2]) - k * (mn + mx) / 2
    return k, off

def table_layout(rows, start, end, pt):
    head_l = _wrap(start, 15); head_r = _wrap(end, 15)
    nums_w = max(measure(track(f"{v:.1f}"), F_TABLE, pt)[0] for r in rows for v in (r["_mile"], r["_left"]))
    hl_w = max(measure(track(h), F_TABLE_B, pt)[0] for h in head_l)
    hr_w = max(measure(track(h), F_TABLE_B, pt)[0] for h in head_r)
    names_w = max([measure(track(r["name"].upper()), F_TABLE, pt)[0] for r in rows] +
                  [measure(track("POINT OF INTEREST"), F_TABLE_B, pt)[0]])
    c1 = max(nums_w, hl_w); c3 = max(nums_w, hr_w); gap = 0.32
    lh = pt / 72 * 1.38
    nhead = max(len(head_l), len(head_r))
    w = c1 + gap + names_w + gap + c3
    h = lh * (len(rows) + nhead) + lh * 0.2
    return dict(w=w, h=h, c1=c1, c2=names_w, c3=c3, gap=gap, lh=lh, head_l=head_l, head_r=head_r, pt=pt, nhead=nhead)

def _wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        if cur and len(cur) + 1 + len(wd) > n:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    return lines + [cur] if cur else lines or [""]

def draw_table(ax, T, x, y_top, rows, s):
    pt = T["pt"] * s
    xr1 = x + T["c1"]; xc2 = xr1 + T["gap"] + T["c2"] / 2; xl3 = xr1 + T["gap"] + T["c2"] + T["gap"]
    xr3 = xl3 + T["c3"]
    nh = T["nhead"]
    for k in range(nh):  # headers, bottom-aligned
        yy = y_top - T["lh"] * (k + 0.5)
        hl = T["head_l"][k - (nh - len(T["head_l"]))] if k >= nh - len(T["head_l"]) else None
        hr = T["head_r"][k - (nh - len(T["head_r"]))] if k >= nh - len(T["head_r"]) else None
        if hl:
            ax.text(xr1, yy, track(hl), fontproperties=F_TABLE_B, fontsize=pt, color=GRAY, ha="right", va="center")
        if hr:
            ax.text(xl3, yy, track(hr), fontproperties=F_TABLE_B, fontsize=pt, color=GRAY, ha="left", va="center")
        if k == nh - 1:
            ax.text(xc2, yy, track("POINT OF INTEREST"), fontproperties=F_TABLE_B, fontsize=pt, color=GRAY, ha="center", va="center")
    y = y_top - T["lh"] * (nh + 0.2)
    for r in rows:
        yy = y - T["lh"] * 0.5
        ax.text(xr1, yy, track(f"{r['_mile']:.1f}"), fontproperties=F_TABLE, fontsize=pt, color=GRAY, ha="right", va="center")
        ax.text(xc2, yy, track(r["name"].upper()), fontproperties=F_TABLE, fontsize=pt, color=GRAY, ha="center", va="center")
        ax.text(xl3, yy, track(f"{r['_left']:.1f}"), fontproperties=F_TABLE, fontsize=pt, color=GRAY, ha="left", va="center")
        y -= T["lh"]

def nice_step(span, n=5):
    raw = span / n
    p = 10 ** math.floor(math.log10(raw))
    return min((m * p for m in (1, 2, 2.5, 5, 10)), key=lambda v: abs(v - raw))

# ------------------------------------------------------------------ the poster
class Poster:
    def __init__(self, project, draft=False):
        self.dir = Path(project)
        self.cfg = read_cfg(self.dir)
        self.draft = draft
        if draft:  # before Gate 2: use the suggested layout, never write print files
            sug = self.cfg.get("suggested", {})
            if self.cfg.get("template") not in ("vertical", "banner"):
                self.cfg["template"] = sug.get("template", "auto")
            if self.cfg.get("orientation") not in ("landscape", "portrait"):
                self.cfg["orientation"] = sug.get("orientation", "auto")
        self._prepare()

    def _prepare(self):
        cfg = self.cfg
        P = compute_points(self.dir, cfg)          # spec 03: mileage scaled to the official total
        self.track, self.pts, self.proj, self.xy, self.cum = P["track"], P["pts"], P["proj"], P["xy"], P["cum"]
        self.k_miles, self.total = P["scale"], P["total"]
        self.rows, self.table_rows_all = P["shown"], P["table"]
        self.start_name, self.end_name = P["start_name"], P["end_name"]
        pts = self.pts
        ele = pts[:, 2]
        self.has_ele = np.isfinite(ele).mean() > 0.8 if len(ele) else False
        # orientation / template
        span = np.ptp(self.xy, axis=0)
        aspect = span[0] / max(span[1], 1e-6)
        orient = cfg.get("orientation", "auto")
        if orient == "auto":
            orient = "portrait" if aspect < 0.45 else "landscape"
        self.orient = orient
        tpl = cfg.get("template", "auto")
        if tpl == "auto":
            tpl = "banner" if (orient == "landscape" and aspect > 2.0) else "vertical"
        self.template = tpl
        prof = cfg.get("profile", "auto")
        self.profile = self.has_ele and (prof is True or (prof == "auto" and tpl == "banner"))
        self.W, self.H = MASTER[orient]
        self._layout()

    # -- layout in master inches -------------------------------------------------
    def _layout(self):
        W, H = self.W, self.H
        cfg = self.cfg
        table_rows = self.table_rows_all
        self.table_rows = table_rows
        self.obstacles = []
        self.bounds = (0.12, 0.12, W - 0.12, H - 0.12)
        title = cfg.get("title", "TRAIL").upper()
        pt = TABLE_PT
        while True:
            T = table_layout(table_rows, self.start_name, self.end_name, pt)
            limit = (H - 0.8) if self.template == "vertical" else (H * 0.42)
            if T["h"] <= limit or pt <= 6.5:
                break
            pt -= 0.5
        self.T = T
        self.footer = (W - 2.4, 0.12, W - 0.25, 0.36)
        self.obstacles.append(self.footer)
        all_xy = np.concatenate([self.xy] + [self.proj(p["pts"][:, 0], p["pts"][:, 1]) for p in self.track["extras"]]) \
            if self.track["extras"] else self.xy
        pois_xy = np.array([self.proj([r["_ll"][0]], [r["_ll"][1]])[0] for r in self.rows]) if self.rows else np.empty((0, 2))
        fit_xy = np.concatenate([all_xy, pois_xy]) if len(pois_xy) else all_xy
        rs = resample(rdp(self.xy, np.ptp(self.xy, axis=0).max() * 0.002), np.ptp(self.xy, axis=0).max() / 400)
        lab = 1.25  # label room each side of the trail (in)
        if self.template == "vertical":
            band = 1.55 if self.orient == "landscape" else 1.35
            self.band = band
            r_c = 0.46
            self.compass = (band / 2 + 0.05, H - 0.38 - r_c, r_c)
            self.title_box = (0.15, 0.3, band, H - 0.95)
            self.obstacles += [(0.1, 0.1, band + 0.1, H - 0.1)]
            area = (band + 0.25, 0.4, W - 0.3, H - 0.35)
        else:
            self.band = 0
            area = (0.35, H * 0.46, W - 0.35, H - 0.3)
        cands = []
        ax0, ay0, ax1, ay1 = area
        tw, th = T["w"], T["h"]
        if self.template == "vertical":
            for corner in ("tr", "br", "tl", "bl"):
                tx = ax1 - tw if corner[1] == "r" else ax0
                ty = ay1 - th if corner[0] == "t" else ay0
                trect = (tx, ty, tx + tw, ty + th)
                for mrect in (area,
                              (ax0, ay0, ax1 - tw - 0.35, ay1) if corner[1] == "r" else (ax0 + tw + 0.35, ay0, ax1, ay1),
                              (ax0, ay0, ax1, ay1 - th - 0.3) if corner[0] == "t" else (ax0, ay0 + th + 0.3, ax1, ay1)):
                    cands.append((trect, mrect))
        else:
            tx = W - 0.4 - tw
            trect = (tx, 0.45, tx + tw, 0.45 + th)
            cands.append((trect, area))
        base_obstacles = list(self.obstacles)
        # Fit the map, place labels; if any label still crosses the trail or collides,
        # give labels more room (smaller map) and try again.
        for attempt, lab in enumerate((1.25, 1.65, 2.05, 2.45)):
            self.obstacles = list(base_obstacles)
            self._fit_and_place(cands, lab, fit_xy, rs)
            if not self.label_problems:
                break
        bad = self.label_problems
        self.warnings = [f"label '{n}' {why}; hide it, shorten it, or set side= (left/right/above/below) in pois.csv"
                         for n, why in bad]

    def _fit_and_place(self, cands, lab, fit_xy, rs):
        best = None
        for trect, mrect in cands:
            inner = (mrect[0] + lab, mrect[1] + 0.3, mrect[2] - lab, mrect[3] - 0.3)
            if inner[2] - inner[0] < 1 or inner[3] - inner[1] < 1:
                continue
            k, off = fit_transform(fit_xy, inner)
            p = rs * k + off
            hits = pts_in(trect, p, 0.35)
            score = k * (1.0 if hits == 0 else 0.0) - hits * 1e-6
            if best is None or score > best[0]:
                best = (score, k, off, trect)
        _, self.k, self.off, self.table_rect = best
        self.obstacles.append(self.table_rect)
        if self.template == "banner":
            self.title_rect = (0.35, 0.4, self.table_rect[0] - 0.4, 2.45)
            self.obstacles.append(self.title_rect)
            if self.profile:
                self.profile_rect = (0.95, 2.85, self.table_rect[0] - 0.6, 4.15)
                self.obstacles.append((0.6, 2.7, self.table_rect[0] - 0.4, 4.3))
        self.trail_draw = [(rdp(self.proj(p["pts"][:, 0], p["pts"][:, 1]), 0.0008 / self.k * 1.0) * self.k + self.off, p["dashed"])
                           for p in self.track["main"]]
        self.extras_draw = [(rdp(self.proj(p["pts"][:, 0], p["pts"][:, 1]), 0.0008 / self.k) * self.k + self.off, True)
                            for p in self.track["extras"]]
        trail_pts = np.concatenate([resample(d, 0.03) for d, _ in self.trail_draw + self.extras_draw])
        for r in self.rows:
            r["_xy"] = tuple(self.proj([r["_ll"][0]], [r["_ll"][1]])[0] * self.k + self.off)
        self.trail_pts = trail_pts
        self.labels = place_labels(self.rows, trail_pts, self.obstacles, self.bounds, LABEL_PT)
        self.label_problems = []
        for i, g, _ in self.labels:
            if g["collisions"]:
                self.label_problems.append((self.rows[i]["name"], "overlaps another label, the table, the title or the page edge"))
            elif g["crossings"]:
                self.label_problems.append((self.rows[i]["name"], "crosses the trail line"))

    # -- drawing -------------------------------------------------------------
    def draw(self, ax, s):
        W, H = self.W, self.H
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
        for d, dashed in self.extras_draw:
            ax.plot(d[:, 0], d[:, 1], color=INK, lw=1.1 * s, ls=(0, (3.2, 2.4)), solid_capstyle="round", zorder=2)
        for d, dashed in self.trail_draw:
            ax.plot(d[:, 0], d[:, 1], color=INK, lw=1.2 * s, ls=(0, (3.2, 2.4)) if dashed else "-",
                    solid_capstyle="round", solid_joinstyle="round", zorder=3)
        for i, g, _ in self.labels:
            r = self.rows[i]
            typ = r["type"]
            if g["icon"]:
                ix, iy, iw, ih = g["icon"]
                if typ == "peak":
                    draw_ridge(ax, ix, iy - 0.03, iw, s, seed=i)
                elif typ in ("shelter", "camp"):
                    draw_tent(ax, ix + iw / 2, iy - ih / 2, iw)
                elif typ == "waterfall":
                    draw_waterfall(ax, ix + iw / 2, iy - ih / 2, ih, s)
                elif typ in ("start", "end", "trailhead"):
                    draw_hiker(ax, ix + iw * 0.45, iy, ih)
            elif typ == "point":
                ax.add_patch(Circle(r["_xy"], 0.035, fc="white", ec=INK, lw=0.9 * s, zorder=5))
            tx, ty, ha, text = g["text"]
            ax.text(tx, ty, text, fontproperties=F_LABEL, fontsize=LABEL_PT * s, color=GRAY, ha=ha, va="center", zorder=6)
        T = self.T
        draw_table(ax, T, self.table_rect[0], self.table_rect[3], self.table_rows, s)
        year = self.cfg.get("year") or datetime.date.today().year
        ax.text(W - 0.3, 0.22, f"\u00a9 {SHOP} {year}", fontproperties=F_TABLE, fontsize=6.5 * s, color=GRAY,
                ha="right", va="center")
        title = self.cfg.get("title", "TRAIL").upper()
        if self.template == "vertical":
            cx, cy, r = self.compass
            draw_compass(ax, cx, cy, r, s)
            top = cy - r - 0.45
            avail = top - 0.45
            t = track(title, 3)
            size = 38.0
            while measure(t, F_TITLE, size)[0] > avail and size > 18:
                size -= 1
            ax.text(cx, top, t, fontproperties=F_TITLE, fontsize=size * s, color=INK, rotation=-90,
                    ha="center", va="top", rotation_mode="default")
            if self.cfg.get("subtitle"):
                ax.text(self.table_rect[0] + T["w"] / 2, self.table_rect[1] - 0.25, track(self.cfg["subtitle"].upper(), 2),
                        fontproperties=F_LABEL, fontsize=9 * s, color=GRAY, ha="center", va="center")
        else:
            x0, y0, x1, y1 = self.title_rect
            r = 0.52
            cx, cy = x0 + 0.6 + r, y0 + 1.15
            draw_compass(ax, cx, cy, r, s)
            tx = cx + r + 0.2
            avail = x1 - tx
            words = title.split()
            lines = [title]
            size = 44.0
            if measure(track(title, 2), F_BANNER, size)[0] > avail and len(words) > 1:
                best = min(range(1, len(words)), key=lambda i: max(len(" ".join(words[:i])), len(" ".join(words[i:]))))
                lines = [" ".join(words[:best]), " ".join(words[best:])]
            while max(measure(track(l, 2), F_BANNER, size)[0] for l in lines) > avail and size > 16:
                size -= 1
            lh = size / 72 * 1.05
            ytop = cy + (lh * len(lines)) / 2 - lh * 0.5
            for n, l in enumerate(lines):
                ax.text(tx, ytop - n * lh, track(l, 2), fontproperties=F_BANNER, fontsize=size * s, color=TITLE_INK,
                        ha="left", va="center")
            sub = self.cfg.get("subtitle") or f"{self.total:,.1f} MILES"
            ax.text(tx + 0.02, ytop - len(lines) * lh - 0.12, track(sub.upper(), 2), fontproperties=F_LABEL,
                    fontsize=11 * s, color=GRAY, ha="left", va="center")
            if self.profile:
                self._draw_profile(ax, s)

    def _draw_profile(self, ax, s):
        x0, y0, x1, y1 = self.profile_rect
        miles = self.cum * self.k_miles
        ft = self.pts[:, 2] * 3.28084
        ok = np.isfinite(ft)
        miles, ft = miles[ok], ft[ok]
        n = max(1, len(ft) // 600)
        if n > 1:
            ft = np.convolve(ft, np.ones(n) / n, mode="same")
        top = max(ft.max(), 1)
        step = nice_step(top, 3)
        ymax = math.ceil(top / step) * step
        X = x0 + miles / miles[-1] * (x1 - x0)
        Y = y0 + ft / ymax * (y1 - y0)
        ax.fill_between(X, y0, Y, color=FILL, lw=0, zorder=2)
        ax.plot(X, Y, color=INK, lw=0.5 * s, zorder=3)
        ax.plot([x0, x1], [y0, y0], color=GRAY, lw=0.4 * s, zorder=3)
        ax.plot([x0, x0], [y0, y1], color=GRAY, lw=0.4 * s, zorder=3)
        v = step
        while v <= ymax:
            yy = y0 + v / ymax * (y1 - y0)
            ax.text(x0 - 0.05, yy, f"{int(v):,}'", fontproperties=F_TABLE, fontsize=5.5 * s, color=GRAY, ha="right", va="center")
            v += step
        mstep = nice_step(miles[-1], 6)
        m = 0.0
        while m < miles[-1] - mstep * 0.4:
            ax.text(x0 + m / miles[-1] * (x1 - x0), y0 - 0.1, f"{m:g}", fontproperties=F_TABLE, fontsize=5.5 * s,
                    color=GRAY, ha="center", va="center")
            m += mstep
        ax.text(x1, y0 - 0.1, "MILES", fontproperties=F_TABLE, fontsize=5.5 * s, color=GRAY, ha="right", va="center")

    # -- output -------------------------------------------------------------
    def figure(self, page_w, page_h, dpi):
        fig = plt.figure(figsize=(page_w, page_h), dpi=dpi, facecolor="white")
        aw, ah = page_w * (1 - 2 * MARGIN), page_h * (1 - 2 * MARGIN)
        sc = min(aw / self.W, ah / self.H)
        w, h = self.W * sc, self.H * sc
        ax = fig.add_axes([(page_w - w) / 2 / page_w, (page_h - h) / 2 / page_h, w / page_w, h / page_h])
        self.draw(ax, sc)
        if self.draft:
            fig.text(0.5, 0.5, "DRAFT", fontproperties=F_TITLE, fontsize=page_w * 18, color="#e04848",
                     alpha=0.10, ha="center", va="center", rotation=28)
            fig.text(0.012, 0.985, "DRAFT - point list not approved - not for sale", fontproperties=F_LABEL,
                     fontsize=page_w * 0.7, color="#e04848", ha="left", va="top")
        return fig

    def slug(self):
        return re.sub(r"[^A-Za-z0-9]+", "_", self.cfg.get("title", "Trail")).strip("_")

    def render(self, sizes="preview"):
        slug = self.slug()
        out = []
        if self.draft:   # watermarked look only: no masters, no print sizes
            fig = self.figure(self.W, self.H, 110)
            p = self.dir / "draft_preview.png"; fig.savefig(p, dpi=110, facecolor="white"); plt.close(fig)
            return [p]
        fig = self.figure(self.W, self.H, 110)
        p = self.dir / "preview.png"; fig.savefig(p, dpi=110, facecolor="white"); plt.close(fig); out.append(p)
        masters = self.dir / "masters"; masters.mkdir(exist_ok=True)
        fig = self.figure(self.W, self.H, 72)
        for ext in ("svg", "pdf"):
            p = masters / f"{slug}.{ext}"; fig.savefig(p, facecolor="white"); out.append(p)
        plt.close(fig)
        if sizes and sizes != "preview":
            table = SIZES[self.orient]
            names = list(table) if sizes == "all" else [x.strip() for x in sizes.split(",")]
            dest = self.dir / slug; dest.mkdir(exist_ok=True)
            for name in names:
                if name not in table:
                    print(f"  ! unknown size {name} for {self.orient}; options: {', '.join(table)}"); continue
                w, h = table[name]
                fig = self.figure(w, h, DPI)
                buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=DPI, facecolor="white"); plt.close(fig)
                p = dest / f"{slug}_{name}.jpg"
                Image.open(buf).convert("RGB").save(p, "JPEG", quality=95, dpi=(DPI, DPI), subsampling=0)
                out.append(p); print(f"  wrote {p.name}")
        return out

    def summary(self):
        lines = [f"Title: {self.cfg.get('title')}   layout: {self.template}/{self.orient}   "
                 f"length: {self.total:.1f} mi{' (scaled to total_miles)' if self.k_miles != 1 else ''}   "
                 f"elevation data: {'yes' if self.has_ele else 'no'}"]
        lines.append(f"Table ({len(self.table_rows)} rows): " + " | ".join(f"{r['_mile']:.1f} {r['name']}" for r in self.table_rows))
        lines += [f"WARNING: {w}" for w in self.warnings]
        return "\n".join(lines)

# ------------------------------------------------------------------ commands
def cmd_render(a):
    if a.draft:   # watermarked look before Gate 2; never print files
        P = Poster(a.project, draft=True)
        p = P.render()[0]
        print(P.summary()); print(f"Draft preview (watermarked): {p}")
        return
    if not is_approved(a.project):   # Gate 2 must be passed first (spec 03)
        sys.exit(f"STOPPED: point list is {approval_status(a.project)}. "
                 f"Run: python tp_points.py review {a.project}  then approve with David.")
    P = Poster(a.project)
    files = P.render(a.sizes)
    print(P.summary())
    print(f"Preview: {Path(a.project) / 'preview.png'}")
    if a.sizes != "preview":
        print(f"Print files: {Path(a.project) / P.slug()}")

def main():
    ap = argparse.ArgumentParser(description="Beech Creek Naturals trail poster generator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="re-render a project after editing pois.csv / poster.json")
    r.add_argument("project")
    r.add_argument("--sizes", default="preview", help="'preview' (default), 'all', or e.g. '7x5,14x11'")
    r.add_argument("--draft", action="store_true",
                   help="watermarked DRAFT preview before Gate 2 (draft_preview.png only; no masters or print files)")
    r.set_defaults(func=cmd_render)
    a = ap.parse_args()
    a.func(a)

if __name__ == "__main__":
    main()
