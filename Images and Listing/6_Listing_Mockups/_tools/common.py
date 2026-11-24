import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None
UP = '/mnt/user-data/uploads/Etsy/Images and Listing/4_Print_Sizes'
HERO = '/mnt/user-data/uploads/95fd39a8-image.png'
LIFE = '/mnt/user-data/uploads/4f7abad0-image.png'

PORTRAIT = ['AT_Checklist_Circles', 'AT_Checklist_Dates', 'AT_Checklist_Lines', 'AT_Path',
            'Pack_Your_Dreams_Green_Circle', 'Pack_Your_Dreams_NewPack_Circle', 'Pack_Your_Dreams_Sketch_Circle']
LANDSCAPE = ['Art_Loeb_Trail', 'Bartram_Trail', 'Mountains_to_Sea_Trail_Map',
             'Pack_Your_Dreams_Green', 'Pack_Your_Dreams_NewPack', 'Pack_Your_Dreams_Sketch']


def design(name, size):
    return Image.open(f'{UP}/{name}/{name}_{size}.jpg').convert('RGB')


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32)


def lighting(region, k=41, blur=6):
    """Paper lighting of a photographed print: strip the old artwork (dark, thin)
    with a per-channel max filter, then smooth."""
    out = np.empty_like(region)
    for c in range(3):
        m = ndi.maximum_filter(region[..., c], size=k)
        out[..., c] = ndi.gaussian_filter(m, blur)
    return out


def fit_cover(img, w, h):
    """Scale to cover w x h, center-crop (crops only white margin when ratios are close)."""
    s = max(w / img.width, h / img.height)
    r = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (r.width - w) // 2, (r.height - h) // 2
    return r.crop((x, y, x + w, y + h))


def composite(base, box, art, light=None, k=41, blur=6):
    """Multiply artwork into base[box] using the paper lighting of that region."""
    x0, y0, x1, y1 = box
    reg = base[y0:y1, x0:x1]
    L = lighting(reg, k, blur) if light is None else light
    a = np.asarray(fit_cover(art, x1 - x0, y1 - y0)).astype(np.float32) / 255.0
    out = base.copy()
    out[y0:y1, x0:x1] = a * L
    return out


def save(arr, path, size=3000, q=90):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if im.width != size:
        im = im.resize((size, round(im.height * size / im.width)), Image.LANCZOS)
    im.save(path, quality=q, optimize=True, subsampling=0)


def lighting_clean(region, band=70, k=121, sigma=60):
    """Smooth paper field + 1-D edge falloff measured along each edge (removes old-art residue)."""
    h, w, _ = region.shape
    out = np.empty_like(region)
    for c in range(3):
        ch = region[..., c]
        field = ndi.gaussian_filter(ndi.maximum_filter(ch, size=k), sigma)
        ratio = ch / np.maximum(field, 1)
        f = np.ones((h, w), np.float32)
        # edge profiles (median along edge, middle 60% of the edge)
        a, b = int(w * .2), int(w * .8)
        top = np.median(ratio[:band, a:b], axis=1); bot = np.median(ratio[h - band:, a:b], axis=1)
        a, b = int(h * .2), int(h * .8)
        lef = np.median(ratio[a:b, :band], axis=0); rig = np.median(ratio[a:b, w - band:], axis=0)
        f[:band, :] *= np.minimum(top, 1)[:, None]
        f[h - band:, :] *= np.minimum(bot, 1)[:, None]
        f[:, :band] *= np.minimum(lef, 1)[None, :]
        f[:, w - band:] *= np.minimum(rig, 1)[None, :]
        out[..., c] = field * f
    return out


# ---- hero (frame on white) ----
HERO_BOX = (557, 322, 2439, 2680)


def hero(art, landscape=False):
    H = load(HERO)
    if landscape:
        H = np.ascontiguousarray(H.transpose(1, 0, 2))     # landscape frame; shadow stays bottom/right
        x0, y0, x1, y1 = HERO_BOX
        box = (y0, x0, y1, x1)
    else:
        box = HERO_BOX
    x0, y0, x1, y1 = box
    Lc = lighting_clean(H[y0:y1, x0:x1])
    return composite(H, box, art, light=Lc)
