# Pakistan — printable major-cities map

A print-ready **A4 vector map of Pakistan** that includes **Azad Jammu & Kashmir (AJK)**
and **Gilgit-Baltistan**, with the 13 requested cities marked by **green dots** and
labelled in place.

| File | What it is |
|---|---|
| `Pakistan_Map_with_Cities_A4.pdf` | **The deliverable.** 1 page, exactly 210 × 297 mm (A4 portrait), true vector PDF, embedded fonts |
| `Pakistan_Map_with_Cities_A4.png` | 300 dpi raster preview of the same page (2480 × 3507 px) |
| `make_pakistan_map.py` | The generator — edit colours, cities, type sizes and re-run |
| `fetch_data.py` | Rebuilds `data/` from a local clone of Natural Earth |
| `data/*.geojson` | Cropped boundary layers actually used by the map (≈1.2 MB) |

## Cities marked

Islamabad · Rawalpindi · Karachi · Lahore · Faisalabad · Hyderabad · Mianwali ·
Bannu · Kohat · Peshawar · Quetta · D.I. Khan · Sargodha

Coordinates were cross-checked against the **GeoNames** gazetteer: the largest
deviation from the published coordinates used here is ≈5 km — far less than one
printed line width at this scale.

## Regenerating

```bash
pip install geopandas shapely pyproj matplotlib          # once
python3 make_pakistan_map.py                             # writes PDF + PNG
```

To rebuild the data layers first (needs a Natural Earth clone):

```bash
git clone --depth 1 https://github.com/nvkelso/natural-earth-vector.git
python3 fetch_data.py natural-earth-vector/geojson
python3 make_pakistan_map.py
```

## Cartography notes

* **Projection** — Lambert Conformal Conic, WGS 84, standard parallels 24 °N / 33 °N.
  Those parallels were chosen numerically so that the *local scale at every one of the
  13 cities* stays within ~0.3 % of true, which makes the printed scale bar accurate
  as drawn (the north of Gilgit-Baltistan reaches ~0.8 %).
* **Boundaries** — Natural Earth 1:10m (public domain). The admin-0 polygon for
  Pakistan already contains AJK and Gilgit-Baltistan, i.e. the map is drawn
  *as administered*; the Line of Control is shown as a dashed disputed boundary and
  the area east of it is toned as Indian-administered Jammu & Kashmir. This is
  stated in the map's own note block.
* **Labelling** — city names are placed automatically with collision detection
  against dots, other city labels and every region/neighbour label, so no two pieces
  of text overlap; the crowded Rawalpindi–Islamabad–Kohat cluster uses hand-tuned
  positions with thin leader lines.
* **Scale bar** — 300 km, 4 × 25 km subdivisions, drawn in map units (not a fixed
  bar length), so it is correct on paper when printed at 100 %.

## Printing

Print at **100 % / "actual size"** (not "fit to page"), A4 portrait, borderless
optional. Everything is vector, so it stays sharp at any printer resolution.
