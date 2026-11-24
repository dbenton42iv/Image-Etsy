"""Build Etsy listing CSVs for Beech Creek Naturals.

Run:  python 5_Etsy_Listings/_tools/build_listings.py   (from anywhere; paths are relative to the Etsy folder)
Writes CSVs to 5_Etsy_Listings/, bundle ZIPs to 5_Etsy_Listings/digital_files/,
and the Pack Your Dreams sticker sheet to 5_Etsy_Listings/print_files/.
One row per variant (Shopify-style): listing-level fields repeat on every row of the
same listing_handle, so the file imports cleanly into Shop Uploader / BulkListingPro
after a column rename, or can be used as a copy-paste sheet in Etsy's listing editor.
"""
import csv, os, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # the Etsy folder
SIZES_DIR = "4_Print_Sizes"
OUT = os.path.join(ROOT, "5_Etsy_Listings")
os.makedirs(os.path.join(OUT, "digital_files"), exist_ok=True)
os.makedirs(os.path.join(OUT, "print_files"), exist_ok=True)

SHOP = "Beech Creek Naturals"
FEE_PCT, FEE_FIXED = 0.095, 0.45   # 6.5% transaction + 3% processing; $0.25 processing + $0.20 listing

def win(p):  # path as the user sees it, relative to the Etsy folder
    return p.replace("/", "\\")

# ---------------------------------------------------------------- designs
# orient: P = portrait files (24x36, 18x24 ...), L = landscape files (36x24, 24x18 ...)
D = {
 "AT_Checklist_Circles": dict(orient="P", name="Appalachian Trail Checklist (Circles)",
   blurb="A minimalist Appalachian Trail checklist: the whole route from Springer Mountain to Mount Katahdin with a circle beside each of the 14 states to mark off as you go. Shows 2,197.9 miles / 3,537.2 km and the trail's highest (6,643 ft) and lowest (124 ft) points."),
 "AT_Checklist_Dates": dict(orient="P", name="Appalachian Trail Checklist (Dates)",
   blurb="A minimalist Appalachian Trail checklist with every state from Mount Katahdin to Springer Mountain and a line beside each one to write the date you crossed it. Made for thru-hikers and section hikers recording their own hike."),
 "AT_Checklist_Lines": dict(orient="P", name="Appalachian Trail Checklist (Color-In)",
   blurb="An Appalachian Trail checklist you color in: the trail is drawn in light gray so you can trace over each state as you complete it, with a line beside every state for dates or notes. A section hiker's progress tracker."),
 "AT_Path": dict(orient="P", name="Appalachian Trail Path Map",
   blurb="A clean, minimalist line map of the Appalachian Trail from Springer Mountain, Georgia, to Mount Katahdin, Maine, with all 14 states labeled, total distance (2,197.9 miles / 3,537.2 km) and the highest and lowest points."),
 "Art_Loeb_Trail": dict(orient="L", name="Art Loeb Trail Map",
   blurb="A minimalist map of the 30.1-mile Art Loeb Trail in Pisgah National Forest, North Carolina, from Camp Daniel Boone to the Davidson River, with a mileage table for Deep Gap, Shining Rock Gap, Ivestor Gap, Tennent Mountain, Pilot Mountain, Butter Gap Shelter, Cat Gap and more."),
 "Bartram_Trail": dict(orient="L", name="Bartram Trail Map",
   blurb="A minimalist map of the 115.4-mile Bartram Trail from Russell Bridge, Georgia, to Cheoah Bald, North Carolina, with a mileage table for Rabun Bald, the GA/NC line, Wayah Bald, Nantahala Lake, Winding Stairs and other points of interest."),
 "Mountains_to_Sea_Trail_Map": dict(orient="L", name="Mountains-to-Sea Trail Map",
   blurb="A minimalist map of North Carolina's 1,177.6-mile Mountains-to-Sea Trail from the Great Smoky Mountains to the Outer Banks, with a full-length elevation profile and a segment mileage table."),
 "MST_Logo_Black": dict(orient="L", name="MST North Carolina Silhouette (Black)", blurb=""),
 "MST_Logo_Blue": dict(orient="L", name="MST North Carolina Silhouette (Blue)", blurb=""),
 "MST_Logo_Green": dict(orient="L", name="MST North Carolina Silhouette (Green)", blurb=""),
 "MST_Logo_Outline": dict(orient="L", name="MST North Carolina Silhouette (Outline)", blurb=""),
 "Pack_Your_Dreams_Green": dict(orient="L", name="Pack Your Dreams (Green)", blurb="", raster=True),
 "Pack_Your_Dreams_NewPack": dict(orient="L", name="Pack Your Dreams (Line Art)", blurb=""),
 "Pack_Your_Dreams_Sketch": dict(orient="L", name="Pack Your Dreams (Sketch)", blurb=""),
}
MST_BLURB = ("North Carolina's outline with the Mountains-to-Sea Trail route traced in red across the state and a bold MST "
             "in the middle. Comes in four colorways: black, blue, deep green and outline.")
MST_PRINT_NOTE = ("PRINTING TIPS FOR THE MST DESIGNS\n"
    "• Print in color. The red trail line is the heart of the design. On a black-and-white printer it turns dark gray "
    "and disappears into the black and green fills.\n"
    "• The large solid areas of color look best printed at a photo or print shop (Walgreens, Costco, Staples, FedEx Office, Mpix) "
    "on matte paper. Home inkjets can streak or curl the paper on big fills; if printing at home, use the best-quality setting "
    "and heavy matte card stock.\n"
    "• Only have a black-and-white laser printer? Use the Outline version: its trail prints as a clear gray line on white.")
PYD_BLURB = ("A hand-drawn backpack with the words \"Pack your dreams, not your fears.\" For the hiker who's "
             "planning the big trip, or the friend who needs a nudge to go.")
for k in D:
    if k.startswith("MST_Logo"): D[k]["blurb"] = MST_BLURB
    if k.startswith("Pack_Your_Dreams"): D[k]["blurb"] = PYD_BLURB

def size_file(design, ratio):
    """ratio key: '2:3','3:4','4:5','11x14','A','5x7' -> path of the 300-dpi master for that shape"""
    o = D[design]["orient"]
    name = {"2:3": ("24x36", "36x24"), "3:4": ("18x24", "24x18"), "4:5": ("16x20", "20x16"),
            "11x14": ("11x14", "14x11"), "A": ("A1", "A1_landscape"), "5x7": ("5x7", "7x5")}[ratio]
    tag = name[0] if o == "P" else name[1]
    return f"{SIZES_DIR}/{design}/{design}_{tag}.jpg"

# print size (portrait wording) -> ratio file
PRINT_SIZES = [("8x10", "4:5"), ("11x14", "11x14"), ("12x18", "2:3"), ("16x20", "4:5"), ("18x24", "3:4"), ("24x36", "2:3")]
def size_label(design, s):
    if D[design]["orient"] == "L":
        a, b = s.split("x"); return f"{b}x{a} in"
    return f"{s} in"

# ---------------------------------------------------------------- pricing
# Unframed: Artelo published US cost (production + shipping) as the floor; Prodigi runs higher -> confirm.
UNFRAMED = {"8x10": (24, 4.06 + 4.91), "11x14": (29, 5.70 + 4.91), "12x18": (32, 6.71 + 4.91),
            "16x20": (39, 8.40 + 4.91), "18x24": (45, 12.62 + 4.91), "24x36": (59, 15.45 + 8.10)}
# Framed: Artelo does not publish framed prices; these are ESTIMATES to replace from the Artelo configurator.
FRAMED = {"8x10": (59, 24.0), "11x14": (79, 32.0), "12x18": (89, 38.0), "16x20": (109, 47.0), "18x24": (129, 56.0)}

def profit(price, cost, ship=0.0):
    """ship = shipping the buyer pays (Etsy takes its % on shipping too)"""
    rev = price + ship
    return round(rev - cost - rev * FEE_PCT - FEE_FIXED, 2)

# ---------------------------------------------------------------- tags
TAGS = {
 "AT_CHECK": ["appalachian trail", "AT checklist", "thru hiker gift", "AT poster", "hiking checklist",
              "springer to katahdin", "AT thru hike", "hiker gift", "trail map print", "backpacking gift",
              "minimalist map", "AT state map", "section hiker"],
 "AT_Path": ["appalachian trail", "AT map print", "thru hiker gift", "AT poster", "trail map art",
             "springer to katahdin", "minimalist map", "hiker gift", "backpacking gift", "hiking wall art",
             "AT thru hike", "trail line art", "hiking poster"],
 "Art_Loeb_Trail": ["art loeb trail", "pisgah forest", "trail map print", "NC hiking gift", "hiker gift",
                    "shining rock", "backpacking gift", "minimalist map", "blue ridge hiking", "brevard nc",
                    "hiking wall art", "western nc art", "mileage map"],
 "Bartram_Trail": ["bartram trail", "trail map print", "NC hiking gift", "georgia hiking", "hiker gift",
                   "nantahala", "backpacking gift", "minimalist map", "rabun bald", "wayah bald",
                   "hiking wall art", "western nc art", "mileage map"],
 "Mountains_to_Sea_Trail_Map": ["mountains to sea", "MST trail map", "NC trail map", "north carolina art",
                    "hiker gift", "thru hiker gift", "backpacking gift", "minimalist map", "elevation profile",
                    "hiking wall art", "NC hiking gift", "section hiker", "trail map print"],
 "MST_LOGO": ["mountains to sea", "MST trail", "north carolina", "NC state outline", "hiker gift",
              "NC hiking gift", "thru hiker gift", "backpacking gift", "minimalist NC art", "trail lover gift",
              "NC outdoors", "hiking decor", "state silhouette"],
 "PYD": ["pack your dreams", "backpacking gift", "hiker gift", "hiking quote", "adventure quote",
         "thru hiker gift", "backpack art", "outdoor lover gift", "camping gift", "travel quote",
         "inspirational hike", "trail gift", "hand drawn pack"],
}
def tags_for(design):
    if design.startswith("AT_Checklist"): return TAGS["AT_CHECK"]
    if design.startswith("MST_Logo"): return TAGS["MST_LOGO"]
    if design.startswith("Pack_Your_Dreams"): return TAGS["PYD"]
    return TAGS[design]
def with_product_tags(tags, extra):
    """replace the last len(extra) tags with product-type tags, keep 13 total"""
    t = [x for x in tags if x not in extra][: 13 - len(extra)] + extra
    return t[:13]

# ---------------------------------------------------------------- common text
DISCLAIM = ("An independent {shop} design, not affiliated with or endorsed by any trail organization. "
            "For decoration and keepsakes; not for navigation.").format(shop=SHOP).replace("design, not affiliated with or endorsed by", "design, not affiliated with or endorsed by")
PARTNER_LINE = "Designed by {shop}. Printed and shipped by our production partner, {p}."

COLUMNS = ["listing_handle", "product_family", "listing_type", "production_partner", "partner_product",
           "title", "description", "tags", "materials", "etsy_category", "who_made", "when_made",
           "is_supply", "shop_section", "processing_time", "shipping_profile",
           "variation_1_name", "variation_1_value", "variation_2_name", "variation_2_value",
           "sku", "price_usd", "buyer_shipping_usd", "quantity", "est_cost_usd", "cost_status", "est_profit_usd",
           "listing_photos", "print_file_for_partner", "digital_files", "status", "notes"]
ROWS = {}   # family -> list
def add(family, **kw):
    row = {c: "" for c in COLUMNS}
    row.update(product_family=family, who_made="I did", is_supply="No", buyer_shipping_usd=0, quantity=kw.pop("quantity", 999))
    row.update(kw)
    if isinstance(row["tags"], list): row["tags"] = ", ".join(row["tags"])
    ROWS.setdefault(family, []).append(row)

def photos(*paths):
    return " | ".join(win(p) for p in paths)

# ================================================================ 1. DIGITAL
def make_zip(zip_name, designs, include_sizes=True, extra_guide=""):
    zpath = f"5_Etsy_Listings/digital_files/{zip_name}"
    full = os.path.join(ROOT, zpath)
    with zipfile.ZipFile(full, "w", zipfile.ZIP_STORED) as z:
        for d in designs:
            for r in ["2:3", "3:4", "4:5", "11x14", "A", "5x7"]:
                f = size_file(d, r)
                z.write(os.path.join(ROOT, f), f"{d}/{os.path.basename(f)}")
        z.writestr("HOW_TO_PRINT.txt", PRINT_GUIDE + ("\n" + extra_guide.replace("• ", "- ") + "\n" if extra_guide else ""))
    mb = os.path.getsize(full) / 1e6
    if mb > 20: print("WARNING zip over Etsy 20MB limit:", zpath, mb)
    return zpath, mb

PRINT_GUIDE = """HOW TO PRINT YOUR {shop} DOWNLOAD

Every file is a 300 DPI JPG. Pick the file whose shape matches your frame:
  24x36 file  -> 4x6, 8x12, 12x18, 16x24, 20x30, 24x36
  18x24 file  -> 6x8, 9x12, 12x16, 18x24
  16x20 file  -> 4x5, 8x10, 16x20
  11x14 file  -> 11x14
  A1 file     -> A5, A4, A3, A2, A1
  5x7 file    -> 5x7
(Landscape designs use the same files turned sideways, e.g. 36x24.)

Every design has a white border sized for framing: at least 1/2 inch on every side
at the smallest print size, more on bigger prints. A mat or frame lip can overlap
the paper by 1/4 inch without touching the artwork. Print at 100% ("actual size"),
not "fit to page" or "borderless", so the border stays even.

Print at home on matte card stock, or upload to any print shop (Staples, FedEx Office,
Walgreens, Costco, Mpix) and choose matte paper for the best look.
For personal use only. Please don't resell or share the files.
""".format(shop=SHOP)

DIGITAL_NOTE = ("INSTANT DOWNLOAD. No physical item will be shipped.\n\nYou get high-resolution 300 DPI JPGs that print sharp at every common frame size:\n"
                "• 2:3 ratio: 4x6, 8x12, 12x18, 16x24, 20x30, 24x36\n• 3:4 ratio: 6x8, 9x12, 12x16, 18x24\n"
                "• 4:5 ratio: 4x5, 8x10, 16x20\n• 11x14\n• ISO: A5, A4, A3, A2, A1\n• 5x7\n\n"
                "Print at home or at any print shop; matte paper looks best. Colors may vary slightly by printer and screen. "
                "For personal use only; please don't resell or share the files.")

singles = ["AT_Checklist_Circles", "AT_Checklist_Dates", "AT_Checklist_Lines", "AT_Path", "Art_Loeb_Trail",
           "Bartram_Trail", "Mountains_to_Sea_Trail_Map", "Pack_Your_Dreams_Green", "Pack_Your_Dreams_NewPack",
           "Pack_Your_Dreams_Sketch"]
for d in singles:
    zpath, mb = make_zip(f"{d}_All_Sizes.zip", [d])
    files = [zpath, size_file(d, "4:5"), size_file(d, "11x14"), size_file(d, "3:4"), size_file(d, "2:3")]
    nm = D[d]["name"]
    price = 6.99 if d.startswith("Pack") else 7.99
    title = {
      "AT_Checklist_Circles": "Appalachian Trail Checklist Printable, AT State Checklist Poster, Thru Hiker Gift, Instant Download",
      "AT_Checklist_Dates": "Appalachian Trail Checklist with Dates Printable, AT Thru Hike Log Poster, Hiker Gift, Instant Download",
      "AT_Checklist_Lines": "Appalachian Trail Coloring Checklist Printable, Color In as You Hike, AT Section Hiker Gift, Download",
      "AT_Path": "Appalachian Trail Map Printable, Minimalist AT Poster, Springer to Katahdin Wall Art, Instant Download",
      "Art_Loeb_Trail": "Art Loeb Trail Map Printable, Pisgah Forest NC Hiking Map with Mileage, Hiker Gift, Instant Download",
      "Bartram_Trail": "Bartram Trail Map Printable, Georgia & North Carolina Hiking Map with Mileage, Instant Download",
      "Mountains_to_Sea_Trail_Map": "Mountains-to-Sea Trail Map Printable, NC MST Map with Elevation Profile, Hiker Gift, Download",
      "Pack_Your_Dreams_Green": "Pack Your Dreams Not Your Fears Printable, Hand-Drawn Backpack Hiking Quote Art, Instant Download",
      "Pack_Your_Dreams_NewPack": "Pack Your Dreams Not Your Fears Printable, Backpack Line Art Hiking Quote Poster, Instant Download",
      "Pack_Your_Dreams_Sketch": "Pack Your Dreams Not Your Fears Printable, Sketch Backpack Adventure Quote Art, Instant Download",
    }[d]
    add("01_Digital", listing_handle=f"dl-{d.lower()}", listing_type="Digital (instant download)",
        production_partner="Etsy (instant download)", partner_product="5 files uploaded to Etsy",
        title=title, description=f"{D[d]['blurb']}\n\n{DIGITAL_NOTE}\n\n{DISCLAIM}",
        tags=with_product_tags(tags_for(d), ["printable wall art", "instant download"]),
        materials="digital file, JPG", etsy_category="Art & Collectibles > Prints > Digital Prints",
        when_made="2020 - 2026", shop_section="Printable Downloads", processing_time="Instant",
        shipping_profile="n/a (digital)", sku=f"BCN-DL-{d.upper()}", price_usd=price, est_cost_usd=0,
        cost_status="n/a", est_profit_usd=profit(price, 0),
        listing_photos=photos(size_file(d, "5x7"), size_file(d, "2:3")),
        digital_files=photos(*files), status="Ready to list",
        notes=f"ZIP is {mb:.1f} MB (Etsy limit 20 MB/file, 5 files/listing). Add a frame mockup as photo 1.")

bundles = [
  ("dl-mst-silhouette-all-colors", ["MST_Logo_Black", "MST_Logo_Blue", "MST_Logo_Green", "MST_Logo_Outline"], 9.99,
   "Mountains to Sea Trail Printable Set of 4, NC State Outline MST Wall Art, North Carolina Hiker Gift, Download",
   MST_BLURB + " All four colorways are included.", "MST_LOGO", "MST_Logo_Blue", "Printable Downloads"),
  ("dl-bundle-at-checklist-trio", ["AT_Checklist_Circles", "AT_Checklist_Dates", "AT_Checklist_Lines"], 12.99,
   "Appalachian Trail Checklist Printable Bundle of 3, Circles, Dates & Color-In AT Posters, Thru Hiker Gift",
   "All three Appalachian Trail checklist posters in one download: the circle checklist to mark off each state, the dated log to record when you crossed it, and the color-in version to trace your progress. Springer Mountain to Mount Katahdin, 14 states, 2,197.9 miles.",
   "AT_CHECK", "AT_Checklist_Circles", "Bundles"),
  ("dl-bundle-at-complete", ["AT_Checklist_Circles", "AT_Checklist_Dates", "AT_Checklist_Lines", "AT_Path"], 15.99,
   "Appalachian Trail Printable Collection, 4 AT Posters, Map + 3 Checklists, Thru Hiker Gift, Instant Download",
   "The complete Appalachian Trail set: the minimalist AT path map plus all three checklist posters (circles, dates and color-in). Springer Mountain to Mount Katahdin, 14 states, 2,197.9 miles.",
   "AT_CHECK", "AT_Path", "Bundles"),
  ("dl-bundle-carolina-trail-maps", ["Art_Loeb_Trail", "Bartram_Trail", "Mountains_to_Sea_Trail_Map"], 15.99,
   "North Carolina Trail Maps Printable Bundle, Art Loeb, Bartram & Mountains-to-Sea Trail, NC Hiker Gift",
   "Three Southern Appalachian long trails in one matching minimalist style: the 30.1-mile Art Loeb Trail, the 115.4-mile Bartram Trail and the 1,177.6-mile Mountains-to-Sea Trail, each with its mileage table.",
   "Mountains_to_Sea_Trail_Map", "Art_Loeb_Trail", "Bundles"),
  ("dl-bundle-pack-your-dreams", ["Pack_Your_Dreams_Green", "Pack_Your_Dreams_NewPack", "Pack_Your_Dreams_Sketch"], 11.99,
   "Pack Your Dreams Not Your Fears Printable Set of 3, Backpack Hiking Quote Art Bundle, Instant Download",
   PYD_BLURB + " All three versions are included: the original green, the clean line-art pack and the pencil-sketch pack.",
   "PYD", "Pack_Your_Dreams_NewPack", "Bundles"),
]
for handle, ds, price, title, blurb, tagkey, hero, section in bundles:
    zips = []
    for d in ds:
        zpath, mb = make_zip(f"{d}_All_Sizes.zip", [d], extra_guide=MST_PRINT_NOTE if d.startswith("MST_Logo") else "")
        zips.append(zpath)
    tg = TAGS[tagkey] if tagkey in TAGS else tags_for(tagkey)
    add("01_Digital", listing_handle=handle, listing_type="Digital (instant download)",
        production_partner="Etsy (instant download)", partner_product=f"{len(zips)} ZIP files uploaded to Etsy",
        title=title, description=f"{blurb}\n\nEach design comes as its own ZIP with every size.\n\n{DIGITAL_NOTE}\n\n" + (MST_PRINT_NOTE + "\n\n" if handle.startswith("dl-mst") else "") + DISCLAIM,
        tags=with_product_tags(tg, ["printable bundle", "instant download"]),
        materials="digital file, JPG, ZIP", etsy_category="Art & Collectibles > Prints > Digital Prints",
        when_made="2020 - 2026", shop_section=section, processing_time="Instant",
        shipping_profile="n/a (digital)", sku="BCN-" + handle.upper(), price_usd=price, est_cost_usd=0,
        cost_status="n/a", est_profit_usd=profit(price, 0),
        listing_photos=photos(*[size_file(d, "5x7") for d in ds]), digital_files=photos(*zips),
        status="Ready to list", notes="Make a collage of all designs for photo 1.")

# ================================================================ 2. UNFRAMED PRINTS (Prodigi)
PRODIGI = "Prodigi"
PRINT_DESC = ("PRINT DETAILS\n• Giclée print with archival pigment inks on museum-grade matte fine art paper\n"
              "• Every design keeps a white border, so nothing is trimmed\n• Frame not included\n"
              "• Made to order and shipped flat or rolled in protective packaging\n\n"
              "Want it ready to hang? See the framed version in our shop. Prefer to print it yourself? "
              "The instant download is in our Printable Downloads section.")
unframed = [
  ("print-at-checklist", ["AT_Checklist_Circles", "AT_Checklist_Dates", "AT_Checklist_Lines"], "Style",
   ["Circles", "Dates", "Color-In"],
   "Appalachian Trail Checklist Print, AT State Checklist Poster, Thru Hiker Gift, Giclée Art Print, Unframed",
   "Three Appalachian Trail checklist styles, one listing: CIRCLES has a circle beside each state to mark off; DATES has a line beside each state to write the date you crossed it; COLOR-IN draws the trail in light gray to trace as you finish each state. Springer Mountain to Mount Katahdin, 14 states, 2,197.9 miles.",
   "AT_CHECK", 6),
  ("print-at-path", ["AT_Path"], None, None,
   "Appalachian Trail Map Print, Minimalist AT Poster, Springer to Katahdin Wall Art, Thru Hiker Gift, Unframed",
   D["AT_Path"]["blurb"], "AT_Path", 6),
  ("print-art-loeb", ["Art_Loeb_Trail"], None, None,
   "Art Loeb Trail Map Print, Pisgah National Forest NC Hiking Map with Mileage, Hiker Gift, Unframed Art Print",
   D["Art_Loeb_Trail"]["blurb"], "Art_Loeb_Trail", 6),
  ("print-bartram", ["Bartram_Trail"], None, None,
   "Bartram Trail Map Print, GA to NC Hiking Map with Mileage Table, Minimalist Trail Art, Hiker Gift, Unframed",
   D["Bartram_Trail"]["blurb"], "Bartram_Trail", 6),
  ("print-mst-map", ["Mountains_to_Sea_Trail_Map"], None, None,
   "Mountains-to-Sea Trail Map Print, North Carolina MST Map with Elevation Profile, Hiker Gift, Unframed",
   D["Mountains_to_Sea_Trail_Map"]["blurb"], "Mountains_to_Sea_Trail_Map", 6),
  ("print-mst-silhouette", ["MST_Logo_Black", "MST_Logo_Blue", "MST_Logo_Green", "MST_Logo_Outline"], "Color",
   ["Black", "Blue", "Green", "Outline"],
   "Mountains to Sea Trail Print, NC State Outline MST Wall Art, North Carolina Hiker Gift, Unframed Art Print",
   MST_BLURB, "MST_LOGO", 6),
  ("print-pack-your-dreams", ["Pack_Your_Dreams_Green", "Pack_Your_Dreams_NewPack", "Pack_Your_Dreams_Sketch"], "Style",
   ["Green", "Line Art", "Sketch"],
   "Pack Your Dreams Not Your Fears Print, Hand-Drawn Backpack Hiking Quote Art, Adventure Gift, Unframed",
   PYD_BLURB + " Choose the original green, the clean line-art pack or the pencil-sketch pack.", "PYD", 6),
]
for handle, ds, v1name, v1vals, title, blurb, tagkey, _ in unframed:
    tg = TAGS[tagkey] if tagkey in TAGS else tags_for(tagkey)
    for i, d in enumerate(ds):
        for s, ratio in PRINT_SIZES:
            if D[d].get("raster") and s == "24x36":
                continue  # raster original tops out around 24x18
            price, cost = UNFRAMED[s]
            sl = size_label(d, s)
            row = dict(listing_handle=handle, listing_type="Physical (print on demand)", production_partner=PRODIGI,
                       partner_product="Fine art print, Enhanced Matte Art Paper (giclée)",
                       title=title, description=f"{blurb}\n\n{PRINT_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRODIGI)} Not affiliated with or endorsed by any trail organization. For decoration and keepsakes; not for navigation.",
                       tags=with_product_tags(tg, ["giclee art print"]),
                       materials="fine art paper, archival pigment ink", etsy_category="Art & Collectibles > Prints > Giclée",
                       when_made="Made to order", shop_section="Art Prints", processing_time="1-3 business days",
                       shipping_profile="POD - free US shipping", sku=f"BCN-PR-{d.upper()}-{s}",
                       price_usd=price, est_cost_usd=round(cost, 2),
                       cost_status="Floor = Artelo published cost; confirm Prodigi cost in its dashboard",
                       est_profit_usd=profit(price, cost),
                       listing_photos=photos(size_file(d, "5x7")), print_file_for_partner=win(size_file(d, ratio)),
                       status="List after sample approved")
            if v1name:
                row.update(variation_1_name=v1name, variation_1_value=v1vals[i], variation_2_name="Size", variation_2_value=sl)
            else:
                row.update(variation_1_name="Size", variation_1_value=sl)
            add("02_Art_Prints_Unframed", **row)

# ================================================================ 3. FRAMED (Artelo)
ARTELO = "Artelo"
FRAME_DESC = ("FRAME DETAILS\n• Premium solid oak frame (black, natural or white) with real glass\n"
              "• Archival matte print, framed and ready to hang, hanging hardware included\n"
              "• Made to order in the USA and shipped in protective packaging\n\n"
              "Unframed prints and instant downloads are also in our shop.")
FRAMES = ["Black", "Natural Oak", "White"]
framed = [
  ("framed-at-checklist-circles", "AT_Checklist_Circles", "AT_CHECK",
   "Framed Appalachian Trail Checklist, AT State Checklist Poster in Oak Frame, Thru Hiker Gift, Ready to Hang"),
  ("framed-at-checklist-dates", "AT_Checklist_Dates", "AT_CHECK",
   "Framed Appalachian Trail Checklist with Dates, AT Thru Hike Log in Oak Frame, Hiker Gift, Ready to Hang"),
  ("framed-at-path", "AT_Path", "AT_Path",
   "Framed Appalachian Trail Map, Minimalist AT Wall Art in Oak Frame, Springer to Katahdin, Ready to Hang"),
  ("framed-art-loeb", "Art_Loeb_Trail", "Art_Loeb_Trail",
   "Framed Art Loeb Trail Map, Pisgah Forest NC Hiking Map with Mileage, Oak Frame, Ready to Hang Hiker Gift"),
  ("framed-bartram", "Bartram_Trail", "Bartram_Trail",
   "Framed Bartram Trail Map, GA to NC Hiking Map with Mileage Table, Oak Frame, Ready to Hang Hiker Gift"),
  ("framed-mst-map", "Mountains_to_Sea_Trail_Map", "Mountains_to_Sea_Trail_Map",
   "Framed Mountains-to-Sea Trail Map, NC MST Map with Elevation Profile, Oak Frame, Ready to Hang"),
  ("framed-pack-your-dreams", "Pack_Your_Dreams_NewPack", "PYD",
   "Framed Pack Your Dreams Not Your Fears Print, Backpack Hiking Quote Art, Oak Frame, Ready to Hang Gift"),
]
for handle, d, tagkey, title in framed:
    tg = TAGS[tagkey] if tagkey in TAGS else tags_for(tagkey)
    for s, (price, cost) in FRAMED.items():
        ratio = dict(PRINT_SIZES)[s]
        for fr in FRAMES:
            add("03_Framed_Prints", listing_handle=handle, listing_type="Physical (print on demand)",
                production_partner=ARTELO, partner_product="Framed print, Premium oak frame, glass, matte paper, ready-to-hang",
                title=title, description=f"{D[d]['blurb']}\n\n{FRAME_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=ARTELO)} Not affiliated with or endorsed by any trail organization. For decoration and keepsakes; not for navigation.",
                tags=with_product_tags(tg, ["framed wall art"]),
                materials="solid oak frame, glass, matte paper, archival ink",
                etsy_category="Art & Collectibles > Prints > Giclée", when_made="Made to order",
                shop_section="Framed Prints", processing_time="2-4 business days",
                shipping_profile="POD - free US shipping", sku=f"BCN-FR-{d.upper()}-{s}-{fr.split()[0].upper()}",
                variation_1_name="Size", variation_1_value=size_label(d, s), variation_2_name="Frame", variation_2_value=fr,
                price_usd=price, est_cost_usd=cost, cost_status="ESTIMATE - replace with Artelo configurator cost",
                est_profit_usd=profit(price, cost), listing_photos=photos(size_file(d, "5x7")),
                print_file_for_partner=win(size_file(d, ratio)), status="List after sample approved")

# ================================================================ 4. STICKERS (Printful)
PRINTFUL = "Printful"
STK_DESC = ("STICKER DETAILS\n• Kiss-cut vinyl sticker on a backing sheet\n• Fade- and water-resistant; good for water bottles, "
            "laptops, bear canisters and car windows\n• Made to order and shipped flat")
stickers = [("Pack_Your_Dreams_Green", "Green"), ("Pack_Your_Dreams_NewPack", "Line Art"), ("Pack_Your_Dreams_Sketch", "Sketch")]
STK_SIZES = [("4 in", 7.00, 3.25 + 3.99), ("5.5 in", 8.50, 3.75 + 3.99)]   # 3 in dropped: loses money after shipping
STK_SHIP = 1.99
for d, style in stickers:
    f = f"{SIZES_DIR}/_Stickers/{d}_Sticker_4500px.png"
    for sz, price, cost in STK_SIZES:
        add("04_Stickers", listing_handle="sticker-pack-your-dreams", listing_type="Physical (print on demand)",
            production_partner=PRINTFUL, partner_product="Kiss-cut stickers",
            title="Pack Your Dreams Not Your Fears Sticker, Backpacking Vinyl Sticker, Hiker Water Bottle Decal, Hiking Gift",
            description=f"{PYD_BLURB} A round badge sticker in three styles.\n\n{STK_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
            tags=with_product_tags(TAGS["PYD"], ["hiking sticker", "water bottle decal", "vinyl sticker"]),
            materials="vinyl", etsy_category="Paper & Party Supplies > Paper > Stickers, Labels & Tags > Stickers",
            when_made="Made to order", shop_section="Stickers & Gear", processing_time="2-5 business days",
            shipping_profile="Stickers - $1.99 shipping", buyer_shipping_usd=STK_SHIP, sku=f"BCN-STK-{d.upper()}-{sz.split()[0]}",
            variation_1_name="Style", variation_1_value=style, variation_2_name="Size", variation_2_value=sz,
            price_usd=price, est_cost_usd=round(cost, 2), cost_status="Printful list price + US shipping (approx.)",
            est_profit_usd=profit(price, cost, STK_SHIP), listing_photos=photos(f), print_file_for_partner=win(f),
            status="List after sample approved",
            notes="Single POD stickers are near break-even; profit comes from multi-item orders. Set the Stickers shipping profile to $1.99 first item, $0.25 each additional.")

# sticker sheet: build the file
try:
    from PIL import Image
    W, H = 1749, 2481   # Printful kiss-cut sticker sheet, 5.83 x 8.27 in @ 300 dpi
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    disc = 1050
    spots = [((W - disc) // 2, 120), (90, 1290), (W - disc - 90, 1290)]
    # shrink the bottom two so they fit side by side with a gap
    small = 760
    spots = [((W - disc) // 2, 110, disc), (100, 1330, small), (W - small - 100, 1330, small)]
    for (d, _), (x, y, s) in zip(stickers, spots):
        im = Image.open(os.path.join(ROOT, f"{SIZES_DIR}/_Stickers/{d}_Sticker_4500px.png")).convert("RGBA").resize((s, s), Image.LANCZOS)
        sheet.alpha_composite(im, (x, y))
    sheet_path = "5_Etsy_Listings/print_files/Pack_Your_Dreams_Sticker_Sheet_1749x2481.png"
    sheet.save(os.path.join(ROOT, sheet_path), dpi=(300, 300))
except Exception as e:
    sheet_path = ""
    print("sticker sheet not built:", e)
add("04_Stickers", listing_handle="sticker-sheet-pack-your-dreams", listing_type="Physical (print on demand)",
    production_partner=PRINTFUL, partner_product="Kiss-cut sticker sheet (5.83 x 8.27 in)",
    title="Pack Your Dreams Sticker Sheet, 3 Backpacking Stickers, Hiker Gift, Vinyl Hiking Stickers for Water Bottle",
    description=f"All three Pack Your Dreams badges on one sheet: the original green, the line-art pack and the sketch pack. {PYD_BLURB}\n\n"
                f"STICKER DETAILS\n• Kiss-cut vinyl stickers on one 5.83 x 8.27 in sheet\n• Fade- and water-resistant\n• Made to order and shipped flat\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
    tags=with_product_tags(TAGS["PYD"], ["sticker sheet", "hiking sticker", "vinyl sticker"]),
    materials="vinyl", etsy_category="Paper & Party Supplies > Paper > Stickers, Labels & Tags > Stickers",
    when_made="Made to order", shop_section="Stickers & Gear", processing_time="2-5 business days",
    shipping_profile="Stickers - $1.99 shipping", buyer_shipping_usd=STK_SHIP, sku="BCN-STKSHEET-PYD", price_usd=11.00, est_cost_usd=round(4.50 + 4.99, 2),
    cost_status="Printful list price + US shipping (approx.)", est_profit_usd=profit(11.00, 4.50 + 4.99, STK_SHIP),
    listing_photos=photos(sheet_path) if sheet_path else "", print_file_for_partner=win(sheet_path),
    status="List after sample approved", notes="Sheet layout built automatically; check it in Printful's sticker-sheet editor before ordering the sample.")
for color in ["Black", "Blue", "Green", "Outline"]:
    add("04_Stickers", listing_handle="sticker-mst-silhouette", listing_type="Physical (print on demand)",
        production_partner=PRINTFUL, partner_product="Kiss-cut stickers",
        title="Mountains to Sea Trail Sticker, NC State Outline MST Vinyl Decal, North Carolina Hiker Water Bottle Sticker",
        description=f"{MST_BLURB}\n\n{STK_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
        tags=with_product_tags(TAGS["MST_LOGO"], ["hiking sticker", "water bottle decal", "vinyl sticker"]),
        materials="vinyl", etsy_category="Paper & Party Supplies > Paper > Stickers, Labels & Tags > Stickers",
        when_made="Made to order", shop_section="Stickers & Gear", processing_time="2-5 business days",
        shipping_profile="Stickers - $1.99 shipping", buyer_shipping_usd=STK_SHIP, sku=f"BCN-STK-MST-{color.upper()}-4",
        variation_1_name="Color", variation_1_value=color, variation_2_name="Size", variation_2_value="4 in",
        price_usd=7.00, est_cost_usd=round(3.25 + 3.99, 2), cost_status="Printful list price + US shipping (approx.)",
        est_profit_usd=profit(7.00, 3.25 + 3.99, STK_SHIP), listing_photos=photos(size_file(f"MST_Logo_{color}", "5x7")),
        print_file_for_partner="NEEDED: transparent PNG of the NC silhouette only (export from _Masters_2026\\MST Trail (2026).pdf)",
        status="BLOCKED - needs transparent art", notes="The print JPGs have a white page and the trail name; a sticker needs the shape alone.")

# ================================================================ 5. APPAREL (Printful)
TEE_DESC = ("SHIRT DETAILS\n• Comfort Colors 1717 garment-dyed heavyweight tee, 100% ring-spun cotton\n"
            "• Relaxed unisex fit; soft, lived-in feel\n• Design printed direct-to-garment on the front\n"
            "• Size up for an oversized fit; see the size chart in the photos\n• Made to order")
TEE_SIZES = [("S", 32), ("M", 32), ("L", 32), ("XL", 32), ("2XL", 35), ("3XL", 37)]
TEE_COST = {"S": 15.60, "M": 15.60, "L": 15.60, "XL": 15.60, "2XL": 17.60, "3XL": 19.60}
tees = [
  ("tee-pack-your-dreams-lineart", "3_Pack_Your_Dreams/Pack_Your_Dreams_NewPack_transparent.png", "Line Art",
   ["Ivory", "White", "Bay", "Chambray"]),
  ("tee-pack-your-dreams-sketch", "3_Pack_Your_Dreams/Pack_Your_Dreams_Sketch_transparent.png", "Sketch",
   ["Ivory", "White", "Bay", "Chambray"]),
  ("tee-pack-your-dreams-green", "3_Pack_Your_Dreams/Pack_Your_Dreams_transparent_4500px.png", "Green",
   ["Ivory", "White"]),
]
for handle, f, style, colors in tees:
    for c in colors:
        for sz, price in TEE_SIZES:
            cost = TEE_COST[sz] + 4.75
            add("05_Apparel", listing_handle=handle, listing_type="Physical (print on demand)",
                production_partner=PRINTFUL, partner_product="Comfort Colors 1717 garment-dyed tee, DTG front",
                title=f"Pack Your Dreams Not Your Fears Shirt, {style} Backpack Hiking Tee, Comfort Colors Hiker Gift",
                description=f"{PYD_BLURB}\n\n{TEE_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
                tags=with_product_tags(TAGS["PYD"], ["hiking shirt", "comfort colors tee", "backpacking shirt"]),
                materials="cotton", etsy_category="Clothing > Gender-Neutral Adult Clothing > Tops & Tees > T-shirts",
                when_made="Made to order", shop_section="Apparel", processing_time="2-5 business days",
                shipping_profile="POD - free US shipping", sku=f"BCN-TEE-PYD-{style.split()[0].upper()}-{c.upper()}-{sz}",
                variation_1_name="Color", variation_1_value=c, variation_2_name="Size", variation_2_value=sz,
                price_usd=price, est_cost_usd=round(cost, 2), cost_status="Printful list price + US shipping (approx.)",
                est_profit_usd=profit(price, cost), listing_photos=photos(f), print_file_for_partner=win(f),
                status="List after sample approved",
                notes="Dark line art needs light shirt colors. Confirm each color exists for CC1717 in Printful.")
for c in ["Ivory", "White", "Bay"]:
    for sz, price in TEE_SIZES:
        cost = TEE_COST[sz] + 4.75
        add("05_Apparel", listing_handle="tee-mst-silhouette", listing_type="Physical (print on demand)",
            production_partner=PRINTFUL, partner_product="Comfort Colors 1717 garment-dyed tee, DTG front",
            title="Mountains to Sea Trail Shirt, NC State Outline MST Tee, North Carolina Hiker Gift, Comfort Colors",
            description=f"{MST_BLURB}\n\n{TEE_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
            tags=with_product_tags(TAGS["MST_LOGO"], ["hiking shirt", "comfort colors tee", "NC shirt"]),
            materials="cotton", etsy_category="Clothing > Gender-Neutral Adult Clothing > Tops & Tees > T-shirts",
            when_made="Made to order", shop_section="Apparel", processing_time="2-5 business days",
            shipping_profile="POD - free US shipping", sku=f"BCN-TEE-MST-{c.upper()}-{sz}",
            variation_1_name="Color", variation_1_value=c, variation_2_name="Size", variation_2_value=sz,
            price_usd=price, est_cost_usd=round(cost, 2), cost_status="Printful list price + US shipping (approx.)",
            est_profit_usd=profit(price, cost), listing_photos=photos(size_file("MST_Logo_Black", "5x7")),
            print_file_for_partner="NEEDED: transparent PNG of MST silhouette + MOUNTAINS-TO-SEA TRAIL text",
            status="BLOCKED - needs transparent art")

# ================================================================ 6. MUGS + TOTE (Printful)
MUG_DESC = ("MUG DETAILS\n• White glossy ceramic mug\n• Dishwasher and microwave safe\n• Design printed on both sides\n• Made to order")
MUG_SIZES = [("11 oz", 18.00, 6.07 + 6.49), ("15 oz", 21.00, 8.95 + 6.49)]
for d, style, f in [("Pack_Your_Dreams_Green", "Green", "3_Pack_Your_Dreams/Pack_Your_Dreams_transparent_4500px.png"),
                    ("Pack_Your_Dreams_NewPack", "Line Art", "3_Pack_Your_Dreams/Pack_Your_Dreams_NewPack_transparent.png"),
                    ("Pack_Your_Dreams_Sketch", "Sketch", "3_Pack_Your_Dreams/Pack_Your_Dreams_Sketch_transparent.png")]:
    for sz, price, cost in MUG_SIZES:
        add("06_Mugs_Totes", listing_handle="mug-pack-your-dreams", listing_type="Physical (print on demand)",
            production_partner=PRINTFUL, partner_product="White glossy mug",
            title="Pack Your Dreams Not Your Fears Mug, Backpacking Coffee Mug, Hiker Gift, Hiking Quote Camp Mug",
            description=f"{PYD_BLURB}\n\n{MUG_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
            tags=with_product_tags(TAGS["PYD"], ["hiking mug", "coffee mug gift"]),
            materials="ceramic", etsy_category="Home & Living > Kitchen & Dining > Drink & Barware > Drinkware > Mugs",
            when_made="Made to order", shop_section="Stickers & Gear", processing_time="2-5 business days",
            shipping_profile="POD - free US shipping", sku=f"BCN-MUG-PYD-{style.split()[0].upper()}-{sz.split()[0]}",
            variation_1_name="Style", variation_1_value=style, variation_2_name="Size", variation_2_value=sz,
            price_usd=price, est_cost_usd=round(cost, 2), cost_status="Printful list price + US shipping (approx.)",
            est_profit_usd=profit(price, cost), listing_photos=photos(f), print_file_for_partner=win(f),
            status="List after sample approved")
for color in ["Black", "Blue", "Green", "Outline"]:
    for sz, price, cost in MUG_SIZES:
        f = size_file(f"MST_Logo_{color}", "5x7")
        add("06_Mugs_Totes", listing_handle="mug-mst-silhouette", listing_type="Physical (print on demand)",
            production_partner=PRINTFUL, partner_product="White glossy mug",
            title="Mountains to Sea Trail Mug, NC State Outline MST Coffee Mug, North Carolina Hiker Gift",
            description=f"{MST_BLURB}\n\n{MUG_DESC}\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
            tags=with_product_tags(TAGS["MST_LOGO"], ["hiking mug", "coffee mug gift"]),
            materials="ceramic", etsy_category="Home & Living > Kitchen & Dining > Drink & Barware > Drinkware > Mugs",
            when_made="Made to order", shop_section="Stickers & Gear", processing_time="2-5 business days",
            shipping_profile="POD - free US shipping", sku=f"BCN-MUG-MST-{color.upper()}-{sz.split()[0]}",
            variation_1_name="Color", variation_1_value=color, variation_2_name="Size", variation_2_value=sz,
            price_usd=price, est_cost_usd=round(cost, 2), cost_status="Printful list price + US shipping (approx.)",
            est_profit_usd=profit(price, cost), listing_photos=photos(f), print_file_for_partner=win(f),
            status="List after sample approved",
            notes="White-background JPG works on a white mug; crop the copyright line off in Printful's placement editor.")
for style, f in [("Line Art", "3_Pack_Your_Dreams/Pack_Your_Dreams_NewPack_transparent.png"),
                 ("Sketch", "3_Pack_Your_Dreams/Pack_Your_Dreams_Sketch_transparent.png"),
                 ("Green", "3_Pack_Your_Dreams/Pack_Your_Dreams_transparent_4500px.png")]:
    add("06_Mugs_Totes", listing_handle="tote-pack-your-dreams", listing_type="Physical (print on demand)",
        production_partner=PRINTFUL, partner_product="Eco tote bag (natural)",
        title="Pack Your Dreams Not Your Fears Tote Bag, Backpacking Canvas Tote, Hiker Gift, Adventure Quote Bag",
        description=f"{PYD_BLURB}\n\nTOTE DETAILS\n• Natural cotton tote, 15 x 15 in\n• Design printed on the front\n• Made to order\n\n{PARTNER_LINE.format(shop=SHOP, p=PRINTFUL)}",
        tags=with_product_tags(TAGS["PYD"], ["hiking tote bag", "canvas tote"]),
        materials="cotton", etsy_category="Bags & Purses > Totes", when_made="Made to order",
        shop_section="Stickers & Gear", processing_time="2-5 business days", shipping_profile="POD - free US shipping",
        sku=f"BCN-TOTE-PYD-{style.split()[0].upper()}", variation_1_name="Style", variation_1_value=style,
        price_usd=24.00, est_cost_usd=round(10.50 + 4.75, 2), cost_status="Printful list price + US shipping (approx.)",
        est_profit_usd=profit(24.00, 10.50 + 4.75), listing_photos=photos(f), print_file_for_partner=win(f),
        status="List after sample approved")

# ================================================================ write
def check(row):
    errs = []
    if len(row["title"]) > 140: errs.append(f"title {len(row['title'])} chars")
    tags = [t.strip() for t in row["tags"].split(",")]
    if len(tags) > 13: errs.append(f"{len(tags)} tags")
    for t in tags:
        if len(t) > 20: errs.append(f"tag too long: {t}")
    for col in ("print_file_for_partner", "digital_files", "listing_photos"):
        for p in [x.strip() for x in row[col].split("|") if x.strip()]:
            if p.startswith("NEEDED"): continue
            if not os.path.exists(os.path.join(ROOT, p.replace("\\", "/"))): errs.append(f"missing file {p}")
    if row["est_profit_usd"] != "" and float(row["est_profit_usd"]) <= 0: errs.append("non-positive profit")
    return errs

problems = 0
allrows = []
for fam in sorted(ROWS):
    rows = ROWS[fam]
    for r in rows:
        e = check(r)
        if e:
            problems += 1; print(fam, r["sku"], e)
    try:
        with open(os.path.join(OUT, f"{fam}.csv"), "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, COLUMNS); w.writeheader(); w.writerows(rows)
    except PermissionError:
        print(f"SKIPPED {fam}.csv - file is open in another program (close Excel and re-run)")
    allrows += rows
with open(os.path.join(OUT, "00_All_Listings.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, COLUMNS); w.writeheader(); w.writerows(allrows)

# summary: one row per listing
summ = {}
for r in allrows:
    s = summ.setdefault(r["listing_handle"], dict(listing_handle=r["listing_handle"], product_family=r["product_family"],
            production_partner=r["production_partner"], title=r["title"], variants=0, min_price=1e9, max_price=0,
            min_profit=1e9, max_profit=-1e9, status=r["status"]))
    s["variants"] += 1
    s["min_price"] = min(s["min_price"], float(r["price_usd"])); s["max_price"] = max(s["max_price"], float(r["price_usd"]))
    s["min_profit"] = min(s["min_profit"], float(r["est_profit_usd"])); s["max_profit"] = max(s["max_profit"], float(r["est_profit_usd"]))
with open(os.path.join(OUT, "00_Listing_Summary.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    cols = list(next(iter(summ.values())).keys())
    w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(summ.values())

print(f"{len(summ)} listings, {len(allrows)} variant rows, {problems} rows with problems")
for fam in sorted(ROWS):
    print(fam, len({r['listing_handle'] for r in ROWS[fam]}), "listings", len(ROWS[fam]), "rows")
