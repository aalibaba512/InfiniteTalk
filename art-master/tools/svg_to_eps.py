"""Convert a traced master SVG (vtracer output) to a print EPS.

The traced SVG contains only absolute M / C / Z path commands plus
translate() transforms and flat hex fills, which makes the conversion to
PostScript exact:

    SVG px space (W_PX x H_PX)  ->  EPS pt space (ft_w*12*72 x ft_h*12*72),
    y axis flipped (PostScript is y-up).

Usage:
    svg_to_eps.py --svg IN.svg --eps OUT.eps --px 2780 1472 --ft 17 9
    add --check to also render the identical transformed path data through
    reportlab to a proof PDF/PNG for visual verification.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def parse_paths(svg_text: str):
    """Yield (fill_hex, tx, ty, segments) in document order.

    segments: list of (cmd, [numbers]) with M/C/Z only (vtracer guarantee).
    """
    for m in re.finditer(r"<path\s+([^>]*?)/>", svg_text):
        at = m.group(1)
        d = re.search(r'd="([^"]*)"', at).group(1)
        fill = re.search(r'fill="([^"]*)"', at).group(1)
        tr = re.search(r'transform="translate\((%s)[ ,](%s)\)"' % (NUM, NUM), at)
        tx, ty = (float(tr.group(1)), float(tr.group(2))) if tr else (0.0, 0.0)
        segs, cmd, nums = [], None, []
        for t in re.findall(r"[MCZ]|" + NUM, d):
            if t.isalpha():
                if cmd is not None:
                    segs.append((cmd, nums)); nums = []
                cmd = t
            else:
                nums.append(float(t))
        if cmd is not None:
            segs.append((cmd, nums))
        yield fill, tx, ty, segs


def rgb(fill: str) -> str:
    r, g, b = (int(fill[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return f"{r:.4f} {g:.4f} {b:.4f}"


def write_eps(svg_text: str, out: Path, w_px: float, h_px: float,
              w_pt: float, h_pt: float, title: str) -> int:
    sx, sy = w_pt / w_px, h_pt / h_px
    n = 0
    with open(out, "w") as f:
        f.write("%!PS-Adobe-3.0 EPSF-3.0\n"
                "%%Creator: vtracer 0.6.15 + art-master/tools/svg_to_eps.py\n"
                f"%%Title: {title}\n"
                f"%%BoundingBox: 0 0 {int(w_pt)} {int(h_pt)}\n"
                f"%%HiResBoundingBox: 0 0 {w_pt:.2f} {h_pt:.2f}\n"
                "%%DocumentData: Clean7Bit\n"
                "%%LanguageLevel: 2\n"
                "%%Pages: 1\n"
                "%%EndComments\n"
                "%%Page: 1 1\n"
                "save\n")
        for fill, tx, ty, segs in parse_paths(svg_text):
            f.write(f"{rgb(fill)} setrgbcolor\nnewpath\n")
            for cmd, nums in segs:
                if cmd == "M":
                    x, y = nums[0] + tx, nums[1] + ty
                    f.write(f"{x*sx:.2f} {h_pt-y*sy:.2f} moveto\n")
                elif cmd == "C":
                    pts = [nums[i] + (tx if i % 2 == 0 else ty) for i in range(6)]
                    X = [pts[0]*sx, h_pt-pts[1]*sy, pts[2]*sx, h_pt-pts[3]*sy,
                         pts[4]*sx, h_pt-pts[5]*sy]
                    f.write(f"{X[0]:.2f} {X[1]:.2f} {X[2]:.2f} {X[3]:.2f} "
                            f"{X[4]:.2f} {X[5]:.2f} curveto\n")
                elif cmd == "Z":
                    f.write("closepath\n")
            f.write("fill\n")
            n += 1
        f.write("restore\n%%EOF\n")
    return n


def write_check_pdf(svg_text: str, out_pdf: Path, w_px, h_px, w_pt, h_pt) -> None:
    from reportlab.pdfgen import canvas

    sx, sy = w_pt / w_px, h_pt / h_px
    c = canvas.Canvas(str(out_pdf), pagesize=(w_pt, h_pt))
    for fill, tx, ty, segs in parse_paths(svg_text):
        p = c.beginPath()
        for cmd, nums in segs:
            if cmd == "M":
                p.moveTo((nums[0]+tx)*sx, h_pt-(nums[1]+ty)*sy)
            elif cmd == "C":
                pts = [nums[i] + (tx if i % 2 == 0 else ty) for i in range(6)]
                p.curveTo(pts[0]*sx, h_pt-pts[1]*sy, pts[2]*sx, h_pt-pts[3]*sy,
                          pts[4]*sx, h_pt-pts[5]*sy)
            elif cmd == "Z":
                p.close()
        r, g, b = (int(fill[i:i+2], 16)/255.0 for i in (1, 3, 5))
        c.setFillColorRGB(r, g, b)
        c.setStrokeColorRGB(r, g, b)
        c.drawPath(p, fill=1, stroke=0)
    c.save()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--eps", required=True)
    ap.add_argument("--px", nargs=2, type=float, required=True,
                    help="pixel space of the traced svg, e.g. 2780 1472")
    ap.add_argument("--ft", nargs=2, type=float, required=True,
                    help="physical size in feet, e.g. 17 9")
    ap.add_argument("--title", default="large-format wall master")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--check-dir", default=None,
                    help="where to write _eps_check proof files (default: eps dir)")
    a = ap.parse_args()

    w_pt, h_pt = a.ft[0] * 12 * 72, a.ft[1] * 12 * 72
    svg_text = Path(a.svg).read_text()
    n = write_eps(svg_text, Path(a.eps), a.px[0], a.px[1], w_pt, h_pt, a.title)
    print(f"wrote {a.eps}: {n} filled paths, BoundingBox 0 0 {int(w_pt)} {int(h_pt)} pt "
          f"({a.ft[0]} ft x {a.ft[1]} ft), {Path(a.eps).stat().st_size//1024} KiB")

    if a.check:
        import PIL.Image
        import pymupdf
        here = Path(a.check_dir) if a.check_dir else Path(a.eps).resolve().parent
        here.mkdir(parents=True, exist_ok=True)
        pdf = here / "_eps_check.pdf"
        write_check_pdf(svg_text, pdf, a.px[0], a.px[1], w_pt, h_pt)
        doc = pymupdf.open(str(pdf))
        pg = doc[0]
        z = 1600 / pg.rect.width
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
        img = PIL.Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(here / "_eps_check_proof.png")
        print(f"check proof -> {here / '_eps_check_proof.png'} {img.size}")
        doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
