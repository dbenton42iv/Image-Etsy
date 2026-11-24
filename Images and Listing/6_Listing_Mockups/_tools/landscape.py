from common import *

# ---- lifestyle (dresser) template geometry, 3000px space ----
FX0, FY0, FX1, FY1 = 1114, 577, 2352, 2092      # frame outer (left, top, right-face start, bottom)
WX0, WY0, WX1, WY1 = 1343, 844, 2114, 1829      # print window
LAMP = (935.27, 1848.01, 295.68)                 # lamp globe circle (cx, cy, r)


def lamp_mask(h, w):
    cx, cy, r = LAMP
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip(r + 0.5 - d, 0, 1)[..., None]   # 1px antialiased edge


def fit_wall(S):
    """Low-order polynomial model of the clean wall around the frame top (per channel)."""
    m = np.zeros(S.shape[:2], bool)
    m[250:400, 500:2700] = True; m[400:950, 500:1020] = True; m[400:950, 2500:2700] = True
    yy, xx = np.nonzero(m)
    sel = np.random.default_rng(0).choice(len(yy), 40000, replace=False); yy, xx = yy[sel], xx[sel]
    def feats(X, Y):
        return np.stack([X ** i * Y ** j for i in range(4) for j in range(4) if i + j <= 3], -1)
    A = feats((xx - 1600) / 1000, (yy - 600) / 500)
    coef = [np.linalg.lstsq(A, S[yy, xx, c], rcond=None)[0] for c in range(3)]
    gy, gx = np.mgrid[0:S.shape[0], 0:S.shape[1]]
    F = feats((gx - 1600) / 1000, (gy - 600) / 500)
    return np.stack([F @ coef[c] for c in range(3)], -1).astype(np.float32)


def stretch(a, w, h):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32)


def build_life_landscape(win_w=1120, win_h=880):
    S = load(LIFE)
    out = S.copy()
    l, t = WX0 - FX0, WY0 - FY0
    b = FY1 - WY1
    nx0 = WX1 - win_w - l          # new frame left outer (frame grows to the left)
    ny0 = WY1 - win_h - t          # new frame top outer
    nwx0, nwy0 = WX1 - win_w, WY1 - win_h

    # 1) wall above the new frame: re-cast the frame's soft top shadow at the new height.
    #    Wall = smooth polynomial C (fit on clean wall) x ratio R (shadow + real texture).
    C = fit_wall(S)
    R = S / C
    dy = ny0 - FY0
    ys0, ys1 = 300, FY0                       # source rows (clean wall .. old frame top)
    xL, xR = nx0 - 160, 2600
    xs = np.arange(xL, xR)
    src = np.where(xs < nx0, FX0 - (nx0 - xs),
          np.where(xs < nwx0, FX0 + (xs - nx0),
          np.where(xs < WX1, WX0 + (xs - nwx0) * (WX1 - WX0) / (WX1 - nwx0), xs)))
    src = np.round(src).astype(int)
    Rn = R[ys0:ys1][:, src]
    new = C[ys0 + dy:ys1 + dy, xL:xR] * Rn
    # feather left/right edges into the untouched image
    fx = np.clip(np.minimum(xs - xL, xR - 1 - xs) / 120.0, 0, 1)[None, :, None]
    fy = np.clip((np.arange(ys0, ys1) - ys0) / 120.0, 0, 1)[:, None, None]
    f = fx * fy
    f = f * f * (3 - 2 * f)                     # smoothstep
    out[ys0 + dy:ys1 + dy, xL:xR] = f * new + (1 - f) * S[ys0 + dy:ys1 + dy, xL:xR]
    # 2) right side: top-right corner (incl. side face + wall shadow) shifted down; rest untouched
    RX1 = 2545
    tr = S[FY0:WY0, WX1:RX1]
    out[ny0:nwy0, WX1:RX1] = tr
    # feather the corner piece into the untouched frame bar below (grain seam)
    n = 30
    for i in range(n):
        a = (i + 1) / (n + 1)
        out[nwy0 + i, WX1:RX1] = (1 - a) * S[WY0 - 1 + 0, WX1:RX1] * 0 + (1 - a) * out[nwy0 - 1, WX1:RX1] + a * S[nwy0 + i, WX1:RX1]

    # 3) top-left corner
    out[ny0:nwy0, nx0:nwx0] = S[FY0:WY0, FX0:WX0]
    # 4) top edge, stretched along the grain
    out[ny0:nwy0, nwx0:WX1] = stretch(S[FY0:WY0, WX0:WX1], win_w, t)
    # 5) left edge (clean part above the lamp), stretched along the grain
    out[nwy0:WY1, nx0:nwx0] = stretch(S[WY0:1550, FX0:WX0], l, win_h)
    # 6) bottom edge, stretched; bottom-left corner = mirrored bottom-right (hidden by lamp anyway)
    out[WY1:FY1, nwx0:WX1] = stretch(S[WY1:FY1, WX0:WX1], win_w, b)
    out[WY1:FY1, nx0:nwx0] = S[WY1:FY1, WX1:WX1 + l][:, ::-1]

    # 7) window lighting (portrait paper lighting resampled to the new window)
    Lp = lighting(S[WY0:WY1, WX0:WX1], 61, 12)
    Lw = stretch(Lp, win_w, win_h)
    out[nwy0:WY1, nwx0:WX1] = Lw

    # 8) lamp globe back in front
    m = lamp_mask(*S.shape[:2])
    out = m * S + (1 - m) * out
    win = (nwx0, nwy0, WX1, WY1)
    return out, Lw, win


if __name__ == '__main__':
    base, Lw, win = build_life_landscape()
    save(base, 'life_land_blank.jpg')
    o = composite(base, win, design('Art_Loeb_Trail', '14x11'), light=Lw)
    o = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
    m = lamp_mask(3000, 3000)
    # lamp must stay on top of the art as well
    S = load(LIFE)
    o = np.asarray(o).astype(np.float32); o = m * S + (1 - m) * o
    save(o, 't_life_land.jpg')
    Image.open('t_life_land.jpg').crop((500, 400, 2700, 2300)).resize((1100, 950)).save('v3.jpg')
