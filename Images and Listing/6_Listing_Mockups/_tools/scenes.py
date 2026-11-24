import numpy as np
from PIL import Image
ROUGH = {'A1': (192, 178, 432, 474), 'A2': (171, 229, 473, 447), 'B1': (333, 106, 587, 416), 'B2': (300, 109, 637, 339)}


def edges(k):
    a = np.asarray(Image.open(f'template_closet_{k}.png').convert('RGB')).astype(float).mean(2)
    x0, y0, x1, y1 = ROUGH[k]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    res = {}
    def walk(line, start, step):
        # from inside the white, walk outward until brightness falls below midpoint of paper/frame
        i = start
        paper = np.median(line[start - 15 * step: start - 3 * step: step]) if step > 0 else np.median(line[start + 3: start + 15])
        while 0 < i < len(line) - 1 and line[i] > paper - 40: i += step
        # subpixel: interpolate crossing at paper-40
        return i - step * (line[i] - (paper - 40)) / (line[i] - line[i - step] + 1e-6) * -1
    pts = {s: [] for s in 'LRTB'}
    for t in np.linspace(0.15, 0.85, 15):
        y = int(y0 + t * (y1 - y0)); row = a[y]
        pts['L'].append((walk(row, int(x0 + 20), -1), y)); pts['R'].append((walk(row, int(x1 - 20), 1), y))
        x = int(x0 + t * (x1 - x0)); col = a[:, x]
        pts['T'].append((x, walk(col, int(y0 + 20), -1))); pts['B'].append((x, walk(col, int(y1 - 20), 1)))
    lines = {}
    for s in 'LR':
        P = np.array(pts[s]); m, b = np.polyfit(P[:, 1], P[:, 0], 1); lines[s] = ('x', m, b)
    for s in 'TB':
        P = np.array(pts[s]); m, b = np.polyfit(P[:, 0], P[:, 1], 1); lines[s] = ('y', m, b)
    def inter(v, h):
        _, mv, bv = lines[v]; _, mh, bh = lines[h]
        # x = mv*y+bv ; y = mh*x+bh
        y = (mh * bv + bh) / (1 - mh * mv); x = mv * y + bv; return (x, y)
    return [inter('L', 'T'), inter('R', 'T'), inter('R', 'B'), inter('L', 'B')]


if __name__ == '__main__':
    for k in ROUGH: print(k, [tuple(round(v, 1) for v in p) for p in edges(k)])
