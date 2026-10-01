#!/usr/bin/env python3
"""
Builds the TEFOS Quiz pitch deck.

Design system mirrors the working prototype: deep teal, gold accent, off-white
canvas, large type. Deliberately not a default Office template.
"""
import os
import struct
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ----------------------------------------------------------------- palette
INK      = RGBColor(0x16, 0x23, 0x2B)
DEEP     = RGBColor(0x0F, 0x3D, 0x4A)
TEAL     = RGBColor(0x0B, 0x6B, 0x7D)
TEAL_LT  = RGBColor(0x7F, 0xD3, 0xE0)
TEAL_PALE= RGBColor(0xE7, 0xF3, 0xF5)
GOLD     = RGBColor(0xD9, 0xA4, 0x41)
GOLD_LT  = RGBColor(0xFF, 0xD9, 0x8A)
GREEN    = RGBColor(0x1A, 0x6B, 0x3C)
GREEN_BG = RGBColor(0xEA, 0xF7, 0xEF)
GREEN_LT = RGBColor(0x3A, 0xA7, 0x6D)
AMBER    = RGBColor(0x8A, 0x5A, 0x10)
AMBER_BG = RGBColor(0xFF, 0xF8, 0xE6)
GREY     = RGBColor(0x5C, 0x6B, 0x75)
GREY_LT  = RGBColor(0x9A, 0xA7, 0xB0)
CANVAS   = RGBColor(0xF6, 0xF7, 0xF8)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
RED      = RGBColor(0xB0, 0x35, 0x35)
RED_BG   = RGBColor(0xFC, 0xEC, 0xEC)

W, H = 13.333, 7.5
M = 0.75                      # margin
FONT = "Calibri"

prs = Presentation()
prs.slide_width  = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]

_n = [0]

# ----------------------------------------------------------------- helpers
def slide(dark=False, count=True):
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = DEEP if dark else CANVAS
    bg.line.fill.background(); bg.shadow.inherit = False
    if count:
        _n[0] += 1
        t = s.shapes.add_textbox(Inches(W-M-1.6), Inches(H-0.48), Inches(1.6), Inches(0.3))
        p = t.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.RIGHT
        r = p.add_run(); r.text = f"{_n[0]:02d}"
        r.font.size = Pt(10); r.font.color.rgb = TEAL_LT if dark else GREY_LT
        r.font.name = FONT
    return s

def box(s, x, y, w, h, fill=None, line=None, radius=0.06, lw=1.0):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    try: sh.adjustments[0] = radius
    except Exception: pass
    return sh

def rect(s, x, y, w, h, fill):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                            Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    sh.line.fill.background(); sh.shadow.inherit = False
    return sh

def text(s, x, y, w, h, runs, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT,
         space=6, anchor=MSO_ANCHOR.TOP, line_spacing=1.0, font=FONT):
    """runs: str, or list of paragraphs. Each paragraph is str or list of
    (text, {opts}) tuples for inline styling."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        p.line_spacing = line_spacing
        chunks = para if isinstance(para, list) else [(para, {})]
        for txt, o in chunks:
            r = p.add_run(); r.text = txt
            f = r.font
            f.name = o.get("font", font)
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color)
    return tb

def eyebrow(s, txt, y=0.52, x=M, color=TEAL):
    text(s, x, y, 8, 0.3, [[(txt.upper(), {"size": 11, "bold": True, "color": color})]])

def head(s, title, sub=None, y=0.88, color=INK, subcolor=GREY, w=11.0):
    text(s, M, y, w, 0.8, [[(title, {"size": 34, "bold": True, "color": color})]])
    if sub:
        text(s, M, y + 0.68, w, 0.6,
             [[(sub, {"size": 15, "color": subcolor})]])

def brandbar(s, dark=False):
    rect(s, 0, 0, W, 0.14, TEAL if not dark else GOLD)
    text(s, M, 0.2, 6, 0.28,
         [[("TEFOS ", {"size": 10, "bold": True, "color": TEAL_LT if dark else TEAL}),
           ("QUIZ", {"size": 10, "bold": True, "color": GREY_LT if dark else GREY_LT})]])

def cardlist(s, x, y, w, items, gap=0.16, fill=WHITE, accent=TEAL, h=0.72):
    """items: list of (title, body)"""
    for i, (t, b) in enumerate(items):
        yy = y + i * (h + gap)
        box(s, x, yy, w, h, fill=fill)
        rect(s, x, yy, 0.055, h, accent)
        text(s, x + 0.26, yy + 0.12, w - 0.5, 0.26,
             [[(t, {"size": 14, "bold": True, "color": INK})]])
        text(s, x + 0.26, yy + 0.38, w - 0.5, 0.3,
             [[(b, {"size": 11.5, "color": GREY})]])

def statrow(s, y, stats, h=1.05):
    n = len(stats)
    gap = 0.2
    w = (W - 2*M - gap*(n-1)) / n
    for i, (big, small, col) in enumerate(stats):
        x = M + i*(w+gap)
        box(s, x, y, w, h, fill=WHITE)
        rect(s, x, y, w, 0.05, col)
        text(s, x, y+0.2, w, 0.45, [[(big, {"size": 26, "bold": True, "color": col})]],
             align=PP_ALIGN.CENTER)
        text(s, x+0.1, y+0.68, w-0.2, 0.3, [[(small, {"size": 10.5, "color": GREY})]],
             align=PP_ALIGN.CENTER)

def footer(s, txt, dark=False):
    text(s, M, H-0.88, 10.5, 0.3,
         [[(txt, {"size": 10, "color": GREY_LT if not dark else TEAL_LT})]])

def png_size(path):
    """Read width/height straight from the PNG header - no PIL dependency."""
    with open(path, "rb") as f:
        d = f.read(26)
    w, h = struct.unpack(">II", d[16:24])
    return w, h

def fit_picture(s, path, bx, by, bw, bh, top=True):
    """Scale a picture to fit inside a box, preserving aspect ratio, and centre
    it horizontally. Returns the (width, height) actually used, in inches."""
    pw, ph = png_size(path)
    ar = pw / ph
    w = bw
    h = w / ar
    if h > bh:
        h = bh
        w = h * ar
    x = bx + (bw - w) / 2
    y = by if top else by + (bh - h) / 2
    s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))
    return w, h

def table(s, x, y, w, rows, colw, hdr=True, rh=0.42, fsize=12):
    nr, nc = len(rows), len(rows[0])
    shp = s.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(rh*nr))
    t = shp.table
    t.first_row = False; t.horz_banding = False
    for j, cw in enumerate(colw):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        t.rows[i].height = Inches(rh)
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            c.margin_left = Inches(0.12); c.margin_right = Inches(0.08)
            c.margin_top = Inches(0.04); c.margin_bottom = Inches(0.04)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            if hdr and i == 0:
                c.fill.fore_color.rgb = DEEP
            else:
                c.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xEF, 0xF3, 0xF4)
            p = c.text_frame.paragraphs[0]
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(fsize)
            r.font.name = FONT
            r.font.bold = (hdr and i == 0)
            r.font.color.rgb = WHITE if (hdr and i == 0) else INK
    return t

HERE = os.path.dirname(os.path.abspath(__file__))
MOCK = os.path.join(HERE, "mockups")

# ================================================================ 01 TITLE
s = slide(dark=True, count=False)
rect(s, 0, 0, 0.18, H, GOLD)
text(s, 1.25, 1.35, 10, 0.4,
     [[("TELECOM FOUNDATION EDUCATION SYSTEM", {"size": 12, "bold": True, "color": GOLD_LT})]])
text(s, 1.25, 1.95, 10.5, 2.2,
     [[("The notebook\nthat teaches back.", {"size": 52, "bold": True, "color": WHITE})]],
     space=0, line_spacing=0.95)
rect(s, 1.25, 4.3, 1.5, 0.045, TEAL_LT)
text(s, 1.25, 4.62, 9.5, 1.0,
     [[("A QR code on every subject notebook turns a finished chapter into a quiz, "
        "a rank, and a bursary \u2014 across all 16 schools.",
        {"size": 17, "color": TEAL_LT})]], line_spacing=1.25)
text(s, 1.25, 6.25, 9, 0.4,
     [[("A proposal  \u00b7  Chapter quizzes \u00b7  Merit bursaries \u00b7  Inter-school championship",
        {"size": 11, "color": GREY_LT})]])

# ================================================================ 02 ONE LINE
s = slide(dark=True, count=False)
text(s, 1.4, 1.5, 10.5, 0.4,
     [[("THE IDEA", {"size": 12, "bold": True, "color": GOLD_LT})]])
text(s, 1.4, 2.1, 10.5, 2.4,
     [[("A student finishes Chapter 1. They scan the book they are already holding. "
        "They answer four questions.\nThey earn points toward next month's bursary.",
        {"size": 30, "bold": True, "color": WHITE})]], line_spacing=1.2)
rect(s, 1.4, 4.9, 1.5, 0.045, TEAL_LT)
text(s, 1.4, 5.2, 9.5, 0.9,
     [[("No app. No signup. No form. No behaviour change \u2014 which is precisely why it will work.",
        {"size": 15, "color": TEAL_LT})]], line_spacing=1.2)

# ================================================================ 03 INSIGHT
s = slide()
brandbar(s); eyebrow(s, "The insight")
head(s, "The QR code is already in the book",
     "This is the only marketing surface a school owns that the student touches voluntarily, every day.")
cardlist(s, M, 2.3, 6.4, [
    ("It meets the student at peak attention",
     "They have just finished the chapter. The book is open. The page is right there."),
    ("It requires zero new behaviour",
     "No app to download, no code to memorise, no website to visit, no reminder to send."),
    ("It travels home and gets photographed",
     "It sits open on a desk where visitors see it, and ends up in photos, on desks, in parents' houses."),
], h=0.9)
box(s, 7.5, 2.3, 5.1, 3.0, fill=DEEP)
text(s, 7.85, 2.62, 4.4, 2.4,
     [[("Every other school\nchannel is a push.", {"size": 21, "bold": True, "color": WHITE})],
      [("Newsletters get ignored.\nFlyers get binned.\nApps get deleted.", {"size": 14, "color": TEAL_LT})],
      [("This one is a pull.", {"size": 15, "bold": True, "color": GOLD_LT})]],
     space=12, line_spacing=1.15)
footer(s, "Compare: a school newsletter competes with everything. A QR in a textbook competes with nothing.")

# ================================================================ 04 JOURNEY
s = slide()
brandbar(s); eyebrow(s, "The student journey")
head(s, "Five steps. About ninety seconds.")
steps = [
    ("01", "Scan", "The QR on the cover of\nany subject notebook."),
    ("02", "Enter code", "Six characters printed\ninside the front cover."),
    ("03", "Pick chapter", "The one they just\nfinished. Tap Go."),
    ("04", "Answer", "Five questions,\nmostly about their own class."),
    ("05", "Rank up", "Points, a rank tier,\nand a place on the board."),
]
gap = 0.22; cw = (W - 2*M - gap*4) / 5
for i, (num, t, b) in enumerate(steps):
    x = M + i*(cw+gap)
    box(s, x, 2.45, cw, 2.6, fill=WHITE)
    rect(s, x, 2.45, cw, 0.05, TEAL)
    text(s, x+0.25, 2.72, cw-0.5, 0.5,
         [[(num, {"size": 26, "bold": True, "color": TEAL_LT})]])
    text(s, x+0.25, 3.3, cw-0.5, 0.35,
         [[(t, {"size": 15, "bold": True, "color": INK})]])
    text(s, x+0.25, 3.72, cw-0.5, 1.0,
         [[(b, {"size": 11, "color": GREY})]], line_spacing=1.2)
    if i < 4:
        text(s, x+cw+0.02, 3.5, gap, 0.3,
             [[("\u203a", {"size": 20, "color": GREY_LT})]], align=PP_ALIGN.CENTER)
box(s, M, 5.45, W-2*M, 0.85, fill=TEAL_PALE)
text(s, M+0.3, 5.68, W-2*M-0.6, 0.5,
     [[("There is no step six. ", {"size": 14, "bold": True, "color": TEAL}),
       ("That is the entire design. Everything in this proposal exists to keep students at step five.",
        {"size": 14, "color": INK})]])

# ================================================================ 05 ENGINE
s = slide()
brandbar(s); eyebrow(s, "The participation engine")
head(s, "Five non-negotiable rules",
     "Break any one of these and the programme dies quietly within a term.")
rules = [
    ("1", "Points are never negative", RED,
     "A student who tries and gets it wrong must never end up worse off than one who never scanned."),
    ("2", "Participation earns the first rank", TEAL,
     "A student who takes part always has an identity, even at zero percent."),
    ("3", "Only a first attempt moves the board", TEAL,
     "Retries pay a little, so nobody is locked out \u2014 but nobody can farm the board."),
    ("4", "Show growth, not distance", TEAL,
     "\u201cYou gained 180 points\u201d, not \u201cyou are 2,400 short\u201d, unless the gap is genuinely reachable."),
    ("5", "Never publish only the top", TEAL,
     "Champions, most improved, and participation rate. Always all three."),
]
y = 2.3
for num, t, col, b in rules:
    box(s, M, y, W-2*M, 0.74, fill=WHITE)
    box(s, M+0.16, y+0.16, 0.42, 0.42, fill=col, radius=0.3)
    text(s, M+0.16, y+0.22, 0.42, 0.3, [[(num, {"size": 14, "bold": True, "color": WHITE})]],
         align=PP_ALIGN.CENTER)
    text(s, M+0.78, y+0.13, 3.3, 0.3, [[(t, {"size": 14, "bold": True, "color": INK})]])
    text(s, M+4.2, y+0.15, W-2*M-4.5, 0.5, [[(b, {"size": 12, "color": GREY})]])
    y += 0.86

# ================================================================ 06 POINTS
s = slide()
brandbar(s); eyebrow(s, "The one number that matters most")
head(s, "Punishing a wrong answer kills participation",
     "The arithmetic below is the single most important line in this proposal.")
box(s, M, 2.35, 5.8, 2.9, fill=RED_BG)
text(s, M+0.32, 2.6, 5.2, 0.4,
     [[("AS ORIGINALLY SPECIFIED", {"size": 11, "bold": True, "color": RED})]])
text(s, M+0.32, 3.0, 5.2, 0.4,
     [[("+10 correct  \u00b7  \u22125 wrong", {"size": 22, "bold": True, "color": INK})]])
for lbl, val, col in [("All 10 right", "+100", GREEN),
                      ("Half right", "+25", AMBER),
                      ("Three right", "\u22125", RED),
                      ("All wrong", "\u221250", RED),
                      ("Never scanned", "0", GREY)]:
    pass
y = 3.55
for lbl, val, col in [("5 of 5 right", "+50", GREEN), ("3 of 5 right", "+5", AMBER),
                      ("2 of 5 right", "\u22125", RED), ("All wrong", "\u221225", RED),
                      ("Never scanned", "0", GREY)]:
    text(s, M+0.32, y, 3.0, 0.3, [[(lbl, {"size": 12, "color": GREY})]])
    text(s, M+3.3, y, 1.0, 0.3, [[(val, {"size": 12, "bold": True, "color": col})]])
    y += 0.32
box(s, 6.9, 2.35, W-M-6.9, 2.9, fill=GREEN_BG)
text(s, 7.2, 2.6, 5.2, 0.4,
     [[("AS BUILT", {"size": 11, "bold": True, "color": GREEN})]])
text(s, 7.2, 3.0, 5.2, 0.4,
     [[("+10  \u00b7  0  \u00b7  +3 retry  \u00b7  +25 perfect", {"size": 20, "bold": True, "color": INK})]])
for i, (lbl, val, col) in enumerate([("All right", "+75", GREEN), ("Half right", "+25", GREEN),
                                     ("Two of five", "0", GREY), ("All wrong", "0", GREY),
                                     ("Never scanned", "0", GREY)]):
    yy = 3.55 + i*0.32
    text(s, 7.2, yy, 3.0, 0.3, [[(lbl, {"size": 12, "color": GREY})]])
    text(s, 10.2, yy, 1.0, 0.3, [[(val, {"size": 12, "bold": True, "color": col})]])
box(s, M, 5.55, W-2*M, 0.9, fill=DEEP)
text(s, M+0.32, 5.78, W-2*M-0.64, 0.6,
     [[("With negatives, a student who scans and does badly is worse off than one who ignores the book entirely. "
        "The programme punishes exactly the behaviour it needs most.",
        {"size": 13.5, "bold": True, "color": WHITE})]], line_spacing=1.2)

# ================================================================ 07 RANKS
s = slide()
brandbar(s); eyebrow(s, "Rank ladder")
head(s, "Spark to Galaxy", "Every student has an identity. Nobody sits in a dead zone below the first rung.")
tiers = [("✦  Spark", "Any points at all", "You took part. That is the whole entry fee.", TEAL),
         ("✨  Rising Star", "30%+", "Getting going.", TEAL),
         ("⭐  Star", "50%+", "Solid and consistent.", TEAL),
         ("🌟  Bright Star", "70%+", "Reliably strong across chapters.", GOLD),
         ("💫  Supernova", "85%+", "Outstanding.", GOLD),
         ("🌌  Galaxy", "95%+", "Exceptional.", GOLD)]
rows = [["Rank", "Points rate", "What it means"]] + [[a, b, c] for a, b, c, _ in tiers]
table(s, M, 2.3, 7.4, rows, [2.4, 1.7, 3.3], rh=0.46, fsize=12)
box(s, 8.5, 2.3, W-M-8.5, 3.0, fill=WHITE)
rect(s, 8.5, 2.3, W-M-8.5, 0.05, RED)
text(s, 8.8, 2.58, W-M-9.1, 0.35,
     [[("THE ACTIVITY FLOOR", {"size": 11, "bold": True, "color": RED})]])
text(s, 8.8, 2.95, W-M-9.1, 1.0,
     [[("Rank is points earned \u00f7 points available \u2014 never a raw average \u2014 and only appears after "
        "5 chapters attempted.", {"size": 12.5, "color": INK})]], line_spacing=1.2)
text(s, 8.8, 4.05, W-M-9.1, 1.1,
     [[("Without the floor, a student sits one easy quiz, scores 95% and quits \u2014 and out-ranks the student "
        "who showed up every week.", {"size": 12, "color": GREY})]], line_spacing=1.2)
box(s, M, 5.6, W-2*M, 0.8, fill=AMBER_BG)
text(s, M+0.3, 5.82, W-2*M-0.6, 0.5,
     [[("Bug we found and fixed: ", {"size": 13, "bold": True, "color": AMBER}),
       ("the floor originally applied to the data but not to the screen \u2014 so a one-quiz student still read "
        "\u201cGalaxy\u201d on their own result. Now the displayed tier is clamped too.", {"size": 13, "color": INK})]])

# ================================================================ 08 SCREENS
s = slide()
brandbar(s); eyebrow(s, "What the student sees")
head(s, "Three screens, ninety seconds")
imgs = [("01-home.png", "The chapter hub", "Every subject, every chapter, one tap to start."),
        ("02-result.png", "The payoff", "Points, rank tier, and how far they have come this month."),
        ("03-leaderboard.png", "The 16-school board", "All campuses together \u2014 plus the reach line, shown only when close.")]
gap = 0.3; iw = (W - 2*M - gap*2) / 3
for i, (fn, t, b) in enumerate(imgs):
    x = M + i*(iw+gap)
    p = os.path.join(MOCK, fn)
    if os.path.exists(p):
        fit_picture(s, p, x, 2.15, iw, 3.85, top=True)
    text(s, x, 6.15, iw, 0.3, [[(t, {"size": 14, "bold": True, "color": INK})]])
    text(s, x, 6.47, iw, 0.4, [[(b, {"size": 10.5, "color": GREY})]])

# ================================================================ 09 UNCHEATABLE
s = slide()
brandbar(s); eyebrow(s, "Integrity")
head(s, "A quiz nobody can google",
     "Half the questions are about things that happened in that specific classroom, that week.")
box(s, M, 2.3, 5.8, 3.3, fill=WHITE)
text(s, M+0.32, 2.58, 5.2, 0.35,
     [[("THE USUAL KIND", {"size": 11, "bold": True, "color": GREY})]])
text(s, M+0.32, 2.95, 5.2, 1.4,
     [[("\u201cA body travels 120 m in 15 s at constant speed. What is its speed?\u201d",
        {"size": 13.5, "color": INK})]], line_spacing=1.25)
text(s, M+0.32, 4.35, 5.2, 1.0,
     [[("Searchable in four seconds. Which means the prize is paid to whoever has the fastest internet "
        "connection and the most willing relatives.", {"size": 12, "color": GREY})]], line_spacing=1.2)
box(s, 6.9, 2.3, W-M-6.9, 3.3, fill=DEEP)
text(s, 7.2, 2.58, 5.2, 0.35,
     [[("THE KIND WE USE", {"size": 11, "bold": True, "color": GOLD_LT})]])
text(s, 7.2, 2.95, 5.2, 1.6,
     [[("\u201cOn the first day of the Motion unit, which classroom activity did we do?\u201d",
        {"size": 13.5, "color": WHITE})],
      [("\u201cOur lab report was due on which date?\u201d", {"size": 13.5, "color": WHITE})]],
     space=8, line_spacing=1.2)
text(s, 7.2, 4.5, 5.2, 0.9,
     [[("Nobody can search these. Only a student who was there can answer \u2014 which means we are paying for "
        "attention, not for guessing.", {"size": 12, "color": TEAL_LT})]], line_spacing=1.2)
statrow(s, 5.85, [("0", "answer keys sent to any device", TEAL),
                  ("5", "chapters before a rank shows", TEAL),
                  ("1", "first attempt per chapter, enforced", TEAL),
                  ("2.5 KB", "per quiz page, gzipped", GOLD)])

# ================================================================ 10 GROWTH
s = slide()
brandbar(s); eyebrow(s, "Motivation")
head(s, "Show growth. Show the gap only when it is reachable.",
     "The most common mistake in school gamification is telling a child exactly how far they are from winning.")
box(s, M, 2.4, 3.85, 2.6, fill=GREEN_BG)
text(s, M+0.3, 2.68, 3.3, 0.4, [[("ALWAYS", {"size": 11, "bold": True, "color": GREEN})]])
text(s, M+0.3, 3.08, 3.3, 1.5,
     [[("\u201cYou are 180 points ahead of where you were last month.\u201d",
        {"size": 16, "bold": True, "color": INK})]], line_spacing=1.2)
text(s, M+0.3, 4.45, 3.3, 0.4,
     [[("Progress against yourself. This is what sustains effort.", {"size": 11, "color": GREY})]],
     line_spacing=1.15)
box(s, 4.78, 2.4, 3.85, 2.6, fill=AMBER_BG)
text(s, 5.08, 2.68, 3.3, 0.4, [[("ONLY IF REACHABLE", {"size": 11, "bold": True, "color": AMBER})]])
text(s, 5.08, 3.08, 3.3, 1.5,
     [[("\u201c240 more points puts you on the top 10 board.\u201d",
        {"size": 16, "bold": True, "color": INK})]], line_spacing=1.2)
text(s, 5.08, 4.45, 3.3, 0.4,
     [[("A real nudge, shown only to students within striking distance.", {"size": 11, "color": GREY})]],
     line_spacing=1.15)
box(s, 8.81, 2.4, W-M-8.81, 2.6, fill=RED_BG)
text(s, 9.11, 2.68, 3.3, 0.4, [[("NEVER", {"size": 11, "bold": True, "color": RED})]])
text(s, 9.11, 3.08, 3.3, 1.5,
     [[("\u201cYou are 2,400 points short of the board.\u201d",
        {"size": 16, "bold": True, "color": INK})]], line_spacing=1.2)
text(s, 9.11, 4.45, 3.3, 0.4,
     [[("The gap is too big to close, so the rational move is to stop trying.", {"size": 11, "color": GREY})]],
     line_spacing=1.15)
box(s, M, 5.35, W-2*M, 1.0, fill=WHITE)
text(s, M+0.3, 5.58, W-2*M-0.6, 0.6,
     [[("Publish three boards, always. ", {"size": 13.5, "bold": True, "color": TEAL}),
       ("Champions \u00b7 Most improved \u00b7 Participation rate. The third one is awarded on how many students took part, "
        "not on scores \u2014 which is what gives smaller campuses a genuine way to win.",
        {"size": 13.5, "color": INK})]], line_spacing=1.2)

# ================================================================ 11 BURSARY
s = slide()
brandbar(s); eyebrow(s, "The economics")
head(s, "The school pays in tuition credit, not cash",
     "This is the trick that makes the whole programme affordable at scale.")
box(s, M, 2.35, 5.8, 2.75, fill=GREEN_BG)
text(s, M+0.32, 2.62, 5.2, 0.35, [[("WHAT IT IS", {"size": 11, "bold": True, "color": GREEN})]])
text(s, M+0.32, 3.0, 5.2, 1.9,
     [[("Merit bursary", {"size": 24, "bold": True, "color": INK})],
      [("Up to 10 bursaries a month, each worth up to 10% of one month's tuition fee, awarded on points earned.",
        {"size": 13, "color": INK})],
      [("Cost to the school: foregone revenue on a student who already pays. Budgetable, capped, predictable.",
        {"size": 12, "color": GREY})]], space=10, line_spacing=1.2)
box(s, 6.9, 2.35, W-M-6.9, 2.75, fill=RED_BG)
text(s, 7.2, 2.62, 5.2, 0.35, [[("WHAT IT MUST NOT BE CALLED", {"size": 11, "bold": True, "color": RED})]])
text(s, 7.2, 3.0, 5.2, 1.9,
     [[("\u201cStudents earn their own fee.\u201d", {"size": 21, "bold": True, "color": INK})],
      [("Identical budget. But it replaces a student election with a leaderboard, invites fee-regulation "
        "scrutiny, and reads badly in a newspaper.", {"size": 12.5, "color": INK})],
      [("Same money, completely different posture.", {"size": 12, "color": GREY})]], space=10, line_spacing=1.2)
box(s, M, 5.35, W-2*M, 1.0, fill=AMBER_BG)
text(s, M+0.32, 5.56, W-2*M-0.64, 0.7,
     [[("The honest caveat: ", {"size": 13, "bold": True, "color": AMBER}),
       ("a bursary helps a wealthy family more than a poor one, because a rich family can absorb the fee. "
        "Keep a small, separately-funded need-based component \u2014 and let sponsors underwrite that, "
        "because it is the strongest education-access outcome report available.",
        {"size": 13, "color": INK})]], line_spacing=1.2)

# ================================================================ 12 CADENCE
s = slide()
brandbar(s); eyebrow(s, "Rhythm")
head(s, "Three cadences, three different jobs",
     "A yearly reward attached to a daily habit is how engagement dies around week six.")
cols = [("WEEKLY", "Star of the Week", TEAL,
         "Recognition only. House points, a name on the school board, and nothing else. Theatre, and that is fine \u2014 "
         "as long as nobody expects cash."),
        ("MONTHLY", "The merit bursary", GOLD,
         "The real reward. Fee credit, published, capped, and actually paid. This is the one that parents care about."),
        ("EVERY 2 MONTHS", "The inter-school championship", DEEP,
         "The big one. Sixteen campuses, trophies, a ceremony, and a camera. This is what sponsors pay for.")]
gap = 0.3; cw = (W - 2*M - gap*2) / 3
for i, (freq, t, col, b) in enumerate(cols):
    x = M + i*(cw+gap)
    box(s, x, 2.4, cw, 3.1, fill=WHITE)
    rect(s, x, 2.4, cw, 0.06, col)
    text(s, x+0.3, 2.68, cw-0.6, 0.3, [[(freq, {"size": 11, "bold": True, "color": col})]])
    text(s, x+0.3, 3.05, cw-0.6, 0.7, [[(t, {"size": 19, "bold": True, "color": INK})]], line_spacing=1.1)
    text(s, x+0.3, 3.95, cw-0.6, 1.4, [[(b, {"size": 12, "color": GREY})]], line_spacing=1.25)
box(s, M, 5.75, W-2*M, 0.75, fill=TEAL_PALE)
text(s, M+0.3, 5.95, W-2*M-0.6, 0.5,
     [[("The monthly rhythm is what keeps the notebook open. ", {"size": 13, "bold": True, "color": TEAL}),
       ("The championship is the photo opportunity. Neither replaces the other.", {"size": 13, "color": INK})]])

# ================================================================ 13 CHAMPIONSHIP
s = slide()
brandbar(s); eyebrow(s, "The big event")
head(s, "Sixteen school champions, not five finalists",
     "A live online final for 48 finalists is how you end up with a cheating scandal and a dead programme.")
box(s, M, 2.4, 5.8, 2.9, fill=WHITE)
rect(s, M, 2.4, 5.8, 0.06, TEAL)
text(s, M+0.32, 2.68, 5.2, 0.35, [[("PHASE 1 \u00b7 SCHOOL HEAT", {"size": 11, "bold": True, "color": TEAL})]])
text(s, M+0.32, 3.05, 5.2, 2.0,
     [[("Two weeks, asynchronous, in the app.", {"size": 15, "bold": True, "color": INK})],
      [("Every student in the class can enter. Same questions, done in their own time inside a two-week window.",
        {"size": 12.5, "color": INK})],
      [("No timing pressure. No dropped connections. No proctoring needed. This is where \u201crepresent your school\u201d "
        "pride actually lives \u2014 and participation stays near total, because anyone can enter.",
        {"size": 11.5, "color": GREY})]], space=9, line_spacing=1.2)
box(s, 6.9, 2.4, W-M-6.9, 2.9, fill=DEEP)
text(s, 7.2, 2.68, 5.2, 0.35, [[("PHASE 2 \u00b7 CITY FINAL", {"size": 11, "bold": True, "color": GOLD_LT})]])
text(s, 7.2, 3.05, 5.2, 2.0,
     [[("Sixteen students. One afternoon.", {"size": 15, "bold": True, "color": WHITE})],
      [("One champion per school, one per class. Live, but sixteen people, all on campus, on good connections, "
        "with staff in the room.", {"size": 12.5, "color": WHITE})],
      [("Genuinely manageable, and it makes a real ceremony worth filming.",
        {"size": 11.5, "color": TEAL_LT})]], space=9, line_spacing=1.2)
rows = [["Place", "Reward", "How many"],
        ["School champion", "Bursary + trophy + name on the school's banner + a slot in the final", "16"],
        ["City winner 1\u20133", "Laptop or tablet", "3"],
        ["City 4\u20135", "Fee waiver", "2"],
        ["Top school of the term", "Inter-school trophy and banner", "1"]]
table(s, M, 5.5, W-2*M, rows, [2.6, 7.7, 1.5], rh=0.36, fsize=11)

# ================================================================ 14 PRIZES
s = slide()
brandbar(s); eyebrow(s, "The prize ladder")
head(s, "Rewarding the middle, not just the peak",
     "The top 20% are already motivated by grades. The programme lives or dies in the middle.")
rows = [["Band", "Reward", "Cadence", "Why"],
        ["Anyone taking part", "Badge, name on the monthly board, a branded bookmark", "Monthly",
         "Participation is the goal, so reward the act of participating"],
        ["50%+ (the middle half)", "Merit bursary \u2014 real money off the fee", "Monthly",
         "The largest group, the biggest family impact, easiest for sponsors to fund"],
        ["70%+", "Certificate and merit gear", "Monthly", "Recognition, not material"],
        ["Top 1 per year group", "Laptop", "Annual", "A real trophy \u2014 eight winners, not one, which removes the incentive to cheat"],
        ["House champion", "Trophy at the ceremony", "Annual", "The photo opportunity, and the sponsor's logo"]]
table(s, M, 2.35, W-2*M, rows, [2.5, 4.0, 1.3, 4.0], rh=0.62, fsize=11)
box(s, M, 5.9, W-2*M, 0.75, fill=RED_BG)
text(s, M+0.3, 6.1, W-2*M-0.6, 0.5,
     [[("Removed: ", {"size": 13, "bold": True, "color": RED}),
       ("\u201ca branded pen for 40%.\u201d It tells a child they did badly and hands them a consolation prize. That is worse "
        "than giving nothing.", {"size": 13, "color": INK})]])

# ================================================================ 15 MARKETING
s = slide()
brandbar(s); eyebrow(s, "The marketing engine")
head(s, "Every printed batch carries its own tracked link",
     "This is how the school answers the only question that matters: which notebooks actually worked?")
box(s, M, 2.4, 7.0, 1.5, fill=DEEP)
text(s, M+0.3, 2.68, 6.4, 0.9,
     [[("https://<host>/t/{batch}/{subject}", {"size": 15, "bold": True, "color": GOLD_LT, "font": "Consolas"})],
      [("redirects to the code entry screen, and records the scan", {"size": 11.5, "color": TEAL_LT})]],
     space=6)
cardlist(s, M, 4.15, 7.0, [
    ("One link per print run",
     "Main campus Physics vs Capital campus Maths are separately attributable from day one."),
    ("Measured, not guessed",
     "Scans, participation and average score per batch, per campus, per subject \u2014 the real marketing number."),
    ("Zero cost",
     "The tracking is a line of code. There is no extra spend to attribute it."),
], h=0.72)
box(s, 8.2, 2.4, W-M-8.2, 3.95, fill=WHITE)
rect(s, 8.2, 2.4, W-M-8.2, 0.06, GOLD)
text(s, 8.5, 2.7, W-M-8.8, 0.35, [[("AND THE BIGGEST LEVER", {"size": 11, "bold": True, "color": GOLD})]])
text(s, 8.5, 3.1, W-M-8.8, 0.9,
     [[("Zero-rated data", {"size": 22, "bold": True, "color": INK})]])
text(s, 8.5, 3.95, W-M-8.8, 2.2,
     [[("Students are on metered mobile data. If the operator zero-rates this host, participation does not improve "
        "slightly \u2014 it changes order of magnitude.", {"size": 12.5, "color": INK})],
      [("A full quiz page already costs 2.5 KB gzipped, so this is a cheap ask with an enormous ceiling. "
        "It is the single most valuable thing an affiliated operator can contribute.",
        {"size": 12, "color": GREY})]], space=9, line_spacing=1.2)

# ================================================================ 16 SPONSORSHIP
s = slide()
brandbar(s); eyebrow(s, "Sponsorship")
head(s, "Sixteen schools changes the conversation",
     "Stop selling \u201clogo on a quiz\u201d. Sell the championship.")
box(s, M, 2.4, 5.8, 2.7, fill=RED_BG)
text(s, M+0.32, 2.68, 5.2, 0.35, [[("WHAT DOES NOT SELL", {"size": 11, "bold": True, "color": RED})]])
text(s, M+0.32, 3.05, 5.2, 1.9,
     [[("\u201cPut your logo on our quiz.\u201d", {"size": 17, "bold": True, "color": INK})],
      [("This is a marketing sponsorship. Education CSR budgets are earmarked for scholarships, infrastructure "
        "and teaching \u2014 a completely different budget line at most corporates. Expect it to be hard.",
        {"size": 12.5, "color": INK})]], space=10, line_spacing=1.2)
box(s, 6.9, 2.4, W-M-6.9, 2.7, fill=GREEN_BG)
text(s, 7.2, 2.68, 5.2, 0.35, [[("WHAT SELLS", {"size": 11, "bold": True, "color": GREEN})]])
text(s, 7.2, 3.05, 5.2, 1.9,
     [[("\u201cTitle sponsor of a 16-school championship.\u201d", {"size": 17, "bold": True, "color": INK})],
      [("16 campuses, 2,000+ students, a recurring streamed event, trophies, media coverage, and a clean "
        "education-access outcome story. That is a headline CSR asset.",
        {"size": 12.5, "color": INK})]], space=10, line_spacing=1.2)
rows = [["Tier", "What they buy", "How easy"],
        ["Scholarship fund", "\u201cWe underwrite N merit bursaries\u201d \u2014 maps perfectly to education-access outcomes", "Easiest"],
        ["In-kind prizes", "Printers, tablets, ISP kit, local vouchers \u2014 hugely valuable, almost no cash", "Very easy"],
        ["Named prize", "\u201cThis month's top scorer wins a [brand] kit\u201d", "Moderate"],
        ["Presented by", "Title sponsor of the biennial championship ceremony", "Moderate"]]
table(s, M, 5.3, W-2*M, rows, [2.6, 7.9, 1.3], rh=0.36, fsize=11)
footer(s, "Rule: run phase 1 with zero sponsors. The bursary model already funds the core. Sponsors are upside, not the business case.")

# ================================================================ 17 PRIVACY
s = slide()
brandbar(s); eyebrow(s, "Privacy and safeguarding")
head(s, "Built GDPR-K grade, by default",
     "Pakistan has no enacted statute comparable to GDPR or COPPA. That is not a licence to collect loosely.")
items = [("Nothing personal is ever typed in", TEAL,
          "No signup form. No name, no father's name, no class, no roll number. The student enters a 6-character printed code."),
         ("Nothing identifying is ever shown", TEAL,
          "Public boards show first name and campus only. No guardian names, no student numbers, no photographs."),
         ("Every point is traceable", TEAL,
          "The points ledger is append-only. A parent can audit every single point their child has ever been awarded."),
         ("A child can always reach an adult", GOLD,
          "The front office number is printed inside the front cover, permanently, regardless of what the server is doing.")]
y = 2.4
for t, col, b in items:
    box(s, M, y, W-2*M, 0.78, fill=WHITE)
    rect(s, M, y, 0.05, 0.78, col)
    text(s, M+0.3, y+0.13, 4.4, 0.3, [[(t, {"size": 14, "bold": True, "color": INK})]])
    text(s, M+5.0, y+0.14, W-2*M-5.3, 0.55, [[(b, {"size": 12, "color": GREY})]], line_spacing=1.2)
    y += 0.9
box(s, M, 6.05, W-2*M, 0.65, fill=AMBER_BG)
text(s, M+0.3, 6.2, W-2*M-0.6, 0.4,
     [[("Before launch: ", {"size": 12.5, "bold": True, "color": AMBER}),
       ("obtain parental consent at enrolment, publish a plain-language privacy notice inside the front cover, "
        "and confirm ICT Directorate guidance with local counsel.", {"size": 12.5, "color": INK})]])

# ================================================================ 18 ROLLOUT
s = slide()
brandbar(s); eyebrow(s, "Execution")
head(s, "Four phases, and a kill switch at every step")
phases = [("PHASE 1", "4\u20136 weeks", TEAL,
           "One subject, one chapter, one class. No sponsors, no ceremony, no bursary. "
           "The only question: will they scan?"),
          ("PHASE 2", "Months 2\u20133", TEAL,
           "All subjects. Weekly house boards. First merit bursary actually paid out. "
           "Teacher dashboard switched on."),
          ("PHASE 3", "Months 4\u20136", GOLD,
           "First inter-school championship. Ceremonies, trophies, and the first sponsorship conversation."),
          ("PHASE 4", "Year 2", DEEP,
           "Championship becomes a fixture. Sponsor renews. New campus cohorts onboarded.")]
gap = 0.28; cw = (W - 2*M - gap*3) / 4
for i, (p, dur, col, b) in enumerate(phases):
    x = M + i*(cw+gap)
    box(s, x, 2.45, cw, 2.5, fill=WHITE)
    rect(s, x, 2.45, cw, 0.06, col)
    text(s, x+0.28, 2.72, cw-0.56, 0.3, [[(p, {"size": 11, "bold": True, "color": col})]])
    text(s, x+0.28, 3.05, cw-0.56, 0.35, [[(dur, {"size": 17, "bold": True, "color": INK})]])
    text(s, x+0.28, 3.55, cw-0.56, 1.3, [[(b, {"size": 11, "color": GREY})]], line_spacing=1.25)
box(s, M, 5.3, W-2*M, 1.0, fill=DEEP)
text(s, M+0.32, 5.52, W-2*M-0.64, 0.7,
     [[("The kill switch. ", {"size": 14, "bold": True, "color": GOLD_LT}),
       ("If monthly participation is below 50% at the end of phase 1, stop and fix it. Do not scale a weak "
        "programme across 16 campuses \u2014 that is how a good idea dies of bad management rather than bad design.",
        {"size": 13.5, "color": WHITE})]], line_spacing=1.2)

# ================================================================ 19 METRICS
s = slide()
brandbar(s); eyebrow(s, "Measurement")
head(s, "One number decides whether this lives",
     "Track it weekly. Everything else is diagnostic.")
box(s, M, 2.4, W-2*M, 1.5, fill=DEEP)
text(s, M+0.35, 2.62, 5.0, 0.8,
     [[("MONTHLY PARTICIPATION", {"size": 11, "bold": True, "color": GOLD_LT})],
      [("Share of enrolled students who opened at least one chapter this month", {"size": 12, "color": TEAL_LT})]],
     space=5)
text(s, 8.4, 2.6, W-M-8.4-0.35, 1.1,
     [[("Below 25%", {"size": 20, "bold": True, "color": RED})],
      [("At risk \u2014 stop and fix", {"size": 11, "color": TEAL_LT})]], align=PP_ALIGN.CENTER)
text(s, 9.6, 2.6, 1.8, 1.1, [[("\u25b2", {"size": 16, "color": TEAL_LT})]], align=PP_ALIGN.CENTER)
text(s, 10.7, 2.6, W-M-10.7-0.35, 1.1,
     [[("Above 50%", {"size": 20, "bold": True, "color": GREEN_LT})],
      [("On track \u2014 scale", {"size": 11, "color": TEAL_LT})]], align=PP_ALIGN.CENTER)
rows = [["What we also watch", "Why it matters", "Who acts on it"],
        ["Participation rate per campus", "Which campuses are engaged, and which need a teacher's nudge", "Campus principal"],
        ["Scans per printed batch", "Which notebook print run actually worked \u2014 the marketing number", "Marketing / HQ"],
        ["Average score per chapter", "Which chapters the cohort actually struggles with", "Subject teacher"],
        ["Share of students reaching 50%+", "Whether the programme is lifting the middle, not just the top", "Head of school"],
        ["Points redeemed as bursary", "Actual cost to the school, against the 0.5\u20131% cap", "Finance"]]
table(s, M, 4.2, W-2*M, rows, [4.3, 6.0, 1.5], rh=0.44, fsize=11)
footer(s, "The teacher-facing report is not a by-product. It is the reason teachers support the programme instead of quietly resenting it.")

# ================================================================ 20 COST
s = slide()
brandbar(s); eyebrow(s, "What it costs")
head(s, "Almost nothing to start")
rows = [["Item", "Cost", "Note"],
        ["QR code printed on the notebook cover", "~PKR 0", "You are already printing these. This is a design change."],
        ["Access code inside the front cover", "~PKR 0", "Printed by the school alongside the class list."],
        ["The application", "PKR 0", "No licences, no hosting minimum, no vendor. Runs on one small server."],
        ["Deployment to 16 campuses", "Minimal", "Server-side software update, not a campus-by-campus installation."],
        ["Merit bursary pool", "0.5\u20131% of fee revenue", "Capped, published, and the real cost. Budget it deliberately."],
        ["Inter-school championship", "Per-event", "Sponsorship-funded. Do not run phase 1 on sponsor money."]]
table(s, M, 2.4, W-2*M, rows, [4.2, 2.4, 5.2], rh=0.52, fsize=11)
box(s, M, 6.0, W-2*M, 0.72, fill=TEAL_PALE)
text(s, M+0.3, 6.2, W-2*M-0.6, 0.45,
     [[("The expensive part is not software. ", {"size": 13, "bold": True, "color": TEAL}),
       ("It is teacher adoption, and it is solved by giving teachers something they want: a free, live picture of "
        "which chapters their own class is weak in.", {"size": 13, "color": INK})]])

# ================================================================ 21 ASKS
s = slide(dark=True)
brandbar(s, dark=True); eyebrow(s, "What we need", color=GOLD_LT)
head(s, "Three decisions", color=WHITE, subcolor=TEAL_LT,
     sub="Nothing here needs a new budget line. All three are policy choices.")
asks = [("01", "Name a pilot", "One class, one subject, one campus. Six weeks. A science teacher who volunteers, "
        "not the most eager head of department."),
        ("02", "Agree the framing", "\u201cMerit bursary\u201d, never \u201cearn your own fee\u201d. And quiz points never decide "
        "Head Boy, monitors or prefects \u2014 that stays exactly as it is today."),
        ("03", "Open the operator conversation", "Zero-rated data on the quiz host, and a first look at "
        "sponsoring the inter-school championship. Both are worth more than the software.")]
y = 2.6
for num, t, b in asks:
    box(s, M, y, W-2*M, 1.15, fill=RGBColor(0x14, 0x4A, 0x59))
    rect(s, M, y, 0.05, 1.15, GOLD)
    text(s, M+0.35, y+0.3, 0.9, 0.5, [[(num, {"size": 26, "bold": True, "color": GOLD})]])
    text(s, M+1.4, y+0.22, 4.2, 0.4, [[(t, {"size": 17, "bold": True, "color": WHITE})]])
    text(s, M+5.7, y+0.26, W-2*M-6.0, 0.7, [[(b, {"size": 12.5, "color": TEAL_LT})]], line_spacing=1.25)
    y += 1.32
text(s, M, 6.65, W-2*M, 0.4,
     [[("Total cost to pilot: the price of six weeks of one teacher's goodwill.",
        {"size": 13, "italic": True, "color": GOLD_LT})]])

# ================================================================ 22 CLOSING
s = slide(dark=True, count=False)
rect(s, 0, 0, 0.18, H, GOLD)
text(s, 1.4, 2.2, 10.5, 0.4,
     [[("THE POINT", {"size": 12, "bold": True, "color": GOLD_LT})]])
text(s, 1.4, 2.8, 10.5, 2.6,
     [[("It is not a quiz app.", {"size": 34, "bold": True, "color": WHITE})],
      [("It is a reason to open the notebook.", {"size": 34, "bold": True, "color": TEAL_LT})]],
     space=14, line_spacing=1.1)
rect(s, 1.4, 5.05, 1.5, 0.045, GOLD)
text(s, 1.4, 5.35, 9.5, 1.1,
     [[("Every other school initiative asks a student to do something extra. This one pays them for what they "
        "were already doing \u2014 which is why it will still be running in March.",
        {"size": 16, "color": TEAL_LT})]], line_spacing=1.3)

# -------------------------------------------------------------------------
out = os.path.join(HERE, "TEFOS-Quiz-Proposal.pptx")
prs.save(out)
print(f"Saved {out}  ({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
