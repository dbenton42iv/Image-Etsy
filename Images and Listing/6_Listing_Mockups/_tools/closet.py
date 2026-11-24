import sys, os
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from scenes import edges
TRUE_BOX = {'A1': (220, 211, 404, 441), 'A2': (227, 261, 417, 413), 'B1': (371, 151, 548, 372), 'B2': (379, 153, 556, 295)}
from common import design, PORTRAIT, LANDSCAPE

Image.MAX_IMAGE_PIXELS = None
OUT = '/mnt/user-data/outputs/mockups'
SC = 3                                   # upscale factor for the scene
SIZES_P = {'16x20': 20 / 16, '11x14': 14 / 11}
SIZES_L = {'20x16': 20 / 16, '14x11': 14 / 11, '36x24': 36 / 24}
SCENES = {'A1': 'P', 'B1': 'P', 'A2': 'L', 'B2': 'L'}
CACHE = {}


def scene(k):
    if k in CACHE: return CACHE[k]
    true = not k.endswith('_orig')
    kk = k.replace('_orig', '')
    im = Image.open(f'template_closet_{kk}_true_scale.png' if true else f'template_closet_{kk}.png').convert('RGB')
    big = im.resize((im.width * SC, im.height * SC), Image.LANCZOS)
    a = np.asarray(big).astype(np.float32)
    if true:
        x0, y0, x1, y1 = TRUE_BOX[kk]
        q = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32) * SC
    else:
        q = np.array(edges(kk), np.float32) * SC + (SC - 1) / 2
    # paper mask (antialiased), inset half a source pixel so the frame lip stays
    c = q.mean(0); qi = c + (q - c) * (1 - 1.2 / np.linalg.norm(q - c, axis=1).mean())
    m = np.zeros(a.shape[:2], np.uint8)
    cv2.fillPoly(m, [np.round(qi * 8).astype(np.int32)], 255, lineType=cv2.LINE_AA, shift=3)
    m = m.astype(np.float32)[..., None] / 255
    # paper lighting: remove placeholder text, keep edge falloff
    x0, y0 = np.floor(qi.min(0)).astype(int) - 4; x1, y1 = np.ceil(qi.max(0)).astype(int) + 4
    reg = a[y0:y1, x0:x1]
    L = np.empty_like(reg)
    inner = cv2.erode(m[y0:y1, x0:x1, 0], np.ones((3, 3)), iterations=40 * SC // 3) > 0.99
    # fit a smooth quadratic field to the paper, ignoring the placeholder text (and a halo around it)
    gray = reg.mean(2)
    loc = ndi.gaussian_filter(gray, 10 * SC)
    text = ndi.binary_dilation(gray < loc - 6, iterations=12 * SC)
    use = inner & ~text
    yy, xx = np.mgrid[0:reg.shape[0], 0:reg.shape[1]]
    X = xx / reg.shape[1] - .5; Y = yy / reg.shape[0] - .5
    F = np.stack([np.ones_like(X), X, Y, X * X, X * Y, Y * Y, X ** 3, Y ** 3], -1)
    w = ndi.gaussian_filter(inner.astype(np.float32), 4 * SC)
    for ch in range(3):
        r = reg[..., ch]
        coef = np.linalg.lstsq(F[use], r[use], rcond=None)[0]
        field = F @ coef
        L[..., ch] = w * field + (1 - w) * np.maximum(r, ndi.maximum_filter(r, size=3))
    light = np.zeros_like(a); light[y0:y1, x0:x1] = L
    CACHE[k] = (a, q, m, light)
    return CACHE[k]


def place(k, art):
    a, q, m, light = scene(k)
    w = np.linalg.norm(q[1] - q[0]); h = np.linalg.norm(q[3] - q[0]); ratio = h / w
    # contain-fit the art onto white paper with the quad's aspect (art keeps its own margins)
    W = 3000; H = round(W * ratio)
    s = min(W / art.width, H / art.height)
    r = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    paper = Image.new('RGB', (W, H), 'white'); paper.paste(r, ((W - r.width) // 2, (H - r.height) // 2))
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    M = cv2.getPerspectiveTransform(src, q)
    warped = cv2.warpPerspective(np.asarray(paper), M, (a.shape[1], a.shape[0]), flags=cv2.INTER_AREA,
                                 borderValue=(255, 255, 255)).astype(np.float32) / 255
    out = m * (warped * light) + (1 - m) * a
    return out


def best(orient, quad_ratio):
    opts = SIZES_P if orient == 'P' else SIZES_L
    return min(opts, key=lambda s: abs(opts[s] - quad_ratio))


def save_scene(k, art, path):
    o = place(k, art)
    Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(path, quality=90, optimize=True)


def run(names):
    for name in names:
        land = name in LANDSCAPE
        d = f'{OUT}/{name}'; os.makedirs(d, exist_ok=True)
        ks = ['A2', 'B2'] if land else ['A1', 'B1']
        art = design(name, '20x16' if land else '16x20')
        for i, k in enumerate(ks):
            save_scene(k, art, f'{d}/{name}_0{5 + i}_hiking_closet_{"ab"[i]}.jpg')
        if land:   # the original wide scene is true to scale for a 36x24 poster
            save_scene('B2_orig', design(name, '36x24'), f'{d}/{name}_07_hiking_closet_36x24.jpg')
        print('done', name, flush=True)


if __name__ == '__main__':
    run(sys.argv[1:] or PORTRAIT + LANDSCAPE)
