import sys; sys.argv = ['x']
from build_all import *
B = {'Bundle_AT_Checklist_Trio': ['AT_Checklist_Circles', 'AT_Checklist_Dates', 'AT_Checklist_Lines'],
     'Bundle_AT_Complete': ['AT_Checklist_Circles', 'AT_Checklist_Dates', 'AT_Checklist_Lines', 'AT_Path'],
     'Bundle_Carolina_Trail_Maps': ['Art_Loeb_Trail', 'Bartram_Trail', 'Mountains_to_Sea_Trail_Map'],
     'Bundle_Pack_Your_Dreams': ['Pack_Your_Dreams_Green', 'Pack_Your_Dreams_NewPack', 'Pack_Your_Dreams_Sketch']}
os.makedirs(f'{OUT}/_Bundles', exist_ok=True)
for b, ns in B.items():
    hs = [load(f'{OUT}/{n}/{n}_01_framed_oak.jpg') for n in ns]
    land = ns[0] in LANDSCAPE
    if len(ns) == 4:
        card = Image.new('RGB', (3000, 3000), 'white')
        cs = [frame_crop(h, False) for h in hs]; w = 1180
        cs = [c.resize((w, round(w * c.height / c.width)), Image.LANCZOS) for c in cs]
        h = cs[0].height; top = (3000 - 2 * h - 110) // 2; left = (3000 - 2 * w - 160) // 2
        for i, c in enumerate(cs):
            card.paste(c, (left + (i % 2) * (w + 160), top + (i // 2) * (h + 110)))
        arr = np.asarray(card).astype(np.float32)
    else:
        arr = collage(hs, land)
    save(arr, f'{OUT}/_Bundles/{b}.jpg'); print(b)
