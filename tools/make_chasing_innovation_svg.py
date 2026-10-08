#!/usr/bin/env python3
"""
make_chasing_innovation_svg.py — hand-authored flat vector artwork.

Recreates the "Chasing Innovation" composition as clean native SVG
(perfect circles, smooth beziers, rounded caps — no tracing involved):

  center rocket · circuit traces L/R · gears · chips · propellers ·
  two drones · satellite · paper-cut mountains · title text

Usage:  python3 tools/make_chasing_innovation_svg.py [out.svg]
"""

import math
import sys
from pathlib import Path

W, H = 1600, 840

# palette sampled from the original artwork
BG        = "#F4F5F2"
TEAL_DARK = "#1E4B42"
TEAL_MID  = "#2E5F53"
SAGE      = "#7A9474"
SAGE_LT   = "#93A88B"
GOLD      = "#C9A24B"
GOLD_LT   = "#DCC084"
CREAM     = "#F1EAD8"
GRAY      = "#8D908D"
TEXT      = "#2E8B6A"

P: list[str] = []


def circle(cx, cy, r, fill, stroke=None, sw=0):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    P.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}/>')


def ring_node(x, y, color, r=9):
    circle(x, y, r, "none", color, 5)


def dot(x, y, color, r=8):
    circle(x, y, r, color)


def trace(pts, color, w=5, node=True, start_ring=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    P.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
             f'stroke-linecap="round" stroke-linejoin="round"/>')
    if node:
        dot(*pts[-1], color)
    if start_ring:
        ring_node(*pts[0], color)


def circle_path(cx, cy, r):
    return (f"M{cx + r},{cy} A{r},{r} 0 1,0 {cx - r},{cy} "
            f"A{r},{r} 0 1,0 {cx + r},{cy} Z")


def gear(cx, cy, R, teeth, fill, hole=0.34, spokes=0):
    step = 2 * math.pi / teeth
    pts = []
    for i in range(teeth):
        a = i * step
        for r, da in ((R * 0.80, 0.00), (R, 0.16 * step),
                      (R, 0.50 * step), (R * 0.80, 0.66 * step)):
            ang = a + da
            pts.append(f"{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}")
    d = "M" + " L".join(pts) + " Z "
    d += circle_path(cx, cy, R * hole)
    for k in range(spokes):  # decorative round cut-outs
        a = k * 2 * math.pi / spokes + step / 2
        d += circle_path(cx + R * 0.52 * math.cos(a), cy + R * 0.52 * math.sin(a),
                         R * 0.16)
    P.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd"/>')


def chip(cx, cy, s, body=TEAL_MID, pins=GOLD):
    h = s / 2
    for i in (-0.3, 0, 0.3):  # pins both sides
        for sx in (-1, 1):
            P.append(f'<path d="M{cx + sx * h},{cy + i * s} h{sx * 10}" '
                     f'stroke="{pins}" stroke-width="4" stroke-linecap="round"/>')
        for sy in (-1, 1):
            P.append(f'<path d="M{cx + i * s},{cy + sy * h} v{sy * 10}" '
                     f'stroke="{pins}" stroke-width="4" stroke-linecap="round"/>')
    P.append(f'<rect x="{cx - h}" y="{cy - h}" width="{s}" height="{s}" rx="6" fill="{body}"/>')
    P.append(f'<rect x="{cx - h * 0.45}" y="{cy - h * 0.45}" width="{s * 0.45}" '
             f'height="{s * 0.45}" rx="3" fill="{SAGE}"/>')


def propeller(cx, cy, r, fill=GRAY):
    circle(cx, cy, r * 0.16, fill)
    for k in range(3):
        ang = 90 + k * 120
        a = math.radians(ang)
        bx, by = cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a)
        P.append(f'<ellipse cx="{bx:.1f}" cy="{by:.1f}" rx="{r * 0.52}" ry="{r * 0.15}" '
                 f'fill="{fill}" transform="rotate({ang} {bx:.1f} {by:.1f})"/>')


def drone(cx, cy, s=1.0, body=GRAY):
    w, h = 70 * s, 16 * s
    P.append(f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" '
             f'rx="{h / 2}" fill="{body}"/>')
    for sx in (-1, 1):  # arms + rotors
        rx = cx + sx * w * 0.78
        P.append(f'<path d="M{cx + sx * w * 0.35},{cy} L{rx},{cy - 18 * s}" '
                 f'stroke="{body}" stroke-width="{7 * s}" stroke-linecap="round"/>')
        P.append(f'<ellipse cx="{rx}" cy="{cy - 22 * s}" rx="{34 * s}" ry="{5 * s}" fill="{body}"/>')
        P.append(f'<rect x="{rx - 4 * s}" y="{cy - 26 * s}" width="{8 * s}" '
                 f'height="{10 * s}" fill="{TEAL_MID}"/>')
    for sx in (-1, 1):  # legs
        P.append(f'<path d="M{cx + sx * w * 0.3},{cy + h / 2} q{sx * 8 * s},{26 * s} {sx * 4 * s},{34 * s}" '
                 f'fill="none" stroke="{body}" stroke-width="{6 * s}" stroke-linecap="round"/>')
    P.append(f'<rect x="{cx - 12 * s}" y="{cy + h / 2}" width="{24 * s}" height="{18 * s}" rx="4" fill="{body}"/>')
    circle(cx, cy + h / 2 + 9 * s, 6 * s, TEAL_MID)


def satellite(cx, cy, rot=-32):
    P.append(f'<g transform="translate({cx},{cy}) rotate({rot})">')
    P.append(f'<rect x="-34" y="-60" width="68" height="120" rx="10" fill="{TEAL_DARK}"/>')
    P.append(f'<rect x="-34" y="-14" width="68" height="26" fill="{GOLD}"/>')
    for py in (-1, 1):  # solar panels
        P.append(f'<rect x="{-150 if py < 0 else 82}" y="-42" width="68" height="84" '
                 f'rx="4" fill="{TEAL_MID}"/>')
        for i in range(1, 3):
            yy = -42 + i * 28
            P.append(f'<path d="M{-150 if py < 0 else 82},{yy} h68" stroke="{TEAL_DARK}" stroke-width="4"/>')
        for i in range(1, 3):
            xx = (-150 if py < 0 else 82) + i * 22.6
            P.append(f'<path d="M{xx},-42 v84" stroke="{TEAL_DARK}" stroke-width="4"/>')
        P.append(f'<path d="M{-82 if py < 0 else 34},0 h{48 if py < 0 else 48}" '
                 f'stroke="{GOLD}" stroke-width="6"/>')
    P.append(f'<path d="M-20,60 a20,20 0 0,0 40,0 Z" fill="{TEAL_DARK}"/>')  # dish
    for i in range(1, 4):  # signal arcs under the dish
        P.append(f'<path d="M{-13 * i},{92 + 7 * i} a{13 * i},{13 * i} 0 0,1 {26 * i},0" '
                 f'fill="none" stroke="{TEAL_MID}" stroke-width="5" stroke-linecap="round"/>')
    P.append('</g>')


def mountains():
    ridges = [
        (SAGE_LT, 690, [(0, 730), (140, 660), (300, 740), (470, 655), (640, 745),
                        (820, 660), (1000, 745), (1180, 655), (1350, 740), (1500, 665), (1600, 725)]),
        (SAGE, 720, [(0, 780), (180, 700), (360, 785), (560, 695), (760, 790),
                     (960, 700), (1160, 790), (1360, 700), (1600, 780)]),
        (TEAL_MID, 760, [(0, 830), (220, 745), (430, 835), (660, 740), (900, 838),
                         (1130, 742), (1360, 835), (1600, 750)]),
    ]
    for color, _, pts in ridges:
        d = f"M0,{H} L" + " L".join(f"{x},{y}" for x, y in pts) + f" L{W},{H} Z"
        P.append(f'<path d="{d}" fill="{color}"/>')


def rocket(cx=800):
    # flame (layered teardrops)
    P.append(f'<path d="M{cx},545 C{cx - 58},610 {cx - 26},660 {cx - 52},715 '
             f'C{cx - 66},770 {cx - 34},805 {cx - 46},838 L{cx + 46},838 '
             f'C{cx + 34},805 {cx + 66},770 {cx + 52},715 C{cx + 26},660 {cx + 58},610 {cx},545 Z" fill="{GOLD}"/>')
    P.append(f'<path d="M{cx},575 C{cx - 34},625 {cx - 15},670 {cx - 31},720 '
             f'C{cx - 40},765 {cx - 19},800 {cx - 27},838 L{cx + 27},838 '
             f'C{cx + 19},800 {cx + 40},765 {cx + 31},720 C{cx + 15},670 {cx + 34},625 {cx},575 Z" fill="{CREAM}"/>')
    # fins
    for sx in (-1, 1):
        P.append(f'<path d="M{cx + sx * 62},420 C{cx + sx * 118},462 {cx + sx * 128},540 {cx + sx * 112},586 '
                 f'C{cx + sx * 84},566 {cx + sx * 68},522 {cx + sx * 62},478 Z" '
                 f'fill="{TEAL_DARK}" stroke="{GOLD}" stroke-width="8" stroke-linejoin="round"/>')
    # body
    P.append(f'<path d="M{cx},118 C{cx - 52},176 {cx - 68},248 {cx - 68},330 L{cx - 68},462 '
             f'C{cx - 68},520 {cx - 40},562 {cx},586 C{cx + 40},562 {cx + 68},520 {cx + 68},462 '
             f'L{cx + 68},330 C{cx + 68},248 {cx + 52},176 {cx},118 Z" '
             f'fill="{CREAM}" stroke="{GOLD}" stroke-width="10" stroke-linejoin="round"/>')
    # nose cone
    P.append(f'<path d="M{cx},124 C{cx - 46},178 {cx - 62},244 {cx - 64},318 L{cx + 64},318 '
             f'C{cx + 62},244 {cx + 46},178 {cx},124 Z" fill="{TEAL_DARK}"/>')
    # rivets
    for i, dx in enumerate((-44, -22, 0, 22, 44)):
        circle(cx + dx, 342, 6, GOLD)
    # window + porthole
    circle(cx, 408, 40, TEAL_DARK, GOLD, 10)
    circle(cx, 492, 15, TEAL_DARK, GOLD, 7)


def build():
    P.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">')
    P.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    # ---- left cluster
    trace([(0, 96), (150, 96), (215, 160), (345, 160)], GOLD, start_ring=True)
    trace([(0, 150), (110, 150), (175, 215), (300, 215)], TEAL_MID)
    trace([(0, 260), (90, 260), (140, 310)], TEAL_MID, node=False)
    trace([(0, 330), (120, 330), (180, 390), (330, 390)], GOLD)
    trace([(0, 420), (150, 420), (215, 480), (400, 480)], TEAL_MID)
    trace([(60, 0), (60, 60), (120, 120)], GOLD, node=False, start_ring=True)
    trace([(420, 60), (420, 130), (480, 190), (560, 190)], TEAL_MID)
    trace([(330, 300), (390, 300), (440, 350), (520, 350)], GOLD)
    trace([(300, 460), (300, 515)], TEAL_MID)
    chip(170, 130, 56)
    chip(80, 235, 44)
    gear(300, 330, 72, 10, SAGE, spokes=4)
    gear(252, 208, 42, 9, GOLD)
    gear(398, 250, 30, 8, TEAL_MID)
    gear(205, 302, 21, 8, GOLD)
    gear(462, 322, 17, 8, SAGE)
    propeller(300, 555, 34)
    propeller(372, 560, 34)
    propeller(444, 555, 34)
    drone(520, 140, 0.9)

    # ---- right cluster
    satellite(1150, 175)
    drone(1380, 165, 0.85)
    trace([(1600, 300), (1470, 300), (1410, 360), (1290, 360)], GOLD, start_ring=True)
    trace([(1600, 360), (1500, 360), (1440, 420), (1330, 420)], TEAL_MID)
    trace([(1600, 470), (1480, 470), (1420, 530)], TEAL_MID, node=False)
    trace([(1600, 560), (1450, 560), (1390, 620), (1240, 620)], GOLD)
    trace([(1150, 420), (1150, 480), (1090, 540), (1010, 540)], TEAL_MID)
    trace([(1050, 330), (1050, 400), (1110, 460)], GOLD, start_ring=True)
    trace([(1240, 640), (1240, 700)], TEAL_MID)
    chip(1120, 430, 52)
    chip(1470, 480, 44)
    gear(1300, 500, 58, 10, SAGE, spokes=4)
    gear(1205, 560, 32, 9, GOLD)
    gear(1282, 590, 24, 8, TEAL_MID)
    gear(1372, 570, 30, 9, GOLD)
    gear(1428, 480, 18, 8, SAGE)

    # ---- title
    P.append(f'<text x="90" y="642" font-family="Verdana, Arial, sans-serif" '
             f'font-size="40" font-weight="600" letter-spacing="10" fill="{TEXT}">'
             f'CHASING INNOVATION</text>')

    mountains()
    rocket()
    P.append('</svg>')
    return "\n".join(P)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "chasing-innovation-handcrafted.svg")
    out.write_text(build() + "\n")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
