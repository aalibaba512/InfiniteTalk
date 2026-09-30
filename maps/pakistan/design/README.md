# Design asset — typographic Pakistan map

A minimal **graphic** version of the map, made to be dropped into a poster, deck,
social post or thumbnail. Every cartographic detail is gone: no rivers, no
province lines, no neighbours, no graticule, no legend, no frame. What is left is
the shape of Pakistan (as administered — the silhouette **includes Azad Jammu &
Kashmir and Gilgit-Baltistan**) and the 13 city names set as the artwork itself.

## The three treatments

| File stem | Look |
|---|---|
| `pakistan_cities_v1_knockout` | Solid deep-green silhouette with cream type knocked out of it — the boldest option, works on dark or photo backgrounds |
| `pakistan_cities_v2_line` | Silhouette as a single hairline, deep-green type, green dots — light, editorial, almost invisible background |
| `pakistan_cities_v3_tint` | Pale-green silhouette with a hairline edge and deep-green type — the safest all-purpose version |

## Extras

| File stem | What it is |
|---|---|
| `pakistan_cities_notitle_v1_knockout` | Same as v1 without the `PAKISTAN / 13 MAJOR CITIES` lockup, for when your design supplies its own title |
| `pakistan_silhouette_v1_knockout` | Just the solid silhouette, no names at all — a clean shape to composite over |
| `pakistan_silhouette_v3_tint` | Same shape in the pale tint |

## Formats

Each stem comes in three files:

* **`.svg`** — true vector, all text converted to **outlines**, so nothing can
  re-flow or go missing on another machine. No raster images inside, no
  background. This is the file to open in Illustrator / Figma / Inkscape /
  Affinity.
* **`.pdf`** — same artwork, transparent background (handy for PDF print layouts).
* **`.png`** — 3000 px wide, 300 dpi, **transparent** background, for quick use.

Want **editable text** instead of outlines (so you can retype a city name)?

```bash
python3 make_design_map.py --live-text     # SVG keeps <text> elements
```

That version references the bundled fonts, so install
`fonts/Poppins-*.ttf` and `fonts/BebasNeue-Regular.ttf` first.

## Design decisions

* **Type** — Poppins (SemiBold/Medium/Regular) for the city names, Bebas Neue for
  the `PAKISTAN` wordmark. Both are SIL Open Font License; licence texts are in
  `fonts/`.
* **Three type tiers** — Karachi, Lahore, Faisalabad, Rawalpindi, Peshawar,
  Islamabad, Quetta are the larger tier; Hyderabad, Mianwali, Sargodha and
  D.I. Khan the middle; Bannu and Kohat the smallest. The six cities of the
  Rawalpindi–Peshawar corridor are set 14 % smaller again, which is normal
  cartographic practice and keeps that dense cluster readable.
* **Letterspacing** — every name is tracked out with thin spaces so the list has
  the even, "typeset" rhythm of a poster rather than a map.
* **Placement is solved, not guessed** — each name is positioned by a small
  optimiser that searches a grid of offsets around its dot and scores
  (1) how much of the name falls on the silhouette, (2) overlap with other names,
  (3) overlap with any city dot, and (4) distance from its own city. Karachi,
  Hyderabad, Lahore and Faisalabad are restricted to sensible sides so a name can
  never appear to label the wrong city. Thin leader lines appear only where a
  name had to move well away from its dot.
* **Projection** — Lambert Conformal Conic (24 °N / 33 °N), the same as the
  printed map, so the shape has honest proportions; the coastline is simplified
  and the scatter of tiny offshore islands dropped so the mark stays clean.

## Regenerating

```bash
python3 make_design_map.py                 # all six stems, outlines + pdf + png
python3 make_design_map.py --live-text     # SVG keeps editable text
```

Recolour by editing `STYLES` at the top of `make_design_map.py` — each treatment
is a handful of hex values (`fill`, `edge`, `type_color`, `dot_color`,
`country_color`, `sub_color`, `leader`). Add or remove cities in `CITIES`.

## One thing to be aware of

Because this is a graphic rather than a reference map, no internal boundaries are
drawn — the Line of Control is not shown, so the silhouette reads as one solid
shape. That is the intended look for a design asset; if you ever need the
disputed boundary shown, use the printed A4 map in the parent folder instead.
