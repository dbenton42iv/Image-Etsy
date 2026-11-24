import os, sys
from common import *
from landscape import build_life_landscape, lamp_mask
from PIL import ImageDraw, ImageFont

OUT = '/mnt/user-data/outputs/mockups'
FONT = '/mnt/user-data/uploads/Etsy/trail_poster/fonts/'
f = lambda n, s: ImageFont.truetype(FONT + f'Montserrat-{n}.ttf', s)

LIFE_P = load(LIFE)
LIFE_L, LW, WIN_L = build_life_landscape()
LAMP_M = lamp_mask(3000, 3000)
SIZES = ['2:3 ratio — 4x6, 8x12, 12x18, 16x24, 20x30, 24x36',
         '3:4 ratio — 6x8, 9x12, 12x16, 18x24',
         '4:5 ratio — 4x5, 8x10, 16x20',
         '11x14   ·   5x7',
         'ISO — A5, A4, A3, A2, A1']


def lifestyle(name, land):
    if land:
        o = composite(LIFE_L, WIN_L, design(name, '14x11'), light=LW)
    else:
        o = composite(LIFE_P, (1343, 844, 2114, 1829), design(name, '11x14'), k=61, blur=12)
    return LAMP_M * LIFE_P + (1 - LAMP_M) * o


# close-up framing per design: (center x, center y) as fractions, square size as fraction of width
DETAIL = {
    'AT_Checklist_Circles': (.47, .33, .82), 'AT_Checklist_Dates': (.45, .35, .62),
    'AT_Checklist_Lines': (.48, .35, .62), 'AT_Path': (.53, .34, .80),
    'Pack_Your_Dreams_Green_Circle': (.5, .5, .92), 'Pack_Your_Dreams_NewPack_Circle': (.5, .5, .92),
    'Pack_Your_Dreams_Sketch_Circle': (.5, .5, .92),
    'Art_Loeb_Trail': (.66, .36, .46), 'Bartram_Trail': (.74, .40, .46),
    'Mountains_to_Sea_Trail_Map': (.79, .62, .40), 'Pack_Your_Dreams_Green': (.63, .50, .60),
    'Pack_Your_Dreams_NewPack': (.28, .50, .52), 'Pack_Your_Dreams_Sketch': (.28, .50, .52),
}


def detail(name, land):
    """Close-up of the print from the 24x36 master (paper tone + light vignette)."""
    im = design(name, '36x24' if land else '24x36')
    fx, fy, fs = DETAIL[name]
    win = int(fs * im.width)
    x0 = int(np.clip(fx * im.width - win / 2, 0, im.width - win))
    y0 = int(np.clip(fy * im.height - win / 2, 0, im.height - win))
    c = im.crop((x0, y0, x0 + win, y0 + win)).resize((3000, 3000), Image.LANCZOS)
    a = np.asarray(c).astype(np.float32) / 255
    paper = np.array([250, 248, 244], np.float32)
    yy, xx = np.mgrid[0:3000, 0:3000]
    vig = 1 - 0.06 * (((xx - 1500) / 1500) ** 2 + ((yy - 1500) / 1500) ** 2)
    noise = np.random.default_rng(2).normal(0, 1.2, (3000, 3000, 1))
    return a * paper * vig[..., None] + noise


def shadowed(card, art, xy):
    """Paste a flat print with a soft drop shadow."""
    sh = Image.new('L', card.size, 0)
    ImageDraw.Draw(sh).rectangle((xy[0] + 18, xy[1] + 28, xy[0] + art.width + 18, xy[1] + art.height + 28), fill=95)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    dark = Image.new('RGB', card.size, (120, 110, 100))
    card.paste(dark, (0, 0), sh)
    card.paste(art, xy)


def digital_card(name, land):
    bg = (244, 241, 236)
    card = Image.new('RGB', (3000, 3000), bg)
    d = ImageDraw.Draw(card)
    ink, soft = (38, 38, 36), (96, 92, 86)
    if land:
        art = design(name, '14x11'); art = art.resize((2100, round(2100 * art.height / art.width)), Image.LANCZOS)
        shadowed(card, art, ((3000 - art.width) // 2, 230))
        y = 230 + art.height + 150; x = 300
        d.text((1500, y), 'INSTANT DOWNLOAD', font=f('ExtraBold', 120), fill=ink, anchor='mt')
        d.text((1500, y + 175), '6 high-resolution JPG files  ·  300 DPI', font=f('Medium', 70), fill=soft, anchor='mt')
        y += 330
        cols = [SIZES[:3], SIZES[3:]]
        for ci, col in enumerate(cols):
            for i, s in enumerate(col):
                d.text((300 + ci * 1500 if ci else 300, y + i * 105), s, font=f('Light', 64), fill=ink)
        d.text((1500, 2860), 'Print at home or at any print shop  ·  No physical item is shipped',
               font=f('Light', 52), fill=soft, anchor='mb')
    else:
        art = design(name, '11x14'); art = art.resize((1330, round(1330 * art.height / art.width)), Image.LANCZOS)
        y0 = (3000 - art.height) // 2 - 60
        shadowed(card, art, (230, y0))
        x = 1750; y = 760
        d.text((x, y), 'INSTANT', font=f('ExtraBold', 150), fill=ink)
        d.text((x, y + 170), 'DOWNLOAD', font=f('ExtraBold', 150), fill=ink)
        d.text((x, y + 420), '6 high-res JPG files', font=f('Medium', 80), fill=soft)
        d.text((x, y + 520), '300 DPI  ·  up to 24x36', font=f('Medium', 70), fill=soft)
        d.line((x, y + 650, x + 1000, y + 650), fill=(200, 194, 186), width=4)
        for i, s in enumerate(SIZES):
            head, _, tail = s.partition(' — ')
            yy = y + 720 + i * 190
            if tail:
                d.text((x, yy), head, font=f('Medium', 64), fill=ink)
                d.text((x, yy + 80), tail, font=f('Light', 54), fill=soft)
            else:
                d.text((x, yy), head, font=f('Medium', 64), fill=ink)
        d.text((1500, 2860), 'Print at home or at any print shop  ·  No physical item is shipped',
               font=f('Light', 52), fill=soft, anchor='mb')
    return np.asarray(card).astype(np.float32)


def frame_crop(arr, land):
    """Crop a hero image to the frame + its shadow (fixed geometry of the template)."""
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return im.crop((200, 440, 2830, 2580) if land else (440, 200, 2580, 2830))


def is_portrait_frame(arr):
    g = arr.mean(2)
    return g[1500, 470] < g[470, 1500]      # frame bar at left-middle -> portrait


def collage(heroes, land):
    """3 framed prints: 2 on top, 1 centered below."""
    card = Image.new('RGB', (3000, 3000), (255, 255, 255))
    crops = [frame_crop(h, land) for h in heroes]
    w = 1350 if land else 1100
    gx, gy = (3000 - 2 * w) // 3, 110
    cs = [c.resize((w, round(w * c.height / c.width)), Image.LANCZOS) for c in crops]
    h = cs[0].height; top = (3000 - 2 * h - gy) // 2
    card.paste(cs[0], (gx, top)); card.paste(cs[1], (2 * gx + w, top))
    card.paste(cs[2], ((3000 - w) // 2, top + h + gy))
    return np.asarray(card).astype(np.float32)


def run(names):
    heroes = {}
    for name in names:
        land = name in LANDSCAPE
        os.makedirs(f'{OUT}/{name}', exist_ok=True)
        h = hero(design(name, '20x16' if land else '16x20'), land)
        heroes[name] = h
        save(h, f'{OUT}/{name}/{name}_01_framed_oak.jpg')
        save(lifestyle(name, land), f'{OUT}/{name}/{name}_02_lifestyle.jpg')
        save(detail(name, land), f'{OUT}/{name}/{name}_03_detail.jpg')
        save(digital_card(name, land), f'{OUT}/{name}/{name}_04_digital_sizes.jpg')
        print('done', name, flush=True)
    return heroes


if __name__ == '__main__':
    names = sys.argv[1:] or PORTRAIT + LANDSCAPE
    run(names)
