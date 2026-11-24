# 06 — Print output, staging and copy

**Does one thing:** turns an approved design into print files, then moves them
into the listing folder after Gate 4.

## Steps
1. **Preview:** one PNG at the master size. **Gate 3:** David approves it.
2. **Render** into staging `trail_poster/output/<Trail>/<Trail>/`:
   - Landscape: `36x24, 24x18, 20x16, 14x11, 7x5, A1_landscape`
   - Portrait: `24x36, 18x24, 16x20, 11x14, 5x7, A1`
   - Named `<Trail>_<size>.jpg` (e.g. `Benton_MacKaye_Trail_36x24.jpg`).
   - 300 dpi RGB JPG, maximum quality, white background, 7% white margin on
     every side, artwork scaled to fit and never cropped. Matches `SIZE_GUIDE.txt`.
   - Vector masters (SVG and PDF) in `output/<Trail>/masters/`.
3. **Gate 4:** Claude lists the files and sizes and asks before copying.
4. **Copy** on David's yes to `Images and Listing/4_Print_Sizes/<Trail>/` and
   the masters to `4_Print_Sizes/_Masters_2026/<Trail>.svg` and `.pdf` (same
   naming as `Art_Loeb_Trail.svg`). Never overwrite an existing file without
   naming it and asking.

## Done when
- [ ] Each JPG's pixel size equals its inches × 300.
- [ ] The 7×5 and 36×24 versions look identical apart from scale.

## Decisions (confirmed 2026-11-23)
- [x] **V6.1** Masters are copied to `4_Print_Sizes/_Masters_2026` with the same
      naming as existing ones.
- [x] **V6.2** No sticker or circle versions of trail maps, ever.
