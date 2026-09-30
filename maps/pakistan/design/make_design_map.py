#!/usr/bin/env python3
"""
Design asset: minimal typographic map of Pakistan.

No rivers, no provinces, no neighbours, no graticule, no legend -- just the
silhouette of Pakistan (including Azad Jammu & Kashmir and Gilgit-Baltistan)
and the names of 13 cities set as the artwork.

Three treatments are produced (same geometry, different look):

    v1 "knockout"  solid deep-green silhouette, cream type knocked out of it
    v2 "line"      silhouette as a single hairline, ink type on transparency
    v3 "tint"      pale green silhouette with a hairline edge, deep-green type

Each treatment is written as:
    pakistan_cities_v1_knockout.svg   vector, text converted to outlines
    pakistan_cities_v1_knockout.pdf   vector, 8x8 in, transparent background
    pakistan_cities_v1_knockout.png   300 dpi, transparent background

Run:  python3 make_design_map.py                 # outlined SVG (safe everywhere)
      python3 make_design_map.py --live-text     # SVG keeps editable text
                                                 # (needs Poppins + Bebas Neue installed)
"""
from __future__ import annotations

import argparse
import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point
from pyproj import Transformer

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MplPolygon
import matplotlib.patheffects as pe

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
FONTS = os.path.join(HERE, "fonts")

CRS_WGS = "EPSG:4326"
# same conic as the printed map: honest proportions, no distortion to the eye
CRS_MAP = ("+proj=lcc +lat_1=24 +lat_2=33 +lat_0=30 +lon_0=69 "
           "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")

# ---------------------------------------------------------------------------
# 1. The 13 cities, grouped into three type tiers so the list has hierarchy
# ---------------------------------------------------------------------------
CITIES = [
    # name,          lat,      lon,      tier
    ("Islamabad",    33.6931, 73.0639, 1),
    ("Rawalpindi",   33.5973, 73.0479, 1),
    ("Karachi",      24.8607, 67.0011, 1),
    ("Lahore",       31.5497, 74.3436, 1),
    ("Faisalabad",   31.4187, 73.0791, 1),
    ("Hyderabad",    25.3792, 68.3683, 2),
    ("Mianwali",     32.5839, 71.5370, 2),
    ("Sargodha",     32.0836, 72.6711, 2),
    ("D.I. Khan",    31.8313, 70.9019, 2),
    ("Peshawar",     34.0151, 71.5249, 1),
    ("Quetta",       30.1798, 66.9750, 1),
    ("Bannu",        32.9889, 70.6056, 3),
    ("Kohat",        33.5869, 71.4414, 3),
]

# ---------------------------------------------------------------------------
# 2. The three looks
# ---------------------------------------------------------------------------
STYLES = {
    "v1_knockout": dict(
        fill="#0C4A34", edge="none", edge_w=0.0,
        type_color="#F6F1E4", dot_color="#F6F1E4", dot_r=3.9,
        country="PAKISTAN", country_color="#0C4A34",
        sub="13 MAJOR CITIES", sub_color="#5E9C7D",
        leader="#F6F1E4", transparent=True, inside_only=True,
    ),
    "v2_line": dict(
        fill="none", edge="#12352A", edge_w=1.5,
        type_color="#12352A", dot_color="#0F9D3A", dot_r=3.3,
        country="PAKISTAN", country_color="#12352A",
        sub="13 MAJOR CITIES", sub_color="#0F9D3A",
        leader="#12352A", transparent=True, inside_only=False,
    ),
    "v3_tint": dict(
        fill="#D9EBDF", edge="#1F6B4A", edge_w=1.0,
        type_color="#124532", dot_color="#1F6B4A", dot_r=3.5,
        country="PAKISTAN", country_color="#124532",
        sub="13 MAJOR CITIES", sub_color="#5E9C7D",
        leader="#1F6B4A", transparent=True, inside_only=False,
    ),
}

# ---------------------------------------------------------------------------
# 3. Typography
# ---------------------------------------------------------------------------
TIER = {                     # tier -> (font file, size in points)
    1: ("Poppins-Bold.ttf", 11.8),
    2: ("Poppins-Medium.ttf", 9.4),
    3: ("Poppins-Regular.ttf", 9.0),
}
WORDMARK_FONT = "BebasNeue-Regular.ttf"
WORDMARK_SIZE = 44.0
SUB_SIZE = 10.5

MEASURE_DPI = 300

THIN = "\u2009"              # thin space -- used to fake letterspacing

# Some neighbours are close enough that a free choice of side reads wrongly
# (Karachi's label would sit next to Hyderabad's dot, and vice versa).  These
# cities may only use offsets inside the given angular sector, measured from
# due east, counter-clockwise (so 90..270 = the western half-plane).
SECTOR = {
    "Karachi":   (25, 250),      # Karachi's name stays off the Hyderabad side
    "Hyderabad": (-80, 85),      # and Hyderabad's east/north-east of its dot
    "Lahore":    (-70, 60),      # Lahore sits north-east of Faisalabad
    "Faisalabad": (110, 250),
}

# the far north is dense: those names are set slightly smaller, which is normal
# cartographic practice and keeps the cluster legible
NORTH = {"Peshawar", "Kohat", "Bannu", "Islamabad", "Rawalpindi", "Mianwali"}
NORTH_SCALE = 0.86


def label_metric(name, tier):
    """(font file, point size) for a city."""
    ffile, fsize = TIER[tier]
    if name in NORTH:
        fsize *= NORTH_SCALE
    return ffile, fsize


def register_fonts():
    names = {}
    for f in ("Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-Bold.ttf",
              "Poppins-ExtraBold.ttf", WORDMARK_FONT):
        path = os.path.join(FONTS, f)
        fm.fontManager.addfont(path)
        names[f] = fm.FontProperties(fname=path).get_name()
    return names


def tracked(text: str, gap: str = THIN, word_gap: str = THIN * 2) -> str:
    """Fake letterspacing: 'KARACHI' -> 'K<ts>A<ts>R...'"""
    return word_gap.join(gap.join(w) for w in text.split())


# ---------------------------------------------------------------------------
# 4. Hand-set label positions
#    (dx, dy) in points from the city dot, ha, va -- tuned on the proof
# ---------------------------------------------------------------------------
POS = {
    "Quetta":      (12, 0, "left", "center"),
    "Karachi":     (-12, 7, "right", "bottom"),
    "Hyderabad":   (12, 5, "left", "bottom"),
    "Lahore":      (12, 4, "left", "bottom"),
    "Faisalabad":  (-12, -3, "right", "top"),
    "Sargodha":    (11, 0, "left", "center"),
    "Mianwali":    (-4, -14, "right", "top"),
    "D.I. Khan":   (-12, 0, "right", "center"),
    "Bannu":       (-9, 5, "right", "bottom"),
    "Kohat":       (11, 1, "left", "center"),
    "Peshawar":    (-11, 7, "right", "bottom"),
    "Islamabad":   (0, 15, "center", "bottom"),
    "Rawalpindi":  (-8, 9, "right", "bottom"),
}
# automatic alternatives: a ring of offsets/directions around each dot
def _ring():
    out = []
    for dist in (8, 12, 17, 23, 31):
        for ang in range(0, 360, 45):
            rad = np.radians(ang)
            dx, dy = dist * np.cos(rad), dist * np.sin(rad)
            ha = "left" if dx > 3 else ("right" if dx < -3 else "center")
            va = "bottom" if dy > 3 else ("top" if dy < -3 else "center")
            out.append((round(dx, 1), round(dy, 1), ha, va))
    return out


CANDS = _ring()
# cities whose label needs a thin leader line back to its dot
LEADER = {"Islamabad", "Rawalpindi", "Peshawar", "Bannu", "Mianwali", "Kohat"}


# ---------------------------------------------------------------------------
# 5. Build one treatment
# ---------------------------------------------------------------------------
def build(style_name: str, st: dict, fonts: dict, live_text: bool, out_dir: str,
          show_title: bool = True, show_cities: bool = True):
    plt.rcParams["svg.fonttype"] = "none" if live_text else "path"
    plt.rcParams["pdf.fonttype"] = 42

    transformer = Transformer.from_crs(CRS_WGS, CRS_MAP, always_xy=True)
    countries = gpd.read_file(os.path.join(DATA, "countries.geojson")).to_crs(CRS_MAP)
    pak = countries[countries.ADMIN == "Pakistan"].geometry.union_all()

    # --- clean silhouette ---------------------------------------------------
    # drop the scatter of tiny coastal islands, then smooth the coastline so the
    # shape reads as a solid graphic mark rather than a survey trace
    parts = list(pak.geoms) if pak.geom_type == "MultiPolygon" else [pak]
    pieces = [g for g in parts if g.area > 1e8]           # keep anything > 100 km2
    silhouette = max(pieces, key=lambda g: g.area).simplify(2600)   # ~2.6 km
    silhouette = Polygon(silhouette.exterior)             # tidy, no interior rings
    pak = silhouette

    fx0, fy0, fx1, fy1 = pak.bounds
    W, H = fx1 - fx0, fy1 - fy0

    # --- canvas: square, with the silhouette optically centred --------------
    pad_x = W * 0.085
    pad_top, pad_bottom = H * 0.075, H * 0.150      # extra room under the map
    cx0, cx1 = fx0 - pad_x, fx1 + pad_x
    cy0, cy1 = fy0 - pad_bottom, fy1 + pad_top
    cw, ch = cx1 - cx0, cy1 - cy0
    CANVAS_IN = 10.0
    fig = plt.figure(figsize=(CANVAS_IN, CANVAS_IN * ch / cw))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(cx0, cx1); ax.set_ylim(cy0, cy1)
    ax.set_aspect("equal"); ax.set_axis_off()

    # --- silhouette ---------------------------------------------------------
    ax.add_patch(MplPolygon(np.asarray(pak.exterior.coords), closed=True,
                            facecolor=st["fill"] if st["fill"] != "none" else "none",
                            edgecolor=st["edge"] if st["edge"] != "none" else "none",
                            linewidth=st["edge_w"], zorder=2, joinstyle="round"))

    # --- wordmark -----------------------------------------------------------
    # --- wordmark lockup, bottom-left ---------------------------------------
    if not show_title:
        pad_pt = 0.0
    pad_pt = 16.0                     # text inset from the canvas edge, points
    x_l = pad_pt / (CANVAS_IN * 72)
    y_0 = pad_pt / (CANVAS_IN * 72 * (ch / cw))      # subtitle baseline
    y_1 = y_0 + (SUB_SIZE * 1.55) / (CANVAS_IN * 72 * (ch / cw))   # wordmark baseline
    if show_title:
        fig.text(x_l, y_0, tracked(st["sub"], gap=THIN, word_gap=THIN * 3),
                 fontproperties=fm.FontProperties(fname=os.path.join(FONTS, "Poppins-Medium.ttf"),
                                                  size=SUB_SIZE),
                 color=st["sub_color"], ha="left", va="baseline")
        fig.text(x_l, y_1, tracked(st["country"], gap=THIN * 2, word_gap=THIN * 4),
                 fontproperties=fm.FontProperties(fname=os.path.join(FONTS, WORDMARK_FONT),
                                                  size=WORDMARK_SIZE),
                 color=st["country_color"], ha="left", va="baseline")

    # --- city labels: optimised placement -----------------------------------
    inv = ax.transData.inverted()

    # measure every label once, in metres, at the very DPI we export at
    canvas_w_m = cx1 - cx0
    fig_w_px = CANVAS_IN * MEASURE_DPI
    m_per_px = canvas_w_m / fig_w_px
    probe = plt.figure(figsize=(CANVAS_IN, CANVAS_IN), dpi=MEASURE_DPI)
    pr = probe.canvas.get_renderer()

    metrics = {}
    for name, lat, lon, tier in CITIES:
        ffile, fsize = label_metric(name, tier)
        t = probe.text(0.5, 0.5, tracked(name.upper(), gap=THIN),
                       fontproperties=fm.FontProperties(
                           fname=os.path.join(FONTS, ffile), size=fsize))
        bb = t.get_window_extent(renderer=pr)
        t.remove()
        metrics[name] = (bb.width * m_per_px, bb.height * m_per_px, ffile, fsize)
    plt.close(probe)

    dots = {c[0]: transformer.transform(c[2], c[1]) for c in CITIES}
    # marker diameter is given in points -> radius in metres on the printed canvas
    dot_r_m = (st["dot_r"] / 2.0) * (MEASURE_DPI / 72.0) * m_per_px

    def on_shape(box) -> float:
        """share of the label box that lies on the silhouette (0..1)"""
        x0, y0, x1, y1 = box
        inside = 0
        for i in range(3):
            for j in range(3):
                x = x0 + (x1 - x0) * (i + 0.5) / 3
                y = y0 + (y1 - y0) * (j + 0.5) / 3
                if pak.contains(Point(x, y)):
                    inside += 1
        return inside / 9.0

    def rect_overlap(a, b) -> float:
        ix = min(a[2], b[2]) - max(a[0], b[0])
        iy = min(a[3], b[3]) - max(a[1], b[1])
        return max(0.0, ix) * max(0.0, iy)

    def boxes_for(name, dx, dy):
        w, h, _, _ = metrics[name]
        x, y = dots[name]
        return (x + dx - w / 2, y + dy - h / 2, x + dx + w / 2, y + dy + h / 2)

    # candidate offsets: a ring plus a coarse grid, in metres
    grid = []
    for r in (0, 18_000, 34_000, 52_000, 72_000, 95_000, 120_000):
        n = 1 if r == 0 else 12
        for k in range(n):
            a = 2 * np.pi * k / n
            grid.append((r * np.cos(a), r * np.sin(a)))

    def cost(name, dx, dy, placed_boxes):
        box = boxes_for(name, dx, dy)
        c = (1.0 - on_shape(box)) * 26.0
        area_lbl = (box[2] - box[0]) * (box[3] - box[1])
        for other in placed_boxes:
            c += rect_overlap(box, other) / area_lbl * 34.0
        for n2, (px, py) in dots.items():                    # never cover a dot
            gap = dot_r_m * (2.2 if n2 == name else 1.0)
            dot_box = (px - gap, py - gap, px + gap, py + gap)
            weight = 150.0 if n2 == name else 40.0
            c += rect_overlap(box, dot_box) / area_lbl * weight
        c += np.hypot(dx, dy) / 120_000.0 * 3.4             # stay near the city
        return c, box

    def allowed(name, dx, dy):
        if name not in SECTOR:
            return True
        lo, hi = SECTOR[name]
        ang = np.degrees(np.arctan2(dy, dx))
        return lo <= ang <= hi if lo <= hi else (ang >= lo or ang <= hi)

    def layout(order):
        placed = {}
        for name in order:
            best = None
            for dx, dy in grid:
                if not allowed(name, dx, dy):
                    continue
                c, box = cost(name, dx, dy, list(placed.values()))
                if best is None or c < best[0]:
                    best = (c, dx, dy, box)
            placed[name] = best[3]
            yield name, best[1], best[2]
        return

    # start with the crowded northern cities, then fill the rest
    crowd = sorted(CITIES, key=lambda c: min(
        np.hypot(dots[c[0]][0] - dots[o[0]][0], dots[c[0]][1] - dots[o[0]][1])
        for o in CITIES if o[0] != c[0]))
    order = [c[0] for c in crowd] if show_cities else []
    placements = {}
    full = layout(order)

    # keep the best of a few passes (the greedy result depends on the order)
    passes = []
    for shift in range(4) if show_cities else []:
        o = order[shift:] + order[:shift]
        res = list(layout(o))
        total = 0.0
        for i, (n, dx, dy) in enumerate(res):
            prior = [boxes_for(n2, a, b) for n2, a, b in res[:i]]
            total += cost(n, dx, dy, prior)[0]
        passes.append((total, res))
    if passes:
        passes.sort(key=lambda r: r[0])
        best_total, result = passes[0]
        placements = {n: (dx, dy) for n, dx, dy in result}
        print(f"  layout: {len(passes)} passes, best total cost {best_total:.1f}")

    for name, lat, lon, tier in (sorted(CITIES, key=lambda c: (c[3], c[0]))
                                 if show_cities else []):
        x, y = transformer.transform(lon, lat)
        ax.plot([x], [y], marker="o", markersize=st["dot_r"],
                color=st["dot_color"], linestyle="none", zorder=6)

        ffile, fsize = label_metric(name, tier)
        fp = fm.FontProperties(fname=os.path.join(FONTS, ffile), size=fsize)
        label = tracked(name.upper(), gap=THIN)
        halo = ([pe.withStroke(linewidth=2.6, foreground=st["fill"])]
                if (style_name != "v1_knockout" and st["fill"] != "none") else [])
        dx, dy = placements[name]
        # offset points from the dot, centred on the anchor
        m_per_pt = canvas_w_m / (CANVAS_IN * 72.0)     # metres per typographic point
        dx_pt, dy_pt = dx / m_per_pt, dy / m_per_pt
        leader = {}
        if np.hypot(dx, dy) > 14_000:
            leader = dict(arrowprops=dict(arrowstyle="-", color=st["leader"],
                                          lw=0.7, shrinkA=2.0, shrinkB=4.0,
                                          connectionstyle="arc3,rad=0"))
        ax.annotate(label, xy=(x, y), xytext=(dx_pt, dy_pt),
                    textcoords="offset points", ha="center", va="center",
                    fontproperties=fp, color=st["type_color"], zorder=7,
                    path_effects=halo, **leader)

    # --- write --------------------------------------------------------------
    tag = "pakistan_cities" if show_cities else "pakistan_silhouette"
    if show_cities and not show_title:
        tag = "pakistan_cities_notitle"
    base = os.path.join(out_dir, f"{tag}_{style_name}")
    fig.savefig(base + ".svg", transparent=st["transparent"])
    fig.savefig(base + ".pdf", transparent=st["transparent"])
    fig.savefig(base + ".png", dpi=300, transparent=st["transparent"])
    plt.close(fig)
    print(f"  {style_name:12s} -> {os.path.basename(base)}.svg / .pdf / .png"
          f"   ({cw/1000:.0f} x {ch/1000:.0f} km canvas)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-text", action="store_true",
                    help="keep SVG text editable (needs the bundled fonts installed)")
    args = ap.parse_args()
    fonts = register_fonts()
    out_dir = HERE
    print("writing design assets:")
    for name, st in STYLES.items():
        build(name, st, fonts, args.live_text, out_dir)
    # extras that are handy inside a layout
    build("v1_knockout", STYLES["v1_knockout"], fonts, args.live_text, out_dir,
          show_title=False)
    build("v1_knockout", STYLES["v1_knockout"], fonts, args.live_text, out_dir,
          show_title=False, show_cities=False)
    build("v3_tint", STYLES["v3_tint"], fonts, args.live_text, out_dir,
          show_title=False, show_cities=False)


if __name__ == "__main__":
    main()
