"""Convert the traced option-2 master SVG to a print EPS (and a check PDF).

The traced SVG (vtracer output) contains only absolute M / C / Z path
commands plus translate() transforms and flat hex fills, which makes the
conversion to PostScript exact:

    SVG px space (2780 x 1472)  ->  EPS pt space (14688 x 7776)
    = 17 ft x 9 ft at 72 pt/inch, y axis flipped (PostScript is y-up).

Usage:
    .venv-art/bin/python art-master/tools/svg_to_eps.py            # write EPS
    .venv-art/bin/python art-master/tools/svg_to_eps.py --check    # also write
                                a reportlab PDF of the same transformed path
                                data and render a 1600px proof for comparison
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SVG = HERE / "chasing_innovation_option2_master.svg"
EPS = HERE / "chasing_innovation_option2_master.eps"

W_PX, H_PX = 2780.0, 1472.0
W_PT, H_PT = 17 * 12 * 72.0, 9 * 12 * 72.0      # 14688 x 7776
SX, SY = W_PT / W_PX, H_PT / H_PX

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def parse_paths(svg_text: str):
    """Yield (fill_hex, tx, ty, segments) in document order.

    segments: list of (cmd, [x,y,...]) with M/C/Z only (vtracer guarantee).
    """
    for m in re.finditer(r"<path\s+([^>]*?)/>", svg_text):
        at = m.group(1)
        d = re.search(r'd="([^"]*)"', at).group(1)
        fill = re.search(r'fill="([^"]*)"', at).group(1)
        tr = re.search(r'transform="translate\((%s)[ ,](%s)\)"' % (NUM, NUM), at)
        tx, ty = (float(tr.group(1)), float(tr.group(2))) if tr else (0.0, 0.0)
        segs, cmd, nums = [], None, []
        toks = re.findall(r"[MCZ]|" + NUM, d)
        for t in toks:
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


def write_eps(svg_text: str, out: Path) -> int:
    n = 0
    with open(out, "w") as f:
        f.write("%!PS-Adobe-3.0 EPSF-3.0\n"
                "%%Creator: vtracer 0.6.15 + art-master/tools/svg_to_eps.py\n"
                "%%Title: CHASING INNOVATION - 17ft x 9ft wall master (option 2)\n"
                f"%%BoundingBox: 0 0 {int(W_PT)} {int(H_PT)}\n"
                f"%%HiResBoundingBox: 0 0 {W_PT:.2f} {H_PT:.2f}\n"
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
                    f.write(f"{x*SX:.2f} {H_PT-y*SY:.2f} moveto\n")
                elif cmd == "C":
                    pts = [nums[i] + (tx if i % 2 == 0 else ty) for i in range(6)]
                    X = [pts[0]*SX, H_PT-pts[1]*SY, pts[2]*SX, H_PT-pts[3]*SY,
                         pts[4]*SX, H_PT-pts[5]*SY]
                    f.write(f"{X[0]:.2f} {X[1]:.2f} {X[2]:.2f} {X[3]:.2f} "
                            f"{X[4]:.2f} {X[5]:.2f} curveto\n")
                elif cmd == "Z":
                    f.write("closepath\n")
            f.write("fill\n")
            n += 1
        f.write("restore\n%%EOF\n")
    return n


def write_check_pdf(svg_text: str, out_pdf: Path) -> None:
    """Same transformed path data through reportlab -> renderable proof."""
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(out_pdf), pagesize=(W_PT, H_PT))
    for fill, tx, ty, segs in parse_paths(svg_text):
        p = c.beginPath()
        for cmd, nums in segs:
            if cmd == "M":
                p.moveTo((nums[0]+tx)*SX, H_PT-(nums[1]+ty)*SY)
            elif cmd == "C":
                pts = [nums[i] + (tx if i % 2 == 0 else ty) for i in range(6)]
                p.curveTo(pts[0]*SX, H_PT-pts[1]*SY, pts[2]*SX, H_PT-pts[3]*SY,
                          pts[4]*SX, H_PT-pts[5]*SY)
            elif cmd == "Z":
                p.close()
        r, g, b = (int(fill[i:i+2], 16)/255.0 for i in (1, 3, 5))
        c.setFillColorRGB(r, g, b)
        c.setStrokeColorRGB(r, g, b)
        c.drawPath(p, fill=1, stroke=0)
    c.save()


def main() -> int:
    svg_text = SVG.read_text()
    n = write_eps(svg_text, EPS)
    print(f"wrote {EPS.name}: {n} filled paths, "
          f"BoundingBox 0 0 {int(W_PT)} {int(H_PT)} pt "
          f"({W_PT/72/12:.1f} ft x {H_PT/72/12:.1f} ft), "
          f"{EPS.stat().st_size//1024} KiB")
    if "--check" in sys.argv:
        pdf = HERE / "_smoke" / "eps_check.pdf"
        write_check_pdf(svg_text, pdf)
        import PIL.Image
        import pymupdf
        doc = pymupdf.open(str(pdf))
        pg = doc[0]
        z = 1600 / pg.rect.width
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
        img = PIL.Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(HERE / "_smoke" / "eps_check_proof.png")
        print(f"check PDF {pg.rect.width:.0f}x{pg.rect.height:.0f} pt -> "
              f"eps_check_proof.png {img.size}")
        doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
