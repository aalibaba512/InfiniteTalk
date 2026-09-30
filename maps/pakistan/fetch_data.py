#!/usr/bin/env python3
"""
Build the small, printable-ready vector layers used by make_pakistan_map.py
from the public-domain Natural Earth 1:10m dataset.

Usage:
    python3 fetch_data.py /path/to/natural-earth-vector/geojson

Source: https://github.com/nvkelso/natural-earth-vector  (public domain, v5.x)
If you do not have a local copy:
    git clone --depth 1 https://github.com/nvkelso/natural-earth-vector.git

Writes into ./data/ :
    countries.geojson        admin-0 countries around Pakistan (Pakistan's
                             polygon includes Azad Jammu & Kashmir + Gilgit-Baltistan)
    pakistan_admin1.geojson  provinces / administered areas of Pakistan
    rivers.geojson           river centrelines
    lakes.geojson            lakes and reservoirs
    line_of_control.geojson  Line of Control (Natural Earth "disputed" layer)
"""
from __future__ import annotations

import os
import sys
import geopandas as gpd
from shapely.geometry import box

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")

# wide clip so that nothing "ends" inside the printed map frame
WIDE = box(48, 8, 92, 52)
# tighter clip for the Pakistani detail layers
PAK_WIN = box(59, 20.5, 81, 39.5)


def clip(gdf, window):
    return gpd.clip(gdf, window).reset_index(drop=True)


def main(src: str):
    os.makedirs(OUT, exist_ok=True)
    b = WIDE.bounds

    g = gpd.read_file(f"{src}/ne_10m_admin_0_countries.geojson",
                      bbox=(b[0], b[1], b[2], b[3]), engine="pyogrio")
    g = clip(g, WIDE)[["ADMIN", "SOVEREIGNT", "TYPE", "NAME", "ISO_A3", "geometry"]]
    g.to_file(f"{OUT}/countries.geojson", driver="GeoJSON")

    pb = PAK_WIN.bounds
    a = gpd.read_file(f"{src}/ne_10m_admin_1_states_provinces.geojson",
                      bbox=(pb[0], pb[1], pb[2], pb[3]), engine="pyogrio")
    a = clip(a[a["admin"] == "Pakistan"], PAK_WIN)[
        ["name", "type_en", "iso_3166_2", "geometry"]]
    a.to_file(f"{OUT}/pakistan_admin1.geojson", driver="GeoJSON")

    r = gpd.read_file(f"{src}/ne_10m_rivers_lake_centerlines.geojson",
                      bbox=(pb[0], pb[1], pb[2], pb[3]), engine="pyogrio")
    r = clip(r[r["featurecla"] == "River"], PAK_WIN)[
        ["name", "name_en", "scalerank", "geometry"]]
    r.to_file(f"{OUT}/rivers.geojson", driver="GeoJSON")

    l = gpd.read_file(f"{src}/ne_10m_lakes.geojson",
                      bbox=(pb[0], pb[1], pb[2], pb[3]), engine="pyogrio")
    l = clip(l, PAK_WIN)[["name", "name_en", "scalerank", "geometry"]]
    l.to_file(f"{OUT}/lakes.geojson", driver="GeoJSON")

    d = gpd.read_file(f"{src}/ne_10m_admin_0_boundary_lines_disputed_areas.geojson",
                      bbox=(pb[0], pb[1], pb[2], pb[3]), engine="pyogrio")
    loc = d[(d["NAME"] == "Indian claim") & (d["ADM0_LEFT"] == "Pakistan")]
    loc = clip(loc, PAK_WIN)[["NAME", "FEATURECLA", "geometry"]]
    loc.to_file(f"{OUT}/line_of_control.geojson", driver="GeoJSON")

    for f in sorted(os.listdir(OUT)):
        print(f"  {f:28s} {os.path.getsize(os.path.join(OUT, f))/1024:8.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
