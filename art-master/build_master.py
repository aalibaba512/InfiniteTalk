#!/usr/bin/env python3
"""CHASING INNOVATION — large-format vector print master builder.

Reconstructs the reference artwork (flat technology illustration) as a true
vector SVG master sized 17 ft x 8.6 ft (14688 pt x 7430.4 pt, ratio 1.9767).

Coordinate system: all authoring is done in "ref units" — pixel coordinates of
the 1778 x 1000 reference sheet whose artwork occupies y in [0, 930] (below is
the print-job caption strip, NOT artwork).  Ref units map uniformly onto the
master page; horizontal bleeds (circuit traces, mountains) extend past the ref
width so they run to the true page edge.

Rendering / print pipeline (verified in this sandbox):
    python3 build_master.py            -> chasing_innovation_master.svg
    .venv-art/bin/python render_proof.py [width_px] [out.png]

Only SVG 1.1 primitives MuPDF handles are used: <path> with M/L/C/Z, <circle>,
<rect>, groups with translate/rotate transforms, flat fills/strokes.  No
gradients, filters, gradients-of-opacity, arcs-as-'A' (cubics instead).
"""

from __future__ import annotations

import math
from pathlib import Path

# --------------------------------------------------------------------------
# page geometry
# --------------------------------------------------------------------------
W_PT = 17 * 12 * 72          # 14688.0
H_PT = 8.6 * 12 * 72         # 7430.4
REF_W = 1778.0
REF_AH = 930.0               # artwork height in ref units
S = H_PT / REF_AH            # uniform scale ref->pt
OX = (W_PT - REF_W * S) / 2  # centering offset

def X(x: float) -> float: return OX + x * S
def Y(y: float) -> float: return y * S

# --------------------------------------------------------------------------
# palette (read from reference; tuned against proof renders)
# --------------------------------------------------------------------------
C = dict(
    bg      = "#F7F9FA",
    teal_d  = "#0E565C",   # rocket body / fins / dark traces
    teal_m  = "#2E7F87",   # mid teal traces
    teal_l  = "#7FA3A6",   # pale teal details
    teal_g  = "#5F8B8E",   # slate teal of the big gears
    gold    = "#D8AC4E",
    gold_d  = "#B08429",
    gold_l  = "#EACB72",
    cream   = "#F6ECD4",
    grey_l  = "#AEB6BA",
    grey_m  = "#7E8A8F",
    grey_d  = "#57646A",
    m_sage  = "#A9B49C",   # mountain back layer
    m_mid   = "#64805F",   # mountain mid layer
    m_deep  = "#2F5847",   # mountain tall peaks
    m_dark  = "#1F4636",   # mountain front band
    m_line  = "#17382C",   # mountain line detail
    text    = "#187C3F",
    sat_d   = "#1E4A3C",   # satellite panel green
)

P: list[str] = []          # svg element accumulator

def el(s: str) -> None: P.append(s)

# --------------------------------------------------------------------------
# primitive helpers (all in ref units)
# --------------------------------------------------------------------------
def poly(pts, close=False, fill=None, stroke=None, sw=0, cap="round", join="round", dash=None):
    d = "M " + " L ".join(f"{X(x):.1f} {Y(y):.1f}" for x, y in pts) + (" Z" if close else "")
    return path_d(d, fill, stroke, sw, cap, join, dash)

def path_d(d, fill=None, stroke=None, sw=0, cap="round", join="round", dash=None, opacity=None):
    at = f' d="{d}"'
    at += f' fill="{fill}"' if fill else ' fill="none"'
    if stroke:
        at += f' stroke="{stroke}" stroke-width="{sw*S:.2f}" stroke-linecap="{cap}" stroke-linejoin="{join}"'
        if dash: at += f' stroke-dasharray="{dash}"'
    if opacity is not None: at += f' opacity="{opacity}"'
    el(f"<path{at}/>")

def circle(cx, cy, r, fill=None, stroke=None, sw=0):
    at = f' cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{r*S:.1f}"'
    at += f' fill="{fill}"' if fill else ' fill="none"'
    if stroke: at += f' stroke="{stroke}" stroke-width="{sw*S:.2f}"'
    el(f"<circle{at}/>")

def rect(x, y, w, h, fill=None, stroke=None, sw=0, rx=0, rot=None, cx=None, cy=None):
    at = f' x="{X(x):.1f}" y="{Y(y):.1f}" width="{w*S:.1f}" height="{h*S:.1f}"'
    if rx: at += f' rx="{rx*S:.1f}"'
    at += f' fill="{fill}"' if fill else ' fill="none"'
    if stroke: at += f' stroke="{stroke}" stroke-width="{sw*S:.2f}"'
    if rot is not None:
        at += f' transform="rotate({rot} {X(cx if cx is not None else x+w/2):.1f} {Y(cy if cy is not None else y+h/2):.1f})"'
    el(f"<rect{at}/>")

def _arc_seg(cx, cy, r, a0, a1):
    """cubic approximation of one arc segment <=90deg, returns 'C ...' """
    th = a1 - a0
    k = 4.0 / 3.0 * math.tan(th / 4.0)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    c1x = x0 - k * r * math.sin(a0); c1y = y0 + k * r * math.cos(a0)
    c2x = x1 + k * r * math.sin(a1); c2y = y1 - k * r * math.cos(a1)
    return (f"C {X(c1x):.1f} {Y(c1y):.1f} {X(c2x):.1f} {Y(c2y):.1f} "
            f"{X(x1):.1f} {Y(y1):.1f}")

def arc_d(cx, cy, r, a0deg, a1deg):
    a0, a1 = math.radians(a0deg), math.radians(a1deg)
    n = max(1, int(abs(a1deg - a0deg) // 90) + 1)
    d = f"M {X(cx + r*math.cos(a0)):.1f} {Y(cy + r*math.sin(a0)):.1f} "
    for i in range(n):
        d += _arc_seg(cx, cy, r, a0 + (a1-a0)*i/n, a0 + (a1-a0)*(i+1)/n)
    return d

def arc(cx, cy, r, a0, a1, stroke, sw, fill=None, cap="round"):
    d = arc_d(cx, cy, r, a0, a1)
    if fill:
        d += f" L {X(cx):.1f} {Y(cy):.1f} Z"
        path_d(d, fill=fill)
    else:
        path_d(d, stroke=stroke, sw=sw, cap=cap)

# --------------------------------------------------------------------------
# component generators
# --------------------------------------------------------------------------
def gear(cx, cy, r_out, teeth, fill, r_root=None, stroke=None, sw=0,
         hole=None, hole_r=None, hub_ring=None, hub_ring_w=None, rot=0):
    r_root = r_root or r_out * 0.76
    pts = []
    for i in range(teeth):
        base = rot + i * 360.0 / teeth
        for r, da in ((r_root, 0.06), (r_out, 0.20), (r_out, 0.44), (r_root, 0.58)):
            a = math.radians(base + da * 360.0 / teeth)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    poly(pts, close=True, fill=fill, stroke=stroke, sw=sw)
    if hub_ring:
        circle(cx, cy, hub_ring, fill="none", stroke=hub_ring, sw=0)  # placeholder
    if hole:
        circle(cx, cy, hole_r or r_out * 0.34, fill=hole)

def gear_ring(cx, cy, r_out, teeth, fill, hole_fill, r_hole, r_hub, hub_fill=None):
    """gear with visible white gap ring + hub, like the big teal gears."""
    gear(cx, cy, r_out, teeth, fill)
    circle(cx, cy, r_hole, fill=hole_fill)
    circle(cx, cy, r_hub, fill=hub_fill or fill)
    circle(cx, cy, r_hub * 0.55, fill=hole_fill)

def spiral(cx, cy, r1, turns, stroke, sw, rot=0):
    n = int(turns * 48)
    pts = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(rot) + t * turns * 2 * math.pi
        r = 1.5 + (r1 - 1.5) * t
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    poly(pts, stroke=stroke, sw=sw, cap="round")

def trace(pts, color, w, start=None, end=None, ring_r=None):
    poly(pts, stroke=color, sw=w, cap="round", join="round")
    rr = ring_r or w * 1.9
    for pt, kind in ((pts[0], start), (pts[-1], end)):
        if kind == "ring":
            circle(pt[0], pt[1], rr, fill=C["bg"], stroke=color, sw=w)
        elif kind == "dot":
            circle(pt[0], pt[1], rr * 0.72, fill=color)

def key(cx, cy, ang, length, fill, head_r=10.5):
    g = []
    g.append(f'<g transform="translate({X(cx):.1f} {Y(cy):.1f}) rotate({ang})">')
    s = S
    g.append(f'<circle r="{head_r*s:.1f}" fill="{fill}"/>')
    g.append(f'<circle r="{head_r*0.42*s:.1f}" fill="{C["bg"]}"/>')
    g.append(f'<rect x="{head_r*0.7*s:.1f}" y="{-2.6*s:.1f}" width="{length*s:.1f}" height="{5.2*s:.1f}" fill="{fill}"/>')
    for tx in (0.62, 0.88):
        g.append(f'<rect x="{(head_r*0.7+length*tx)*s:.1f}" y="{2.0*s:.1f}" width="{4.6*s:.1f}" height="{7.5*s:.1f}" fill="{fill}"/>')
    g.append("</g>")
    el("".join(g))

def chip(cx, cy, s_, body, line):
    rect(cx - s_/2, cy - s_/2, s_, s_, fill=body, stroke=line, sw=1.6, rx=2)
    rect(cx - s_*0.28, cy - s_*0.28, s_*0.56, s_*0.56, fill="none", stroke=line, sw=1.4)
    for i in (-0.3, 0, 0.3):
        rect(cx - s_/2 - 4, cy + i*s_ - 1.2, 4, 2.4, fill=line)
        rect(cx + s_/2, cy + i*s_ - 1.2, 4, 2.4, fill=line)

def prop(cx, cy, r, ang, fill, blades=3, hub=None):
    g = [f'<g transform="translate({X(cx):.1f} {Y(cy):.1f}) rotate({ang})">']
    s = S
    for i in range(blades):
        a = i * 360.0 / blades
        g.append(f'<path transform="rotate({a})" fill="{fill}" d="M 0 0 '
                 f'C {7*s:.1f} {-r*0.25*s:.1f} {8*s:.1f} {-r*0.75*s:.1f} 0 {-r*s:.1f} '
                 f'C {-8*s:.1f} {-r*0.75*s:.1f} {-7*s:.1f} {-r*0.25*s:.1f} 0 0 Z"/>')
    g.append(f'<circle r="{(hub or r*0.16)*s:.1f}" fill="{fill}"/>')
    g.append("</g>")
    el("".join(g))

def prop_disc(cx, cy, w_, fill, stroke=None):
    """thin horizontal rotor lens (drones)"""
    d = (f"M {X(cx-w_/2):.1f} {Y(cy):.1f} "
         f"C {X(cx-w_/6):.1f} {Y(cy-3.2):.1f} {X(cx+w_/6):.1f} {Y(cy-3.2):.1f} {X(cx+w_/2):.1f} {Y(cy):.1f} "
         f"C {X(cx+w_/6):.1f} {Y(cy+3.2):.1f} {X(cx-w_/6):.1f} {Y(cy+3.2):.1f} {X(cx-w_/2):.1f} {Y(cy):.1f} Z")
    path_d(d, fill=fill, stroke=stroke, sw=1 if stroke else 0)

# --------------------------------------------------------------------------
# artwork sections
# --------------------------------------------------------------------------
def mountains():
    back = [(-30, 846), (60, 830), (150, 840), (255, 818), (360, 840), (470, 826),
            (575, 842), (700, 830), (830, 842), (960, 828), (1080, 842), (1200, 826),
            (1310, 842), (1420, 822), (1530, 840), (1640, 824), (1730, 840), (1810, 830)]
    mid  = [(-30, 872), (80, 846), (170, 862), (300, 836), (420, 862), (540, 846),
            (660, 866), (780, 850), (900, 868), (1020, 848), (1140, 866), (1260, 842),
            (1380, 864), (1500, 840), (1620, 864), (1720, 846), (1810, 860)]
    deep_l = [(-30, 930), (-30, 846), (40, 820), (115, 788), (170, 816), (215, 800),
              (268, 838), (330, 822), (392, 852), (470, 838), (540, 868), (620, 858),
              (700, 890), (760, 930)]
    deep_r = [(1030, 930), (1090, 884), (1170, 862), (1250, 880), (1330, 852),
              (1410, 872), (1480, 842), (1560, 786), (1620, 814), (1672, 796),
              (1730, 834), (1810, 820), (1810, 930)]
    front = [(-30, 930), (-30, 898), (90, 884), (210, 898), (330, 882), (450, 900),
             (570, 886), (690, 902), (810, 888), (930, 902), (1050, 886), (1170, 902),
             (1290, 884), (1410, 900), (1530, 886), (1650, 902), (1770, 886), (1810, 894), (1810, 930)]
    poly(back + [(1810, 930), (-30, 930)], close=True, fill=C["m_sage"])
    poly(mid + [(1810, 930), (-30, 930)], close=True, fill=C["m_mid"])
    poly(deep_l, close=True, fill=C["m_deep"])
    poly(deep_r, close=True, fill=C["m_deep"])
    poly(front, close=True, fill=C["m_dark"])
    # ridge line detail on the two tall peaks
    for pts in ([(60, 836), (115, 798), (152, 824)], [(128, 846), (168, 812)],
                [(30, 860), (72, 842)], [(1512, 806), (1560, 794), (1606, 822)],
                [(1612, 830), (1664, 804), (1706, 838)], [(1700, 848), (1748, 832)],
                [(270, 850), (300, 842)], [(1230, 856), (1260, 848)]):
        poly(pts, stroke=C["m_line"], sw=1.6)

def exhaust_and_cloud():
    # outer flame silhouette: wide wavy ribbon with side tongues
    d = (f"M {X(866):.1f} {Y(552):.1f} "
         f"C {X(856):.1f} {Y(586):.1f} {X(860):.1f} {Y(606):.1f} {X(852):.1f} {Y(630):.1f} "
         f"C {X(856):.1f} {Y(632):.1f} {X(864):.1f} {Y(622):.1f} {X(868):.1f} {Y(610):.1f} "
         f"C {X(862):.1f} {Y(664):.1f} {X(872):.1f} {Y(700):.1f} {X(862):.1f} {Y(742):.1f} "
         f"C {X(868):.1f} {Y(770):.1f} {X(866):.1f} {Y(792):.1f} {X(862):.1f} {Y(872):.1f} "
         f"L {X(924):.1f} {Y(872):.1f} "
         f"C {X(920):.1f} {Y(792):.1f} {X(918):.1f} {Y(770):.1f} {X(924):.1f} {Y(742):.1f} "
         f"C {X(914):.1f} {Y(700):.1f} {X(924):.1f} {Y(664):.1f} {X(918):.1f} {Y(610):.1f} "
         f"C {X(922):.1f} {Y(622):.1f} {X(930):.1f} {Y(632):.1f} {X(934):.1f} {Y(630):.1f} "
         f"C {X(926):.1f} {Y(606):.1f} {X(930):.1f} {Y(586):.1f} {X(920):.1f} {Y(552):.1f} Z")
    path_d(d, fill=C["gold"])
    # cream core
    d = (f"M {X(878):.1f} {Y(556):.1f} C {X(872):.1f} {Y(620):.1f} {X(882):.1f} {Y(680):.1f} {X(874):.1f} {Y(868):.1f} "
         f"L {X(912):.1f} {Y(868):.1f} C {X(904):.1f} {Y(680):.1f} {X(914):.1f} {Y(620):.1f} {X(908):.1f} {Y(556):.1f} Z")
    path_d(d, fill=C["cream"])
    # flame edge lines
    for xs in ((862, 870), (916, 924)):
        poly([(xs[0], 566), (xs[1]-4, 616), (xs[0]+2, 664), (xs[1]-2, 716), (xs[0]+4, 770), (xs[1]-4, 850)],
             stroke=C["gold_d"], sw=1.6)
    # scalloped smoke cloud: stacked scallop tiers, gold -> light gold -> cream
    def scallops(cy, r, x0, x1, fill):
        d = f"M {X(x0):.1f} {Y(cy):.1f} "
        x = x0
        while x < x1 - 1:
            w = min(r * 2, x1 - x)
            d += (f"C {X(x+w*0.25):.1f} {Y(cy-r*1.35):.1f} {X(x+w*0.75):.1f} {Y(cy-r*1.35):.1f} "
                  f"{X(x+w):.1f} {Y(cy):.1f} ")
            x += w
        d += f"L {X(x1):.1f} {Y(936):.1f} L {X(x0):.1f} {Y(936):.1f} Z"
        path_d(d, fill=fill)
    scallops(858, 38, 648, 1140, C["gold"])
    scallops(878, 33, 682, 1106, C["gold_l"])
    scallops(898, 29, 714, 1074, C["cream"])
    for (lx, ly, lr) in ((664, 884, 26), (676, 914, 22), (1124, 884, 26), (1112, 914, 22)):
        circle(lx, ly, lr, fill=C["gold"])
    for (lx, ly, lr) in ((700, 906, 18), (1088, 906, 18)):
        circle(lx, ly, lr, fill=C["cream"])
    # gold arc details over the tiers
    for (ax, ay, ar) in ((742, 872, 24), (818, 866, 28), (894, 862, 30), (970, 866, 28),
                         (1046, 872, 24), (780, 892, 24), (856, 888, 26), (932, 888, 26),
                         (1008, 892, 24), (818, 912, 22), (894, 910, 24), (970, 912, 22)):
        arc(ax, ay, ar, 200, 340, C["gold_d"], 1.6)

def rocket():
    # fins first (behind body)
    fl = (f"M {X(836):.1f} {Y(430):.1f} C {X(786):.1f} {Y(462):.1f} {X(764):.1f} {Y(516):.1f} {X(762):.1f} {Y(600):.1f} "
          f"C {X(788):.1f} {Y(572):.1f} {X(812):.1f} {Y(554):.1f} {X(838):.1f} {Y(546):.1f} Z")
    path_d(fl, fill=C["teal_d"])
    fr = (f"M {X(950):.1f} {Y(430):.1f} C {X(1000):.1f} {Y(462):.1f} {X(1022):.1f} {Y(516):.1f} {X(1024):.1f} {Y(600):.1f} "
          f"C {X(998):.1f} {Y(572):.1f} {X(974):.1f} {Y(554):.1f} {X(948):.1f} {Y(546):.1f} Z")
    path_d(fr, fill=C["teal_d"])
    # body
    d = (f"M {X(893):.1f} {Y(163):.1f} C {X(930):.1f} {Y(206):.1f} {X(962):.1f} {Y(300):.1f} {X(962):.1f} {Y(402):.1f} "
         f"C {X(962):.1f} {Y(472):.1f} {X(950):.1f} {Y(522):.1f} {X(934):.1f} {Y(550):.1f} "
         f"L {X(852):.1f} {Y(550):.1f} C {X(836):.1f} {Y(522):.1f} {X(824):.1f} {Y(472):.1f} {X(824):.1f} {Y(402):.1f} "
         f"C {X(824):.1f} {Y(300):.1f} {X(856):.1f} {Y(206):.1f} {X(893):.1f} {Y(163):.1f} Z")
    path_d(d, fill=C["teal_d"])
    # inner white panel w/ gold trim
    d = (f"M {X(893):.1f} {Y(200):.1f} C {X(922):.1f} {Y(238):.1f} {X(947):.1f} {Y(316):.1f} {X(947):.1f} {Y(404):.1f} "
         f"C {X(947):.1f} {Y(466):.1f} {X(938):.1f} {Y(512):.1f} {X(925):.1f} {Y(536):.1f} "
         f"L {X(861):.1f} {Y(536):.1f} C {X(848):.1f} {Y(512):.1f} {X(839):.1f} {Y(466):.1f} {X(839):.1f} {Y(404):.1f} "
         f"C {X(839):.1f} {Y(316):.1f} {X(864):.1f} {Y(238):.1f} {X(893):.1f} {Y(200):.1f} Z")
    path_d(d, fill="#FFFFFF", stroke=C["gold"], sw=2.6)
    # window
    circle(893, 318, 40, fill="#FFFFFF", stroke=C["teal_d"], sw=13)
    # gears inside
    gear(872, 398, 30, 8, C["teal_m"], hole="#FFFFFF", hole_r=10)
    rect(862, 388, 20, 20, fill=C["grey_d"], rx=2)
    for i in (-5, 0, 5):
        rect(858, 396+i, 4, 2.4, fill=C["grey_d"])
        rect(882, 396+i, 4, 2.4, fill=C["grey_d"])
    gear(923, 383, 20, 8, C["gold"], stroke=C["gold_d"], sw=1.4, hole="#FFFFFF", hole_r=6.5)
    # inner traces
    trace([(868, 432), (868, 468), (858, 478)], C["teal_m"], 2.2, end="dot")
    trace([(893, 436), (893, 502)], C["teal_m"], 2.2, end="dot")
    trace([(916, 432), (926, 458)], C["teal_m"], 2.2, end="ring")
    # centre fin
    d = (f"M {X(884):.1f} {Y(540):.1f} L {X(884):.1f} {Y(596):.1f} "
         f"C {X(888):.1f} {Y(606):.1f} {X(898):.1f} {Y(606):.1f} {X(902):.1f} {Y(596):.1f} "
         f"L {X(902):.1f} {Y(540):.1f} Z")
    path_d(d, fill=C["teal_d"])

# --- left cluster ----------------------------------------------------------
def left_cluster():
    # spiral top-left with teal outer arc
    spiral(127, 214, 30, 2.2, C["gold"], 5.5, rot=200)
    arc(127, 214, 34, 160, 380, C["teal_m"], 4.5)
    # entering traces
    trace([(-20, 262), (140, 262), (176, 226), (296, 226)], C["teal_m"], 3.2, end="ring")
    trace([(-20, 288), (150, 288), (188, 250), (330, 250), (352, 272)], C["teal_d"], 3.2, end="dot")
    trace([(-20, 318), (120, 318)], C["teal_d"], 3.2, end="dot")
    trace([(-20, 348), (96, 348)], C["grey_m"], 3.0, end="dot")
    trace([(150, 300), (208, 300), (238, 330)], C["teal_m"], 2.6, end="ring")
    # gold line sweeping to lower right
    trace([(-20, 412), (180, 412), (352, 566)], C["gold"], 3.0)
    # chip + doodads
    chip(240, 285, 30, C["grey_l"], C["grey_d"])
    poly([(172, 322), (196, 322), (196, 332), (208, 332), (208, 344), (172, 344)], stroke=C["teal_m"], sw=3.0)
    circle(335, 468, 12, fill=C["gold"], stroke=C["gold_d"], sw=1.6)
    circle(335, 468, 5, fill=C["teal_d"])
    circle(398, 524, 7, fill="none", stroke=C["teal_d"], sw=3.0)
    # gears
    gear(295, 345, 32, 10, C["gold"], stroke=C["gold_d"], sw=1.8, hole="#FFFFFF", hole_r=11)
    gear_ring(390, 385, 56, 12, C["teal_g"], "#FFFFFF", 34, 24)
    # propellers + small gears top right of cluster
    prop(440, 214, 34, 15, C["grey_m"], 3)
    prop(516, 206, 40, 40, C["grey_d"], 4)
    prop(592, 240, 36, 80, C["grey_m"], 3)
    gear(556, 214, 12, 8, C["grey_m"], hole="#FFFFFF", hole_r=4)
    gear(585, 292, 22, 9, C["grey_m"], stroke=C["grey_d"], sw=1.4, hole="#FFFFFF", hole_r=7.5)
    gear(560, 330, 13, 8, C["teal_m"], hole="#FFFFFF", hole_r=4.5)
    gear(512, 385, 17, 8, C["gold"], stroke=C["gold_d"], sw=1.4, hole="#FFFFFF", hole_r=5.5)
    key(612, 322, 90, 40, C["grey_m"])
    key(447, 492, 45, 44, C["gold"])
    # traces from gear to drone
    trace([(438, 428), (470, 460), (470, 500)], C["teal_m"], 2.8, end="dot")
    trace([(452, 420), (520, 488), (520, 528), (552, 560)], C["teal_d"], 2.8)
    trace([(470, 430), (560, 520), (560, 556)], C["teal_m"], 2.4)
    drone(552, 600)

def drone(cx, cy):
    prop_disc(cx - 108, cy - 34, 84, C["grey_l"], C["grey_d"])
    prop_disc(cx + 108, cy - 34, 84, C["grey_l"], C["grey_d"])
    rect(cx - 116, cy - 30, 16, 12, fill=C["grey_m"], rx=3)
    rect(cx + 100, cy - 30, 16, 12, fill=C["grey_m"], rx=3)
    poly([(cx - 100, cy - 22), (cx - 52, cy - 6)], stroke=C["grey_d"], sw=5)
    poly([(cx + 100, cy - 22), (cx + 52, cy - 6)], stroke=C["grey_d"], sw=5)
    rect(cx - 58, cy - 10, 116, 18, fill=C["grey_m"], stroke=C["grey_d"], sw=2, rx=7)
    for i in range(5):
        circle(cx - 30 + i * 15, cy - 1, 2.4, fill=C["grey_d"])
    poly([(cx - 40, cy + 8), (cx - 52, cy + 48), (cx - 44, cy + 52)], stroke=C["grey_d"], sw=5)
    poly([(cx + 40, cy + 8), (cx + 52, cy + 48), (cx + 44, cy + 52)], stroke=C["grey_d"], sw=5)
    circle(cx, cy + 34, 13, fill=C["grey_m"], stroke=C["grey_d"], sw=2.4)
    circle(cx, cy + 34, 5.5, fill=C["grey_d"])

# --- right cluster ---------------------------------------------------------
def right_cluster():
    satellite(1332, 208, -33)
    # radio arcs + spiral
    arc(1252, 306, 12, 20, 130, C["teal_d"], 3.4)
    arc(1252, 306, 21, 20, 130, C["teal_d"], 3.4)
    arc(1252, 306, 30, 20, 130, C["teal_d"], 3.4)
    spiral(1268, 348, 30, 2.2, C["gold"], 5.5, rot=20)
    # long traces
    trace([(1090, 366), (1240, 366)], C["gold"], 3.0, start="dot")
    trace([(1082, 402), (1300, 402), (1338, 364), (1500, 364), (1530, 394), (1700, 394)], C["teal_m"], 3.2, start="ring", end="ring")
    trace([(1078, 440), (1360, 440), (1392, 408), (1560, 408), (1592, 440), (1778, 440)], C["teal_d"], 3.2, start="ring")
    trace([(1078, 492), (1290, 492)], C["teal_d"], 3.6, start="ring", end="dot")
    trace([(1082, 538), (1330, 538), (1368, 576), (1520, 576)], C["teal_m"], 3.2, start="ring", end="dot")
    trace([(1086, 572), (1250, 572), (1420, 700), (1520, 700)], C["gold"], 3.0, start="ring")
    trace([(1600, 470), (1660, 470), (1690, 440), (1778, 440)], C["teal_m"], 2.6)
    # chip + doodad
    chip(1390, 420, 30, C["grey_l"], C["grey_d"])
    poly([(1282, 458), (1306, 458), (1306, 468), (1318, 468), (1318, 480), (1282, 480)], stroke=C["teal_m"], sw=3.0)
    circle(1505, 613, 12, fill=C["gold"], stroke=C["gold_d"], sw=1.6)
    circle(1505, 613, 5, fill=C["teal_d"])
    circle(1585, 678, 7, fill="none", stroke=C["teal_d"], sw=3.0)
    # gears
    gear(1455, 480, 34, 10, C["gold"], stroke=C["gold_d"], sw=1.8, hole="#FFFFFF", hole_r=11.5)
    gear_ring(1560, 520, 60, 12, C["teal_g"], "#FFFFFF", 37, 26)
    gear(1737, 460, 30, 10, C["grey_m"], stroke=C["grey_d"], sw=1.6, hole="#FFFFFF", hole_r=10)
    gear(1703, 520, 18, 8, C["gold"], stroke=C["gold_d"], sw=1.4, hole="#FFFFFF", hole_r=6)
    key(1637, 636, 45, 46, C["gold"])
    key(1652, 640, 35, 40, C["grey_m"])
    trace([(1688, 690), (1740, 690), (1778, 728)], C["teal_m"], 3.0)
    trace([(1718, 742), (1778, 788)], C["teal_d"], 3.0)

def satellite(cx, cy, ang):
    g = [f'<g transform="translate({X(cx):.1f} {Y(cy):.1f}) rotate({ang})">']
    s = S
    # solar wings with struts
    for sgn in (-1, 1):
        x0 = sgn * 34
        wx = min(x0, x0 + sgn * 74)
        g.append(f'<line x1="{sgn*18*s:.1f}" y1="0" x2="{x0*s:.1f}" y2="0" stroke="{C["grey_d"]}" stroke-width="{3*s:.1f}"/>')
        g.append(f'<rect x="{wx*s:.1f}" y="{-60*s:.1f}" width="{74*s:.1f}" height="{120*s:.1f}" fill="{C["sat_d"]}" stroke="{C["grey_d"]}" stroke-width="{2*s:.1f}"/>')
        for i in range(1, 3):
            g.append(f'<line x1="{(x0+sgn*74*i/3)*s:.1f}" y1="{-60*s:.1f}" x2="{(x0+sgn*74*i/3)*s:.1f}" y2="{60*s:.1f}" stroke="{C["teal_l"]}" stroke-width="{1.6*s:.1f}"/>')
        for j in range(1, 4):
            g.append(f'<line x1="{wx*s:.1f}" y1="{(-60+120*j/4)*s:.1f}" x2="{(x0+sgn*74)*s:.1f}" y2="{(-60+120*j/4)*s:.1f}" stroke="{C["teal_l"]}" stroke-width="{1.6*s:.1f}"/>')
    # body
    g.append(f'<rect x="{-18*s:.1f}" y="{-60*s:.1f}" width="{36*s:.1f}" height="{120*s:.1f}" fill="{C["sat_d"]}" stroke="{C["grey_d"]}" stroke-width="{2*s:.1f}"/>')
    g.append(f'<rect x="{-11*s:.1f}" y="{-34*s:.1f}" width="{22*s:.1f}" height="{40*s:.1f}" fill="{C["gold"]}" opacity="0.85"/>')
    g.append("</g>")
    el("".join(g))
    # drone props flanking satellite (page level)
    prop_disc(cx - 104, cy + 14, 110, C["grey_l"], C["grey_d"])
    prop_disc(cx + 116, cy + 18, 110, C["grey_l"], C["grey_d"])
    rect(cx - 112, cy + 18, 16, 12, fill=C["grey_m"], rx=3)
    rect(cx + 108, cy + 22, 16, 12, fill=C["grey_m"], rx=3)
    poly([(cx - 96, cy + 26), (cx - 30, cy + 40)], stroke=C["grey_d"], sw=5)
    poly([(cx + 108, cy + 30), (cx + 40, cy + 44)], stroke=C["grey_d"], sw=5)

# --- title text -------------------------------------------------------------
GLYPHS = {
    "C": [(78, 16), (60, 0), (20, 0), (0, 20), (0, 80), (20, 100), (60, 100), (78, 84)],
    "H": [(0, 0), (0, 100), None, (80, 0), (80, 100), None, (0, 50), (80, 50)],
    "A": [(0, 100), (40, 0), (80, 100), None, (16, 62), (64, 62)],
    "S": [(80, 14), (64, 0), (16, 0), (0, 16), (0, 38), (16, 52), (64, 52), (80, 66), (80, 84), (64, 100), (16, 100), (0, 86)],
    "I": [(10, 0), (10, 100)],
    "N": [(0, 100), (0, 0), None, (0, 0), (80, 100), None, (80, 100), (80, 0)],
    "G": [(80, 16), (62, 0), (20, 0), (0, 20), (0, 80), (20, 100), (62, 100), (80, 80), (80, 55), (48, 55)],
    "O": [(20, 0), (60, 0), (80, 20), (80, 80), (60, 100), (20, 100), (0, 80), (0, 20), (20, 0)],
    "V": [(0, 0), (40, 100), (80, 0)],
    "T": [(0, 0), (80, 0), None, (40, 0), (40, 100)],
}
GLYPH_W = {"C": 78, "H": 80, "A": 80, "S": 80, "I": 20, "N": 80, "G": 80, "O": 80, "V": 80, "T": 80}

def title_text():
    text = "CHASING INNOVATION"
    tracking = 34
    space_w = 60
    units = 0
    for ch in text:
        units += (GLYPH_W[ch] if ch != " " else space_w) + tracking
    units -= tracking
    # target: spans x 140..722 in ref units, cap height 30
    x0, x1 = 140.0, 722.0
    cap = 30.0
    k = (x1 - x0) / units
    sw = 14.0 * k
    px = x0
    y0 = 737.0 - cap
    for ch in text:
        if ch != " ":
            for seg in _glyph_segs(GLYPHS[ch]):
                pts = [(px + a * k, y0 + b * k) for a, b in seg]
                poly(pts, stroke=C["text"], sw=sw, cap="butt", join="miter")
        px += ((GLYPH_W[ch] if ch != " " else space_w) + tracking) * k

def _glyph_segs(g):
    seg, cur = [], []
    for p in g:
        if p is None:
            seg.append(cur); cur = []
        else:
            cur.append(p)
    if cur: seg.append(cur)
    return seg

# --------------------------------------------------------------------------
def build() -> str:
    el(f'<rect x="0" y="0" width="{W_PT}" height="{H_PT}" fill="{C["bg"]}"/>')
    mountains()
    exhaust_and_cloud()
    left_cluster()
    right_cluster()
    rocket()
    title_text()
    body = "\n".join(P)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_PT}pt" height="{H_PT}pt" '
            f'viewBox="0 0 {W_PT} {H_PT}">\n{body}\n</svg>\n')

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "chasing_innovation_master.svg"
    out.write_text(build(), encoding="utf-8")
    print("wrote", out, out.stat().st_size, "bytes")
