"""Render the vector master to a PNG proof via MuPDF.

usage:  render_proof.py [width_px] [out_png]
"""
import sys
from pathlib import Path

import PIL.Image
import pymupdf

HERE = Path(__file__).resolve().parent.parent
SVG = HERE / "chasing_innovation_master.svg"


def main() -> int:
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 1600
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "_smoke" / "proof.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(SVG))
    pg = doc[0]
    z = width / pg.rect.width
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    img = PIL.Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.save(out)
    print(f"proof: {img.size[0]}x{img.size[1]} -> {out}  (page {pg.rect.width:.1f}x{pg.rect.height:.1f} pt)")
    doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
