"""Rebuild each closet scene with a true-to-scale frame (16x20 portrait / 20x16 landscape).

Scale comes from the insulated bottle on the bench (~10.5 in tall, ~8% nearer the camera than the wall).
The old frame and hanging cord are painted out with a smooth wall model, a new frame is cut
from the old one (corners kept, bars shortened), and the cord is redrawn from the same nail.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scenes import edges

BOTTLE_PX = {'A1': 130, 'A2': 107, 'B1': 125, 'B2': 100}   # bottle height in scene pixels
NAIL = {'A1': (313, 83), 'A2': (323, 141), 'B1': (462, 24), 'B2': (471, 36)}
PAPER_IN = {'A1': (16, 20), 'B1': (16, 20), 'A2': (20, 16), 'B2': (20, 16)}
BOTTLE_IN, NEAR = 10.5, 0.93


def wall_fit(a, fill, ring):
    """Cubic per-channel fit to wall pixels in `ring` (non-wall objects rejected by colour)."""
    med = np.median(a[ring], 0)
    ok = ring & (np.abs(a - med).max(2) < 22)
    yy, xx = np.nonzero(ok)
    h, w = fill.shape
    def F(x, y):
        X, Y = x / w - .5, y / h - .5
        return np.stack([X ** i * Y ** j for i in range(4) for j in range(4) if i + j <= 3], -1)
    A = F(xx, yy)
    gy, gx = np.mgrid[0:h, 0:w]
    G = F(gx, gy)
    out = np.empty_like(a); resid = []
    for c in range(3):
        coef = np.linalg.lstsq(A, a[yy, xx, c], rcond=None)[0]
        out[..., c] = G @ coef
        resid.append((a[yy, xx, c] - A @ coef).std())
    return out, np.array(resid), ok


def rebuild(k, paper_in=None, seed=0):
    src = Image.open(f'template_closet_{k}.png').convert('RGB')
    a = np.asarray(src).astype(np.float32)
    H, W = a.shape[:2]
    q = np.array(edges(k))
    ix0, iy0 = q[:, 0].min(), q[:, 1].min(); ix1, iy1 = q[:, 0].max(), q[:, 1].max()
    g = a.mean(2)
    # frame border thickness: walk outward from the inner edge until the wall (bright) returns
    row = g[int((iy0 + iy1) / 2)]
    x = int(ix0) - 1
    while row[x] < row[int(ix0) - 25] - 15: x -= 1
    t = int(round(ix0 - x)) + 1
    ox0, oy0, ox1, oy1 = int(round(ix0)) - t, int(round(iy0)) - t, int(round(ix1)) + t, int(round(iy1)) + t
    nx, ny = NAIL[k]

    # ---- 1) paint out old frame + cord
    fill = np.zeros((H, W), bool)
    fill[oy0 - 6:oy1 + 9, ox0 - 6:ox1 + 9] = True
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    d.polygon([(nx, ny), (ox0, oy0 + 2), (ox1, oy0 + 2)], fill=255)
    d.line([(nx, ny), (ox0 + 8, oy0)], fill=255, width=9); d.line([(nx, ny), (ox1 - 8, oy0)], fill=255, width=9)
    fill |= np.asarray(im) > 0
    nail = np.zeros((H, W), bool); nail[ny - 9:ny + 9, nx - 9:nx + 9] = True
    nail = ndi.binary_dilation(g < 70, iterations=2) & nail      # the nail head itself
    fill &= ~nail
    ring = ndi.binary_dilation(fill, iterations=45) & ~ndi.binary_dilation(fill, iterations=3)
    wall, sd, okr = wall_fit(a, fill, ring)
    # seamless: carry the real wall's local offset from the fit into the hole (normalized convolution)
    okr &= ~ndi.binary_dilation(nail, iterations=8)
    D = (a - wall) * okr[..., None]
    wgt = ndi.gaussian_filter(okr.astype(np.float32), 18)[..., None]
    off = np.stack([ndi.gaussian_filter(D[..., c], 18) for c in range(3)], -1) / np.maximum(wgt, 1e-4)
    wall = wall + np.clip(off, -25, 25)
    wall += np.random.default_rng(seed).normal(0, 1, wall.shape) * sd * 0.8
    soft = ndi.gaussian_filter(fill.astype(np.float32), 2)[..., None]
    soft = np.maximum(soft, fill[..., None])
    out = soft * wall + (1 - soft) * a

    # ---- 2) new frame, sliced from the old one
    ppi = BOTTLE_PX[k] / BOTTLE_IN * NEAR
    pw, ph = [int(round(v * ppi)) for v in (paper_in or PAPER_IN[k])]
    cxm, cym = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    nix0, niy0 = int(round(cxm - pw / 2)), int(round(cym - ph / 2))
    nox0, noy0 = nix0 - t, niy0 - t
    fw, fh = pw + 2 * t, ph + 2 * t
    m = 3                                                   # carry a little wall/shadow with the bars
    old = a[oy0 - m:oy1 + m, ox0 - m:ox1 + m]
    OH, OW = old.shape[:2]
    c = t + m
    newf = np.zeros((fh + 2 * m, fw + 2 * m, 3), np.float32)
    NH, NW = newf.shape[:2]
    # corners
    newf[:c, :c] = old[:c, :c]; newf[:c, NW - c:] = old[:c, OW - c:]
    newf[NH - c:, :c] = old[OH - c:, :c]; newf[NH - c:, NW - c:] = old[OH - c:, OW - c:]
    # bars: take the middle stretch of the old bar
    def mid(n_old, n_new):
        s = (n_old - n_new) // 2; return slice(s, s + n_new)
    newf[:c, c:NW - c] = old[:c, c:OW - c][:, mid(OW - 2 * c, NW - 2 * c)]
    newf[NH - c:, c:NW - c] = old[OH - c:, c:OW - c][:, mid(OW - 2 * c, NW - 2 * c)]
    newf[c:NH - c, :c] = old[c:OH - c, :c][mid(OH - 2 * c, NH - 2 * c)]
    newf[c:NH - c, NW - c:] = old[c:OH - c, OW - c:][mid(OH - 2 * c, NH - 2 * c)]
    newf[c:NH - c, c:NW - c] = 250                              # placeholder paper (lit later)
    # outer m px are wall+shadow from the old spot: blend them in softly
    alpha = np.ones((NH, NW), np.float32)
    for i in range(m):
        v = (i + 1) / (m + 1)
        alpha[i, :] = np.minimum(alpha[i, :], v); alpha[NH - 1 - i, :] = np.minimum(alpha[NH - 1 - i, :], v)
        alpha[:, i] = np.minimum(alpha[:, i], v); alpha[:, NW - 1 - i] = np.minimum(alpha[:, NW - 1 - i], v)
    y0, x0 = noy0 - m, nox0 - m
    out[y0:y0 + NH, x0:x0 + NW] = alpha[..., None] * newf + (1 - alpha[..., None]) * out[y0:y0 + NH, x0:x0 + NW]

    # paper lighting: old paper field (text removed) resampled to the new opening
    reg = a[int(iy0) + 1:int(iy1), int(ix0) + 1:int(ix1)]
    gr = reg.mean(2); txt = ndi.binary_dilation(gr < ndi.gaussian_filter(gr, 10) - 6, iterations=12)
    hh, ww = gr.shape; yy, xx = np.mgrid[0:hh, 0:ww]
    def Fp(x, y):
        X, Y = x / ww - .5, y / hh - .5
        return np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y], -1)
    use = ~txt
    use[:6, :] = use[-6:, :] = False; use[:, :6] = use[:, -6:] = False
    paper = np.empty((ph, pw, 3), np.float32)
    py, px = np.mgrid[0:ph, 0:pw]
    for ch in range(3):
        coef = np.linalg.lstsq(Fp(xx[use], yy[use]), reg[..., ch][use], rcond=None)[0]
        paper[..., ch] = Fp(px * ww / pw, py * hh / ph) @ coef
    # inner edge shading copied from the old opening's border rows/cols (frame lip shadow)
    e = 5
    ratio = reg / np.maximum(np.stack([Fp(xx, yy) @ np.linalg.lstsq(Fp(xx[use], yy[use]), reg[..., ch][use], rcond=None)[0]
                                       for ch in range(3)], -1), 1)
    top = np.median(ratio[:e], 1); bot = np.median(ratio[-e:], 1)
    lef = np.median(ratio[:, :e], 0); rig = np.median(ratio[:, -e:], 0)
    paper[:e] *= np.minimum(top, 1)[:, None]; paper[-e:] *= np.minimum(bot, 1)[:, None]
    paper[:, :e] *= np.minimum(lef, 1)[None]; paper[:, -e:] *= np.minimum(rig, 1)[None]
    out[niy0:niy0 + ph, nix0:nix0 + pw] = paper

    # ---- 3) cord from the nail to the new frame's top corners
    # cord colour: darkest pixel per row along the old left cord
    samp = []
    for y in range(ny + 12, oy0 - 6):
        xs = np.arange(max(ox0 - 5, 0), nx - 4)
        j = xs[np.argmin(g[y, xs])]
        samp.append(a[y, j])
    col = np.median(np.array(samp), 0)
    S = 4
    big = Image.new('L', (W * S, H * S), 0); d = ImageDraw.Draw(big)
    ax = 0.04 * fw
    for ex in (nox0 + ax, nox0 + fw - ax):
        d.line([(nx * S, ny * S), (ex * S, (noy0 + 1) * S)], fill=255, width=int(1.6 * S))
    cm = np.asarray(big.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255
    cm[noy0 + 1:, :] = 0
    out = cm * col + (1 - cm) * out
    # nail back on top
    out[nail] = a[nail]
    return np.clip(out, 0, 255), (nix0, niy0, nix0 + pw, niy0 + ph)


if __name__ == '__main__':
    for k in BOTTLE_PX:
        o, box = rebuild(k)
        Image.fromarray(o.astype(np.uint8)).save(f'template_closet_{k}_true_scale.png')
        print(k, box)
