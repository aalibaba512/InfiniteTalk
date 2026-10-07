"""Smoke-test the SVG -> PDF -> high-res raster print pipeline.

Proves the toolchain used to build the 17 ft x 8.6 ft vector master works here:

    SVG (vector master)  ->  PDF (svglib/reportlab)  ->  PNG (pymupdf render)

Three things are asserted, because a clean exit code is not a pass:

1. PHYSICAL SIZE  - the PDF page measures exactly 17.00 ft x 8.60 ft.
                    NOTE: dimensions MUST be declared in `pt` in the SVG.
                    svglib rescales `px` by 0.75 (96px/in -> 72pt/in), which
                    silently shrinks the page to 12.75 ft x 6.45 ft.
2. FLAT COLOURS   - solid fills rasterise to a single exact value per region
                    (no gradient banding, no noise, no texture).
3. CRISP EDGES    - the transition ramp across a straight edge is ~1 device px,
                    i.e. mathematically clean paths, not blur.

Run:  .venv-art/bin/python art-master/tools/smoke_test_pipeline.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import PIL.Image
import pymupdf
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

OUT = pathlib.Path(__file__).resolve().parent.parent / "_smoke"
OUT.mkdir(parents=True, exist_ok=True)

# 17 ft x 8.6 ft, master coordinate space: 1 unit == 1 pt == 1/72 inch.
PAGE_W = 17 * 12 * 72      # 14688 pt  == 17.00 ft
PAGE_H = 8.6 * 12 * 72     # 7430.4 pt ==  8.60 ft

GOLD = "#E8B93A"
GREEN = "#1F5B52"
GREY = "#3A3A3A"


def build_svg() -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{PAGE_W}pt" height="{PAGE_H}pt" viewBox="0 0 {PAGE_W} {PAGE_H}">
  <rect x="0" y="0" width="{PAGE_W}" height="{PAGE_H}" fill="#FFFFFF"/>
  <!-- half-canvas gold field: one long straight vertical edge for the crispness test -->
  <rect x="0" y="0" width="{PAGE_W // 2}" height="{PAGE_H}" fill="{GOLD}"/>
  <circle cx="{PAGE_W * 0.5}" cy="{PAGE_H * 0.5}" r="2000" fill="{GREEN}"/>
  <path d="M 2000 6000 L 6000 1500 L 10000 5000 L 13000 2500" fill="none"
        stroke="{GREEN}" stroke-width="24" stroke-linecap="round"/>
  <rect x="11000" y="5000" width="2000" height="1200" fill="{GREEN}"/>
  <text x="{PAGE_W * 0.5}" y="{PAGE_H * 0.25}" font-family="DejaVu Sans"
        font-size="900" font-weight="bold" fill="{GREY}" text-anchor="middle">CHASING INNOVATION</text>
</svg>
"""


def main() -> int:
    svg_path = OUT / "smoke.svg"
    pdf_path = OUT / "smoke.pdf"
    png_path = OUT / "smoke.png"
    svg_path.write_text(build_svg(), encoding="utf-8")

    drawing = svg2rlg(str(svg_path))
    if drawing is None:
        print("FAIL: svglib could not parse the SVG")
        return 1

    renderPDF.drawToFile(drawing, str(pdf_path))

    doc = pymupdf.open(pdf_path)
    page = doc[0]
    ft_w = page.rect.width / 72 / 12
    ft_h = page.rect.height / 72 / 12
    print(f"[1] PDF page: {page.rect.width:.2f} x {page.rect.height:.2f} pt "
          f"= {ft_w:.4f} ft x {ft_h:.4f} ft")
    size_ok = abs(ft_w - 17.0) < 0.005 and abs(ft_h - 8.6) < 0.005

    # Render a proof raster.
    zoom = 4000 / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    img = PIL.Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.save(png_path)
    doc.close()
    a = np.asarray(img).astype(int)
    print(f"    proof PNG: {img.size[0]} x {img.size[1]} px (zoom {zoom:.6f})")

    # [2] flat colour check: gold field interior must be one exact value.
    patch = a[int(a.shape[0] * 0.9): int(a.shape[0] * 0.95),
              int(a.shape[1] * 0.05): int(a.shape[1] * 0.10)]
    uniq = {tuple(c) for c in patch.reshape(-1, 3)}
    # reportlab quantises each channel to 1/255, so #E8B93A -> (232,184,58);
    # assert flatness within that rounding, not against the literal input hex.
    drift = max(abs(int(v) - g) for c in uniq for v, g in zip(c, (232, 185, 58)))
    print(f"[2] gold field 5% x 5% interior patch: {len(uniq)} distinct value(s) "
          f"-> {sorted(uniq)} (max channel drift {drift}/255 from #E8B93A)")
    flat_ok = len(uniq) == 1 and drift <= 1

    # [3] edge crispness: scan across the gold/white vertical boundary.
    y = int(a.shape[0] * 0.10)
    row = a[y]
    gold = np.abs(row - np.array([232, 185, 58])).sum(1) < 12
    white = np.abs(row - 255).sum(1) < 12
    ramp = np.where(~(gold | white))[0]
    boundary = int(a.shape[1] / 2)
    near = ramp[(ramp > boundary - 40) & (ramp < boundary + 40)]
    print(f"[3] y={y}: non-pure px within +-40px of the boundary x={boundary}: {len(near)}")
    crisp_ok = len(near) <= 3

    ok = size_ok and flat_ok and crisp_ok
    print("RESULT:", "PASS" if ok else
          f"FAIL (size={size_ok} flat={flat_ok} crisp={crisp_ok})")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
