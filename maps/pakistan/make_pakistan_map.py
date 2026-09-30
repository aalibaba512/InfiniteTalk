#!/usr/bin/env python3
"""
Printable A4 map of Pakistan -- including Azad Jammu & Kashmir (AJK) and
Gilgit-Baltistan -- with 13 major cities marked as green dots and labelled.

Data (Natural Earth 1:10m, public domain) in ./data/ :
    countries.geojson          admin-0 countries (the Pakistan polygon already
                               includes Azad Jammu & Kashmir + Gilgit-Baltistan)
    pakistan_admin1.geojson    provinces / administered areas of Pakistan
    rivers.geojson             river centrelines
    lakes.geojson              lakes / reservoirs
    line_of_control.geojson    Line of Control (disputed -> dashed)

Output:
    Pakistan_Map_with_Cities_A4.pdf   vector PDF, A4 portrait, print ready
    Pakistan_Map_with_Cities_A4.png   300 dpi raster preview

Run:  python3 make_pakistan_map.py
"""
from __future__ import annotations

import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from pyproj import Transformer

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Polygon as MplPolygon

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PDF_OUT = os.path.join(HERE, "Pakistan_Map_with_Cities_A4.pdf")
PNG_OUT = os.path.join(HERE, "Pakistan_Map_with_Cities_A4.png")

# ----------------------------------------------------------------------------
# 1. Style constants
# ----------------------------------------------------------------------------
C_SEA = "#dde9f5"           # ocean / outside land
C_NEIGHBOUR = "#f0ede6"     # neighbouring countries
C_NEIGHBOUR_EDGE = "#bdb5a7"
C_PAK = "#cde6c9"           # Pakistan fill
C_PAK_EDGE = "#2f6b3d"      # Pakistan outline
C_PROV_EDGE = "#7fa87f"     # province boundaries
C_DOT = "#0f9d3a"           # city dot (green)
C_RIVER = "#8dc0e0"
C_LAKE = "#a9cfec"
C_GRAT = "#9db4c9"
C_TEXT = "#1d2b22"
C_MUTED = "#6b7a70"
INK = "#25333e"

# A4 portrait, inches
PAGE_W, PAGE_H = 8.268, 11.693
MARGIN = 0.42
HEADER_H = 1.25
FOOTER_H = 2.15

# Geographic window of the map frame (a little larger than Pakistan)
FRAME = dict(lon0=60.2, lon1=78.4, lat0=22.4, lat1=37.9)

CRS_WGS = "EPSG:4326"
# Lambert Conformal Conic (metres).  Standard parallels 24N/33N bracket the whole
# country and the scale-bar location, so local scale stays within ~0.3 % of true
# everywhere a city is plotted (max ~0.8 % up in the far north of Gilgit-Baltistan).
CRS_MAP = ("+proj=lcc +lat_1=24 +lat_2=33 +lat_0=30 +lon_0=69 "
           "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")

# ----------------------------------------------------------------------------
# 2. Cities -- coordinates cross-checked against the GeoNames gazetteer
#    (largest deviation ~5 km, i.e. far less than one printed line width here)
# ----------------------------------------------------------------------------
CITIES = [
    # name,           lat,      lon,      rank (1 = major)
    ("Islamabad",    33.6931, 73.0639, 2),
    ("Rawalpindi",   33.5973, 73.0479, 1),
    ("Karachi",      24.8607, 67.0011, 1),
    ("Lahore",       31.5497, 74.3436, 1),
    ("Faisalabad",   31.4187, 73.0791, 1),
    ("Hyderabad",    25.3792, 68.3683, 2),
    ("Mianwali",     32.5839, 71.5370, 3),
    ("Bannu",        32.9889, 70.6056, 3),
    ("Kohat",        33.5869, 71.4414, 3),
    ("Peshawar",     34.0151, 71.5249, 1),
    ("Quetta",       30.1798, 66.9750, 1),
    ("D.I. Khan",    31.8313, 70.9019, 3),
    ("Sargodha",     32.0836, 72.6711, 3),
]


# ----------------------------------------------------------------------------
# 3. Helpers
# ----------------------------------------------------------------------------
def load(name, crs):
    g = gpd.read_file(os.path.join(DATA, name))
    if g.crs is None:
        g = g.set_crs(CRS_WGS)
    return g.to_crs(crs)


def frame_polygon(transformer, frame=FRAME):
    """The lon/lat window projected into map CRS, as a shapely polygon."""
    lons = np.linspace(frame["lon0"], frame["lon1"], 80)
    lats = np.linspace(frame["lat0"], frame["lat1"], 80)
    ring = ([(x, frame["lat0"]) for x in lons]
            + [(frame["lon1"], y) for y in lats]
            + [(x, frame["lat1"]) for x in reversed(lons)]
            + [(frame["lon0"], y) for y in reversed(lats)])
    xs, ys = transformer.transform(*zip(*ring))
    return Polygon(zip(xs, ys))


def graticule(transformer, frame=FRAME):
    meridians, parallels = [], []
    for lon in np.arange(55, 85, 5):
        lats = np.linspace(frame["lat0"], frame["lat1"], 160)
        xs, ys = transformer.transform([lon] * len(lats), lats)
        meridians.append((lon, np.column_stack([xs, ys])))
    for lat in np.arange(15, 45, 5):
        lons = np.linspace(frame["lon0"], frame["lon1"], 160)
        xs, ys = transformer.transform(lons, [lat] * len(lons))
        parallels.append((lat, np.column_stack([xs, ys])))
    return meridians, parallels


def scale_bar(ax, x0, y0, bar_w, bar_h, total_km=300, seg_km=100, sub=4, fs=6.3):
    """Alternating black/white scale bar. x0/y0/bar_w/bar_h in map metres."""
    seg = bar_w * seg_km / total_km
    x = x0
    for i in range(sub):
        w = bar_w * (seg_km / total_km) / sub
        ax.add_patch(Rectangle((x, y0), w, bar_h,
                               facecolor="black" if i % 2 == 0 else "white",
                               edgecolor=INK, lw=0.6, zorder=56))
        x += w
    for i in range(1, total_km // seg_km):
        ax.add_patch(Rectangle((x, y0), seg, bar_h,
                               facecolor="black" if i % 2 else "white",
                               edgecolor=INK, lw=0.6, zorder=56))
        x += seg
    for km in range(0, total_km + 1, seg_km):
        ax.text(x0 + bar_w * km / total_km, y0 + bar_h * 1.4, f"{km}",
                ha="center", va="bottom", fontsize=fs, color=INK, zorder=57)
    ax.text(x0 + bar_w + bar_w * 0.16, y0 + bar_h * 1.4, "km", ha="left",
            va="bottom", fontsize=fs, color=INK, zorder=57)


def north_arrow(ax, x, y, h, color=INK):
    w = h * 0.36
    ax.add_patch(MplPolygon([[x, y + h], [x - w, y], [x, y + h * 0.26], [x + w, y]],
                            closed=True, facecolor="white", edgecolor=color,
                            lw=0.8, zorder=56))
    ax.text(x, y + h * 1.10, "N", ha="center", va="bottom", fontsize=7.5,
            color=color, fontweight="bold", zorder=57)


# ----------------------------------------------------------------------------
# 4. Build the map
# ----------------------------------------------------------------------------
def main():
    plt.rcParams.update({"font.family": "DejaVu Sans",
                         "pdf.fonttype": 42, "ps.fonttype": 42})

    transformer = Transformer.from_crs(CRS_WGS, CRS_MAP, always_xy=True)
    countries = load("countries.geojson", CRS_MAP)
    admin1 = load("pakistan_admin1.geojson", CRS_MAP)
    rivers = load("rivers.geojson", CRS_MAP)
    lakes = load("lakes.geojson", CRS_MAP)
    loc = load("line_of_control.geojson", CRS_MAP)
    # the Natural Earth claim lines also run along the Afghan border (Durand
    # line) and beyond, which is *not* the Line of Control -- keep only the
    # segments that actually bound Azad Jammu & Kashmir and are far from
    # Afghanistan.
    afg = countries[countries.ADMIN == "Afghanistan"].geometry.union_all()
    ajk_shape = admin1[admin1.name == "Azad Kashmir"].geometry.union_all()
    loc = loc[loc.geometry.apply(lambda g: g.distance(afg) > 5000
                                 and g.intersects(ajk_shape.buffer(12000)))]

    pak = countries[countries.ADMIN == "Pakistan"]
    neighbours = countries[countries.ADMIN != "Pakistan"]

    fx0, fy0, fx1, fy1 = frame_polygon(transformer).bounds
    W, H = fx1 - fx0, fy1 - fy0
    aspect = W / H

    # ---- page + axes geometry ----------------------------------------------
    map_w = PAGE_W - 2 * MARGIN
    map_h = map_w / aspect
    avail_h = PAGE_H - 2 * MARGIN - HEADER_H - FOOTER_H
    if map_h > avail_h:
        map_h, map_w = avail_h, avail_h * aspect
    slack = avail_h - map_h
    map_bottom_in = MARGIN + FOOTER_H + slack * 0.5

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    ax = fig.add_axes([(PAGE_W - map_w) / 2 / PAGE_W, map_bottom_in / PAGE_H,
                       map_w / PAGE_W, map_h / PAGE_H])
    ax.set_facecolor(C_SEA)
    ax.set_xlim(fx0, fx1)
    ax.set_ylim(fy0, fy1)
    ax.set_aspect("equal")            # rect already matches the data aspect
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(""); ax.set_ylabel("")

    # ---- graticule ----------------------------------------------------------
    meridians, parallels = graticule(transformer)
    for _, pts in meridians + parallels:
        ax.plot(pts[:, 0], pts[:, 1], color=C_GRAT, lw=0.4, ls=(0, (4, 3)),
                alpha=0.8, zorder=1)
    for lon, pts in meridians:          # longitude labels below the neatline
        if pts[:, 0].max() < fx0 or pts[:, 0].min() > fx1:
            continue
        ax.text(pts[:, 0][int(np.argmin(pts[:, 1]))], fy0 - H * 0.006,
                f"{lon}\u00b0E", ha="center", va="top", fontsize=6.2,
                color="#54697a", zorder=41, clip_on=False)
    for lat, pts in parallels:          # latitude labels left of the neatline
        if pts[:, 1].max() < fy0 or pts[:, 1].min() > fy1:
            continue
        ax.text(fx0 - W * 0.005, pts[:, 1][int(np.argmin(pts[:, 0]))],
                f"{lat}\u00b0N", ha="right", va="center", fontsize=6.2,
                color="#54697a", zorder=41, clip_on=False)

    # ---- land ---------------------------------------------------------------
    neighbours.plot(ax=ax, facecolor=C_NEIGHBOUR, edgecolor=C_NEIGHBOUR_EDGE,
                    linewidth=0.5, zorder=2)
    pak.plot(ax=ax, facecolor=C_PAK, edgecolor=C_PAK_EDGE, linewidth=1.2, zorder=4)
    admin1.boundary.plot(ax=ax, color=C_PROV_EDGE, linewidth=0.55, zorder=5)

    # ---- lakes + rivers -----------------------------------------------------
    lakes.plot(ax=ax, facecolor=C_LAKE, edgecolor=C_RIVER, linewidth=0.35, zorder=6)
    pak_zone = pak.geometry.union_all()
    riv_zone = pak_zone.buffer(90000)
    r = rivers[rivers.intersects(riv_zone)].copy()
    r["geometry"] = r.geometry.intersection(riv_zone)
    r[r.scalerank > 6].plot(ax=ax, color=C_RIVER, linewidth=0.45, alpha=0.95, zorder=6)
    r[r.scalerank <= 6].plot(ax=ax, color=C_RIVER, linewidth=0.95, zorder=7)

    # ---- Line of Control (disputed) ----------------------------------------
    loc.plot(ax=ax, color="#8a6d3b", linewidth=0.95, linestyle=(0, (5, 2.4)), zorder=8)

    # ---- neatline -----------------------------------------------------------
    ax.add_patch(Rectangle((fx0, fy0), W, H, fill=False, edgecolor="#2b3a44",
                           linewidth=1.0, zorder=50, clip_on=False))

    # ---- fixed lettering (also used as obstacles for city labels) ----------
    fixed = []

    def to_xy(lon, lat):
        return transformer.transform(lon, lat)

    def fixed_label(text, lon, lat, fs, color, weight="normal", style="normal",
                    spacing=0, alpha=1.0, zorder=20, rotation=0.0, lsp=1.15):
        x, y = to_xy(lon, lat)
        s = (" " * spacing).join(text) if spacing else text
        fixed.append(ax.text(x, y, s, ha="center", va="center", fontsize=fs,
                             color=color, fontweight=weight, fontstyle=style,
                             alpha=alpha, zorder=zorder, rotation=rotation,
                             rotation_mode="anchor", linespacing=lsp))

    fixed_label("PAKISTAN", 70.35, 28.55, 21, C_PAK_EDGE, weight="bold",
                spacing=1, alpha=0.26, zorder=15)
    fixed_label("IRAN", 61.30, 28.10, 9, C_MUTED, spacing=1, alpha=0.9)
    fixed_label("AFGHANISTAN", 64.4, 33.1, 9, C_MUTED, spacing=1, alpha=0.9)
    fixed_label("INDIA", 76.4, 26.4, 9, C_MUTED, spacing=1, alpha=0.9)
    fixed_label("CHINA", 77.2, 35.9, 8.5, C_MUTED, spacing=1, alpha=0.8)
    fixed_label("TURKMENISTAN", 61.70, 37.60, 7, C_MUTED, spacing=0, alpha=0.6)
    fixed_label("ARABIAN SEA", 67.45, 23.12, 9, "#5b7f9c", style="italic", alpha=0.95)
    fixed_label("Gilgit-Baltistan", 75.0, 35.3, 6.6, "#5f7d63", style="italic")
    # AJK is a narrow crescent (max 54 km wide), so its name is set along the
    # crescent axis; the full title of the region is given in the page header.
    fixed_label("Azad Kashmir", 73.92, 33.45, 5.8, "#3f6b47", style="italic",
                rotation=72)
    fixed_label("Balochistan", 64.4, 27.6, 7.2, "#6c8a6f", style="italic")
    fixed_label("Sindh", 69.7, 26.4, 7.2, "#6c8a6f", style="italic")
    fixed_label("Punjab", 72.7, 30.8, 7.2, "#6c8a6f", style="italic")
    # Khyber Pakhtunkhwa is a long crescent, so its name runs along the province
    # axis (NNW-SSE), the way it is set on most published maps of the country.
    fixed_label("Khyber\nPakhtunkhwa", 72.20, 35.30, 6.6, "#6c8a6f", style="italic",
                rotation=56)
    fixed_label("Indian-administered\nJammu & Kashmir", 76.35, 32.9, 6.0,
                "#9a9188", style="italic", alpha=0.9)
    fixed_label("Line of Control", 74.62, 32.86, 5.8, "#8a6d3b", style="italic",
                alpha=0.95, rotation=-25)

    # ---- city dots + collision-free labels ---------------------------------
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    placed = [t.get_window_extent(renderer=renderer).expanded(1.05, 1.25)
              for t in fixed]

    # candidate label spots: (dx, dy, ha, va) in points around the dot
    CAND = [(6.0, 0.0, "left", "center"), (-6.0, 0.0, "right", "center"),
            (0.0, 5.4, "center", "bottom"), (0.0, -5.4, "center", "top"),
            (4.8, 4.4, "left", "bottom"), (-4.8, 4.4, "right", "bottom"),
            (4.8, -4.4, "left", "top"), (-4.8, -4.4, "right", "top"),
            (0.0, 9.0, "center", "bottom"), (0.0, -9.0, "center", "top"),
            (9.5, 7.0, "left", "bottom"), (-9.5, 7.0, "right", "bottom"),
            (9.5, -7.0, "left", "top"), (-9.5, -7.0, "right", "top"),
            (14.0, 9.5, "left", "bottom"), (-14.0, 9.5, "right", "bottom"),
            (14.0, -9.5, "left", "top"), (-14.0, -9.5, "right", "top")]

    # hand-tuned preferred position for every city (checked by eye on the proof
    # print).  Islamabad / Rawalpindi / Kohat sit almost on top of each other,
    # so they are fanned out with thin leader lines instead of stacked text.
    POS = {
        "Peshawar":   (-6.0, 4.0, "right", "bottom"),
        "Islamabad":  (6.0, 5.0, "left", "bottom"),
        "Rawalpindi": (-6.0, -4.5, "right", "top"),
        "Kohat":      (6.0, 2.0, "left", "center"),
        "Bannu":      (-6.0, 0.0, "right", "center"),
        "Mianwali":   (6.0, -1.0, "left", "center"),
        "Sargodha":   (6.0, 0.0, "left", "center"),
        "D.I. Khan":  (-6.0, 0.0, "right", "center"),
        "Faisalabad": (6.0, 3.0, "left", "bottom"),
        "Lahore":     (6.0, 2.0, "left", "center"),
        "Quetta":     (6.0, 0.0, "left", "center"),
        "Karachi":    (-6.0, 4.0, "right", "bottom"),
        "Hyderabad":  (6.0, 3.0, "left", "bottom"),
    }
    LEADER = {"Islamabad", "Rawalpindi", "Kohat", "Peshawar"}

    halo = [pe.withStroke(linewidth=2.3, foreground="white")]
    dot_ms = 5.9
    dot_px = dot_ms * fig.dpi / 72
    report = []

    # every dot is an obstacle for every label, so text never sits on a marker
    def dot_box(name):
        lat, lon = next((c[1], c[2]) for c in CITIES if c[0] == name)
        px, py = ax.transData.transform(to_xy(lon, lat))
        r = dot_px * 0.62
        return matplotlib.transforms.Bbox.from_bounds(px - r, py - r, 2 * r, 2 * r)

    dot_boxes = {c[0]: dot_box(c[0]) for c in CITIES}

    for name, lat, lon, rank in sorted(CITIES, key=lambda c: (c[3], c[0])):
        x, y = to_xy(lon, lat)
        fs = 9.6 if rank == 1 else (9.0 if rank == 2 else 8.4)
        ax.plot([x], [y], marker="o", markersize=dot_ms, color=C_DOT,
                markeredgecolor="white", markeredgewidth=0.75, zorder=25,
                linestyle="none", clip_on=False)

        obstacles = [bb for n, bb in dot_boxes.items() if n != name] + placed
        cands = list(CAND)
        if name in POS:
            cands = [POS[name]] + [c for c in cands if c != POS[name]]
        lead = ({'arrowprops': dict(arrowstyle="-", color="#2f6b3d", lw=0.6,
                                    shrinkA=1.5, shrinkB=2.5)}
                if name in LEADER else {})

        chosen, scored = None, []
        for dx, dy, ha, va in cands:
            t = ax.annotate(name, xy=(x, y), xytext=(dx, dy),
                            textcoords="offset points", ha=ha, va=va,
                            fontsize=fs, color=C_TEXT, zorder=26,
                            path_effects=halo, **lead)
            bb = t.get_window_extent(renderer=renderer).expanded(1.05, 1.25)
            if (bb.x0 < 2 or bb.y0 < 2 or bb.x1 > fig.bbox.width - 2
                    or bb.y1 > fig.bbox.height - 2):
                t.remove(); continue
            area = 0.0
            for o in obstacles:
                if bb.overlaps(o):
                    ix0, iy0 = max(bb.x0, o.x0), max(bb.y0, o.y0)
                    ix1, iy1 = min(bb.x1, o.x1), min(bb.y1, o.y1)
                    area += max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
            if area == 0.0:
                chosen = (t, bb); break
            scored.append((area, (dx, dy, ha, va)))
            t.remove()
        if chosen is None:                       # least-overlap fallback
            scored.sort(key=lambda r: r[0])
            area, (dx, dy, ha, va) = scored[0]
            t = ax.annotate(name, xy=(x, y), xytext=(dx, dy),
                            textcoords="offset points", ha=ha, va=va, fontsize=fs,
                            color=C_TEXT, zorder=26, path_effects=halo, **lead)
            chosen = (t, t.get_window_extent(renderer=renderer))
            report.append(f"  \u00b7 {name}: {area:.0f} px\u00b2 of overlap in every "
                          f"candidate spot (placed the least crowded one)")
        placed.append(chosen[1])

    # ---- scale bar + north arrow (over the Arabian Sea, no land covered) ---
    sb_x, _ = to_xy(61.55, 23.62)
    sb_y, _ = to_xy(61.55, 23.30)
    bar_w, bar_h = 300000.0, 46000.0
    pad_x, pad_y = 42000.0, 40000.0
    na_x, na_y = to_xy(65.55, 23.32)
    na_h = 92000.0
    box_x0 = sb_x - pad_x
    box_x1 = max(sb_x + bar_w, na_x + na_h * 0.42) + pad_x
    box_y0 = sb_y - pad_y * 0.9
    box_y1 = sb_y + bar_h + pad_y * 1.9
    ax.add_patch(Rectangle((box_x0, box_y0), box_x1 - box_x0, box_y1 - box_y0,
                           facecolor="white", edgecolor="#8a949b", lw=0.7, zorder=55))
    scale_bar(ax, sb_x, sb_y, bar_w, bar_h)
    north_arrow(ax, na_x, na_y, na_h)

    # ---- header -------------------------------------------------------------
    title_y = 1 - (MARGIN + 0.12) / PAGE_H
    fig.text(0.5, title_y, "P A K I S T A N", ha="center", va="top", fontsize=27,
             fontweight="bold", color="#17351f")
    fig.text(0.5, title_y - 0.55 / PAGE_H,
             "Major Cities Map", ha="center", va="top", fontsize=13.5,
             color="#2f6b3d")
    fig.text(0.5, title_y - 0.92 / PAGE_H,
             "Including Azad Jammu & Kashmir and Gilgit-Baltistan",
             ha="center", va="top", fontsize=9.5, color=C_MUTED)
    fig.add_artist(plt.Line2D([0.5 - 0.18, 0.5 + 0.18],
                              [(title_y - 1.12 / PAGE_H)] * 2,
                              transform=fig.transFigure, color="#c3d6c6", lw=1.2))

    # ---- footer panel: legend + notes --------------------------------------
    FOOT_X0 = MARGIN
    FOOT_W = PAGE_W - 2 * MARGIN
    foot = fig.add_axes([FOOT_X0 / PAGE_W, MARGIN / PAGE_H,
                         FOOT_W / PAGE_W, (FOOTER_H - 0.16) / PAGE_H], zorder=1)
    foot.set_facecolor("#f7f9f8")
    foot.set_xticks([]); foot.set_yticks([])
    for s in foot.spines.values():
        s.set_color("#ccd6d2"); s.set_linewidth(0.7)
    foot.set_xlim(0, 1); foot.set_ylim(0, 1)

    foot.text(0.022, 0.955, "LEGEND", fontsize=7.6, fontweight="bold", color=INK,
              ha="left", va="top")
    legend_rows = [
        ("city", "Major city (green dot)"),
        ("pak", "Pakistan (incl. AJK & Gilgit-Baltistan)"),
        ("nbr", "Neighbouring country"),
        ("loc", "Line of Control (disputed)"),
        ("prov", "Provincial / administrative boundary"),
        ("river", "River"),
        ("lake", "Lake / reservoir"),
        ("grat", "Graticule (5\u00b0 spacing)"),
    ]
    for i, (kind, label) in enumerate(legend_rows):
        col, row = divmod(i, 3)                 # 3 columns of up to 3 items
        xx = 0.030 + col * 0.330
        yy = 0.775 - row * 0.165
        sx = xx + 0.026
        if kind == "city":
            foot.plot([sx], [yy], marker="o", markersize=5.2, color=C_DOT,
                      markeredgecolor="white", markeredgewidth=0.75, linestyle="none")
        elif kind in ("pak", "nbr"):
            foot.add_patch(Rectangle((sx - 0.015, yy - 0.048), 0.030, 0.096,
                                     facecolor=C_PAK if kind == "pak" else C_NEIGHBOUR,
                                     edgecolor=C_PAK_EDGE if kind == "pak" else C_NEIGHBOUR_EDGE,
                                     lw=0.6))
        elif kind == "loc":
            foot.plot([sx - 0.020, sx + 0.020], [yy, yy], color="#8a6d3b", lw=0.95,
                      ls=(0, (4, 2)))
        elif kind == "prov":
            foot.plot([sx - 0.020, sx + 0.020], [yy, yy], color=C_PROV_EDGE, lw=0.9)
        elif kind == "river":
            foot.plot([sx - 0.020, sx + 0.020], [yy, yy], color=C_RIVER, lw=1.2)
        elif kind == "lake":
            foot.add_patch(Rectangle((sx - 0.015, yy - 0.028), 0.030, 0.056,
                                     facecolor=C_LAKE, edgecolor=C_RIVER, lw=0.5))
        elif kind == "grat":
            foot.plot([sx - 0.020, sx + 0.020], [yy, yy], color=C_GRAT, lw=0.6,
                      ls=(0, (3, 2)))
        foot.text(sx + 0.030, yy, label, fontsize=6.7, color="#25333e",
                  ha="left", va="center")

    foot.plot([0.022, 0.978], [0.325, 0.325], color="#d3dbd8", lw=0.7)
    note = ("Pakistan is shown as administered: the map includes Azad Jammu & Kashmir (AJK) and "
            "Gilgit-Baltistan; the Line of Control is drawn as a dashed disputed boundary.\n"
            "Boundaries: Natural Earth 1:10m, public domain (naturalearthdata.com).  "
            "City positions cross-checked against the GeoNames gazetteer.\n"
            "Projection: Lambert Conformal Conic, WGS 84, standard parallels 24\u00b0N / 33\u00b0N; local scale is "
            "within ~0.3 % of true at every city plotted.\n"
            "Print this page at 100% / actual size on A4 paper \u2014 the scale bar is accurate as drawn.  Vector PDF, 1 page.")
    foot.text(0.022, 0.290, note, fontsize=6.0, color="#7b878a", ha="left", va="top",
              linespacing=1.62, wrap=False)

    # thin page border
    b = 0.25
    fig.add_artist(Rectangle((b / PAGE_W, b / PAGE_H), 1 - 2 * b / PAGE_W,
                             1 - 2 * b / PAGE_H, transform=fig.transFigure,
                             fill=False, edgecolor="#dde3e6", lw=0.6, zorder=-5))

    # geopandas sets axis labels to the CRS axis names -- clear them last
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.xaxis.set_visible(False); ax.yaxis.set_visible(False)

    fig.savefig(PDF_OUT, format="pdf",
                metadata={"Title": "Pakistan Major Cities Map "
                                   "(including Azad Jammu & Kashmir and Gilgit-Baltistan)",
                          "Author": "InfiniteTalk map generator",
                          "Subject": "Printable A4 map of Pakistan with 13 major cities",
                          "Keywords": "Pakistan, cities, map, AJK, Gilgit-Baltistan, A4"})
    fig.savefig(PNG_OUT, dpi=300)

    for line in report:
        print(line)
    print("cities labelled:", len(CITIES))
    print("page %.3f x %.3f in | map %.2f x %.2f in | aspect %.3f"
          % (PAGE_W, PAGE_H, map_w, map_h, aspect))
    print("wrote", PDF_OUT)
    print("wrote", PNG_OUT)


if __name__ == "__main__":
    main()

