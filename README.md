# Image-Etsy

Version history for the Beech Creek Naturals Etsy shop files (trail map posters, Pack Your Dreams designs, print sizes, listing mockups, listing CSVs and the `trail_poster` tool).

This repo mirrors the local folder `OneDrive\Documents\Etsy`. Everything except `Images and Listing/_to_delete/` is tracked.

## Layout
| Folder | What it holds |
|---|---|
| `Images and Listing/4_Print_Sizes/<design>/` | Print files for drop-ship partners (Prodigi, Artelo) and the size masters |
| `Images and Listing/4_Print_Sizes/_Home_Print/` | Digital-download versions of the trail maps, darkened for home printers |
| `Images and Listing/4_Print_Sizes/_Masters_2026/` | Vector/PDF masters |
| `Images and Listing/4_Print_Sizes/_Displate/` | Displate metal-print files (vendor spec, no mat margin) |
| `Images and Listing/5_Etsy_Listings/` | Listing CSVs, download ZIPs, POD print files |
| `Images and Listing/6_Listing_Mockups/` | Listing photos |
| `trail_poster/` | Trail poster generator (Python) |

## Reverting
Every change is a commit. To get an older version of a file:
`git log -- "<path>"` to find the commit, then `git checkout <commit> -- "<path>"`.
The first commit (`Baseline`) is the state of the folder on 2026-11-24 before the text-scaling change.
