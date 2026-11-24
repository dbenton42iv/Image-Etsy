import sys, os
sys.argv = ['x']
from common import *
import closet
from PIL import ImageDraw, ImageFont

PAPERS = {  # name: (paper, ink)
    'Kraft':         ((196, 160, 118), (48, 36, 26)),
    'Antique_Cream': ((242, 231, 206), (58, 50, 42)),
    'Sage':          ((184, 196, 170), (36, 50, 38)),
    'Forest_Green':  ((40, 62, 48),    (238, 228, 200)),
    'Navy':          ((33, 45, 66),    (238, 233, 220)),
    'Charcoal':      ((46, 46, 46),    (238, 232, 220)),
}
OUT = '/mnt/user-data/outputs/paper_colors'
os.makedirs(OUT, exist_ok=True)


def recolor(img, paper, ink, grain=0):
    v = np.asarray(img.convert('L')).astype(np.float32)[..., None] / 255   # 1 = paper, 0 = ink
    p, k = np.array(paper, np.float32), np.array(ink, np.float32)
    out = k + (p - k) * v
    if grain:
        rng = np.random.default_rng(3)
        n = ndi.gaussian_filter(rng.normal(0, 1, v.shape[:2]), 1.2)[..., None]
        out += n * grain * v
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def label(im, text):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype('/mnt/user-data/uploads/Etsy/trail_poster/fonts/Montserrat-Medium.ttf', 34)
    d.text((im.width // 2, im.height - 14), text.replace('_', ' '), font=f, fill=(40, 40, 40), anchor='mb')
    return im


tiles = []
for name, (p, k) in PAPERS.items():
    g = 10 if name == 'Kraft' else 3
    a = recolor(design('AT_Path', '16x20'), p, k, g)
    h = hero(a)
    save(h, f'{OUT}/AT_Path_{name}_framed_oak.jpg')
    b = recolor(design('Art_Loeb_Trail', '20x16'), p, k, g)
    o = closet.place('B2', b)
    Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(f'{OUT}/Art_Loeb_Trail_{name}_hiking_closet.jpg', quality=90)
    print(name, flush=True)
