#!/usr/bin/env python3
"""
Builds the designed 22-slide Telecom Foundation TEFOS Quiz proposal.
Outputs: TEFOS-Quiz-Proposal-Designed.pdf / .pptx and slides/slide_XX.png
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slide_engine import SlideCanvas, PAL, export_deck, HERE, measure_text_px

W, H, M = SlideCanvas.W, SlideCanvas.H, SlideCanvas.M
CW = W - 2 * M  # content width 1728
slides = []

def S(n, **kw):
    sc = SlideCanvas(n, **kw); slides.append(sc); return sc

def tip_bar(sc, y, lead, body, emoji="bulb", fill=None, border=None, lead_col=None, h=86):
    fill = fill or (PAL["TF_DARK_CARD"] if sc.dark else PAL["TF_MINT"])
    border = border or (PAL["TF_DARK_LINE"] if sc.dark else PAL["TF_MINT_BDR"])
    lead_col = lead_col or (PAL["TF_LIME_BRT"] if sc.dark else PAL["TF_EMERALD"])
    body_col = PAL["DARK_TEXT"] if sc.dark else PAL["INK"]
    sc.rect(M, y, CW, h, fill=fill, stroke=border, rx=18)
    sc.add_twemoji(emoji, M + 26, y + h/2 - 17, 34)
    sc.add_rich_text(M + 82, y + 14, CW - 110, h - 28,
        [[(lead + " ", {"weight": "bold", "size_px": 18.5, "color": lead_col}),
          (body, {"size_px": 18.5, "color": body_col})]], v_align="middle", line_height=1.3)

def stat_card(sc, x, y, w, h, big, small, emoji, accent):
    sc.card(x, y, w, h, top_stripe=accent)
    sc.add_twemoji(emoji, x + w/2 - 18, y + 22, 36)
    sc.add_text(x, y + 68, w, 50, big, size_px=38, weight="extrabold",
                color=accent, align="center", family="Poppins")
    sc.add_text(x + 16, y + 122, w - 32, 50, small, size_px=14.5, weight="medium",
                color=PAL["SLATE"], align="center", line_height=1.25)

def table(sc, x, y, w, rows, colw, rh=54, fsize=16, head_fill=None):
    head_fill = head_fill or PAL["TF_EMERALD"]
    n = len(rows)
    sc.rect(x, y, w, rh * n, fill=PAL["WHITE"], stroke=PAL["BORDER"], rx=14, shadow="sm")
    # header
    cid = sc._next_id("tbl")
    sc.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{rh*n}" rx="14"/></clipPath>')
    sc.bg_els.append(f'<rect x="{x}" y="{y}" width="{w}" height="{rh}" fill="{head_fill}" clip-path="url(#{cid})"/>')
    for i in range(1, n):
        if i % 2 == 0:
            sc.bg_els.append(f'<rect x="{x}" y="{y+i*rh}" width="{w}" height="{rh}" fill="{PAL["CANVAS_ALT"]}" clip-path="url(#{cid})"/>')
        sc.bg_els.append(f'<line x1="{x}" y1="{y+i*rh}" x2="{x+w}" y2="{y+i*rh}" stroke="{PAL["BORDER"]}" stroke-width="1"/>')
    for i, row in enumerate(rows):
        cx = x
        for j, cell in enumerate(row):
            tx_off = 0
            if isinstance(cell, tuple):
                em, cell = cell
                sc.add_twemoji(em, cx + 20, y + i*rh + rh/2 - 12, 24)
                tx_off = 36
            col = PAL["WHITE"] if i == 0 else PAL["INK"]
            wt = "bold" if (i == 0 or j == 0) else "regular"
            sz = fsize - 1.5 if i == 0 else fsize
            sc.add_text(cx + 20 + tx_off, y + i*rh, colw[j] - 36 - tx_off, rh, str(cell), size_px=sz,
                        weight=wt, color=col, v_align="middle", line_height=1.2,
                        letter_spacing=1.0 if i == 0 else 0)
            cx += colw[j]

def feature_card(sc, x, y, w, h, title, body, emoji=None, lucide=None, accent=None, body_size=16.5):
    accent = accent or PAL["TF_EMERALD"]
    sc.card(x, y, w, h, left_stripe=accent)
    if emoji:
        sc.icon_badge(x + 28, y + 24, 54, emoji=emoji, bg=PAL["TF_MINT"])
    else:
        sc.icon_badge(x + 28, y + 24, 54, lucide=lucide, bg=PAL["TF_MINT"], icon_color=accent)
    sc.add_text(x + 100, y + 26, w - 130, 32, title, size_px=20, weight="bold")
    sc.add_text(x + 100, y + 60, w - 130, h - 70, body, size_px=body_size,
                color=PAL["SLATE"], line_height=1.35)

# =============================================================== 01 TITLE
sc = S(1, dark=True, count=False, bg_image="processed/hero_emerald_bg.jpg")
sc.bg_els.append(f'<rect x="0" y="0" width="{W}" height="8" fill="url(#tf_brand_grad)"/>')
sc.add_image("tf_logo_dark.png", M, 64, 420, 54)
sc.add_eyebrow("A proposal for the Telecom Foundation Education System", "grad_cap", y=300)
sc.add_rich_text(M, 360, 1100, 260,
    [[("The notebook\nthat ", {"size_px": 92, "weight": "extrabold", "color": PAL["WHITE"]}),
      ("teaches back.", {"size_px": 92, "weight": "extrabold", "color": PAL["TF_LIME_BRT"]})]],
    line_height=1.02)
sc.bg_els.append(f'<rect x="{M}" y="610" width="160" height="6" rx="3" fill="url(#tf_gold_grad)"/>')
sc.add_text(M, 646, 980, 120,
    "A QR code on every subject notebook turns a finished chapter into a quiz, a rank, and a merit bursary — across all 16 TEFOS schools.",
    size_px=24, color=PAL["DARK_TEXT"], line_height=1.42)
# three chips
cx = M
for em, lbl in [("mobile", "Chapter quizzes"), ("medal", "Merit bursaries"), ("trophy", "Inter-school championship")]:
    tw = measure_text_px(lbl, "Poppins", "semibold", 16) + 70
    sc.rect(cx, 820, tw, 46, fill="rgba(255,255,255,0.07)", stroke="rgba(140,224,74,0.35)", rx=23)
    sc.add_twemoji(em, cx + 16, 831, 24)
    sc.add_text(cx + 50, 820, tw - 50, 46, lbl, size_px=16, weight="semibold", color=PAL["WHITE"], v_align="middle")
    cx += tw + 16
sc.add_text(M, H - 70, 900, 30, "TEFOS QUIZ  ·  NOTEBOOK QR PROGRAMME  ·  2026", size_px=13, weight="bold",
            color=PAL["DARK_MUTED"], letter_spacing=2.2)
sc.add_text(W - M - 500, H - 70, 500, 30, "Transforming Communities", size_px=15, weight="medium",
            color=PAL["TF_LIME_BRT"], align="right", italic=True)

# =============================================================== 02 THE IDEA
sc = S(2, dark=True, count=False, bg_image="processed/waves_dark_bg.jpg")
sc.add_header("The idea")
sc.add_eyebrow("The idea in one breath", "bulb", y=120)
steps = [("open_book", "A student finishes Chapter 1."),
         ("mobile", "They scan the book they are already holding."),
         ("writing", "They answer four questions."),
         ("medal", "They earn points toward next month's bursary.")]
y = 200
for i, (em, txt) in enumerate(steps):
    sc.rect(M, y, 1180, 108, fill="rgba(14,71,47,0.72)", stroke=PAL["TF_DARK_LINE"], rx=22)
    sc.rect(M + 22, y + 24, 60, 60, fill="rgba(124,192,64,0.16)", rx=16)
    sc.add_twemoji(em, M + 36, y + 38, 32)
    sc.add_text(M + 104, y, 70, 108, f"0{i+1}", size_px=44, family="Bebas Neue", color=PAL["GOLD_BRT"], v_align="middle")
    sc.add_text(M + 176, y, 980, 108, txt, size_px=30, weight="bold", color=PAL["WHITE"], v_align="middle")
    y += 124
# right callout
sc.card(1340, 200, 484, 480, fill="rgba(5,36,23,0.78)", stroke=PAL["TF_DARK_LINE"], rx=26)
sc.add_twemoji("sparkles", 1380, 240, 44)
sc.add_text(1380, 300, 410, 200, "No app.\nNo signup.\nNo form.\nNo behaviour change.", size_px=34, weight="extrabold",
            color=PAL["WHITE"], line_height=1.18)
sc.add_text(1380, 570, 410, 90, "— which is precisely why it will work.", size_px=20, color=PAL["TF_LIME_BRT"], italic=True, line_height=1.3)
sc.add_footer("Everything in this deck exists to protect those four steps.", "pushpin")

# =============================================================== 03 INSIGHT
sc = S(3)
sc.add_header("The insight")
sc.add_eyebrow("The insight", "bulb")
sc.add_title("The QR code is already in the book", highlight="already in the book",
             sub="This is the only marketing surface a school owns that the student touches voluntarily, every day.")
cards = [("target", "It meets the student at peak attention",
          "They have just finished the chapter. The book is open. The page is right there."),
         ("seedling", "It requires zero new behaviour",
          "No app to download, no code to memorise, no website to visit, no reminder to send."),
         ("school", "It travels home and gets photographed",
          "It sits open on a desk where visitors see it, and ends up in photos, on desks, in parents' houses.")]
y = 290
for em, t, b in cards:
    feature_card(sc, M, y, 1000, 172, t, b, emoji=em)
    y += 194
sc.card(1140, 290, 684, 556, bg_image="processed/card_emerald_ribbons.jpg", rx=26, stroke=None)
sc.add_text(1184, 330, 600, 120, "Every other school channel is a push.", size_px=34, weight="extrabold", color=PAL["WHITE"], line_height=1.15)
yy = 470
for em, t in [("megaphone", "Newsletters get ignored."), ("trash", "Flyers get binned."), ("mobile", "Apps get deleted.")]:
    sc.add_twemoji(em, 1184, yy, 26); sc.add_text(1224, yy - 2, 540, 32, t, size_px=20, color=PAL["DARK_TEXT"]); yy += 46
sc.rect(1184, 740, 300, 56, fill=PAL["TF_LIME_BRT"], rx=28)
sc.add_text(1184, 740, 300, 56, "✦  This one is a pull.", size_px=19, weight="extrabold", color=PAL["TF_DEEP"], align="center", v_align="middle")
sc.add_footer("Compare: a school newsletter competes with everything. A QR in a textbook competes with nothing.", "magnifying_glass")

# =============================================================== 04 JOURNEY
sc = S(4)
sc.add_header("Student journey")
sc.add_eyebrow("The student journey", "rocket")
sc.add_title("Five steps. About ninety seconds.", highlight="ninety seconds.")
steps = [("qr-code", "Scan", "The QR on the cover of any subject notebook."),
         ("key-round", "Enter code", "Six characters printed inside the front cover."),
         ("book-open", "Pick chapter", "The one they just finished. Tap Go."),
         ("file-check", "Answer", "Five questions, mostly about their own class."),
         ("trophy", "Rank up", "Points, a rank tier, and a place on the board.")]
gap = 28; cw = (CW - gap * 4) / 5
# connector line
sc.bg_els.append(f'<line x1="{M+cw/2}" y1="372" x2="{W-M-cw/2}" y2="372" stroke="{PAL["TF_MINT_BDR"]}" stroke-width="3" stroke-dasharray="8 8"/>')
for i, (ic, t, b) in enumerate(steps):
    x = M + i * (cw + gap)
    sc.card(x, 300, cw, 420, top_stripe=PAL["TF_EMERALD"] if i < 4 else PAL["GOLD"])
    sc.rect(x + cw/2 - 36, 336, 72, 72, fill=PAL["TF_EMERALD"] if i < 4 else PAL["GOLD"], rx=36)
    sc.add_lucide(ic, x + cw/2 - 18, 354, 36, color=PAL["WHITE"])
    sc.add_text(x, 430, cw, 50, f"0{i+1}", size_px=40, family="Bebas Neue", color=PAL["TF_LIME"], align="center")
    sc.add_text(x, 486, cw, 40, t, size_px=24, weight="bold", align="center")
    sc.add_text(x + 24, 532, cw - 48, 120, b, size_px=16, color=PAL["SLATE"], align="center", line_height=1.35)
tip_bar(sc, 770, "There is no step six.",
        "That is the entire design. Everything in this proposal exists to keep students at step five.", emoji="check", h=90)
sc.add_footer("Average completion in the prototype: 1 minute 32 seconds, on a five-year-old Android over 3G.", "stopwatch")

# =============================================================== 05 RULES
sc = S(5)
sc.add_header("Participation engine")
sc.add_eyebrow("The participation engine", "fire")
sc.add_title("Five non-negotiable rules", highlight="non-negotiable",
             sub="Break any one of these and the programme dies quietly within a term.")
rules = [("Points are never negative", "A student who tries and gets it wrong must never end up worse off than one who never scanned.", "stop", PAL["CORAL"]),
         ("Participation earns the first rank", "A student who takes part always has an identity, even at zero percent.", "sparkles", PAL["TF_EMERALD"]),
         ("Only a first attempt moves the board", "Retries pay a little, so nobody is locked out — but nobody can farm the board.", "lock", PAL["TF_EMERALD"]),
         ("Show growth, not distance", "“You gained 180 points”, not “you are 2,400 short” — unless the gap is genuinely reachable.", "chart_up", PAL["TF_EMERALD"]),
         ("Never publish only the top", "Champions, most improved, and participation rate. Always all three.", "bar_chart", PAL["GOLD"])]
y = 290
for i, (t, b, em, col) in enumerate(rules):
    sc.card(M, y, CW, 108, left_stripe=col)
    sc.rect(M + 28, y + 28, 52, 52, fill=col, rx=26)
    sc.add_text(M + 28, y + 28, 52, 52, str(i + 1), size_px=24, weight="extrabold", color=PAL["WHITE"], align="center", v_align="middle")
    sc.add_text(M + 104, y, 520, 108, t, size_px=22, weight="bold", v_align="middle")
    sc.add_text(M + 640, y, 1000, 108, b, size_px=18, color=PAL["SLATE"], v_align="middle", line_height=1.3)
    sc.add_twemoji(em, W - M - 70, y + 34, 40)
    y += 126
sc.add_footer("Each rule is enforced in code, not in policy — the database refuses to break them.", "shield")

# =============================================================== 06 POINTS
sc = S(6)
sc.add_header("The arithmetic")
sc.add_eyebrow("The one number that matters most", "scales")
sc.add_title("Punishing a wrong answer kills participation", highlight="kills participation",
             sub="The arithmetic below is the single most important line in this proposal.")
half = (CW - 32) / 2
# left - bad
sc.card(M, 300, half, 400, fill=PAL["CORAL_BG"], stroke=PAL["CORAL_BDR"], top_stripe=PAL["CORAL"])
sc.add_twemoji("cross", M + 32, 332, 28)
sc.add_text(M + 72, 334, 500, 30, "AS ORIGINALLY SPECIFIED", size_px=13.5, weight="bold", color=PAL["CORAL"], letter_spacing=2)
sc.add_text(M + 32, 376, half - 64, 50, "+10 correct   ·   −5 wrong", size_px=32, weight="extrabold")
yy = 450
for lbl, val, col in [("5 of 5 right", "+50", PAL["TF_EMERALD"]), ("3 of 5 right", "+5", PAL["GOLD"]),
                      ("2 of 5 right", "−5", PAL["CORAL"]), ("All wrong", "−25", PAL["CORAL"]), ("Never scanned", "0", PAL["MUTED"])]:
    sc.add_text(M + 32, yy, 400, 30, lbl, size_px=18, color=PAL["SLATE"])
    sc.add_text(M + half - 200, yy, 160, 30, val, size_px=20, weight="extrabold", color=col, align="right")
    sc.bg_els.append(f'<line x1="{M+32}" y1="{yy+40}" x2="{M+half-40}" y2="{yy+40}" stroke="{PAL["CORAL_BDR"]}" stroke-width="1"/>')
    yy += 48
# right - good
x2 = M + half + 32
sc.card(x2, 300, half, 400, fill=PAL["TF_MINT"], stroke=PAL["TF_MINT_BDR"], top_stripe=PAL["TF_EMERALD"])
sc.add_twemoji("check", x2 + 32, 332, 28)
sc.add_text(x2 + 72, 334, 500, 30, "AS BUILT", size_px=13.5, weight="bold", color=PAL["TF_EMERALD"], letter_spacing=2)
sc.add_text(x2 + 32, 376, half - 64, 50, "+10  ·  0  ·  +3 retry  ·  +25 perfect", size_px=30, weight="extrabold")
yy = 450
for lbl, val, col in [("All right", "+75", PAL["TF_EMERALD"]), ("Half right", "+25", PAL["TF_EMERALD"]),
                      ("Two of five", "0", PAL["MUTED"]), ("All wrong", "0", PAL["MUTED"]), ("Never scanned", "0", PAL["MUTED"])]:
    sc.add_text(x2 + 32, yy, 400, 30, lbl, size_px=18, color=PAL["SLATE"])
    sc.add_text(x2 + half - 200, yy, 160, 30, val, size_px=20, weight="extrabold", color=col, align="right")
    sc.bg_els.append(f'<line x1="{x2+32}" y1="{yy+40}" x2="{x2+half-40}" y2="{yy+40}" stroke="{PAL["TF_MINT_BDR"]}" stroke-width="1"/>')
    yy += 48
sc.rect(M, 750, CW, 130, fill="url(#tf_dark_grad)", rx=20)
sc.add_twemoji("warning", M + 30, 795, 40)
sc.add_text(M + 94, 750, CW - 130, 130,
    "With negatives, a student who scans and does badly is worse off than one who ignores the book entirely. The programme punishes exactly the behaviour it needs most.",
    size_px=20, weight="bold", color=PAL["WHITE"], v_align="middle", line_height=1.35)
sc.add_footer("The floor is 0. Scanning always beats not scanning — and the only route to the top is accuracy on first tries.", "key")

# =============================================================== 07 RANKS
sc = S(7)
sc.add_header("Rank ladder")
sc.add_eyebrow("Rank ladder", "glowing_star")
sc.add_title("Spark to Galaxy", highlight="Galaxy",
             sub="Every student has an identity. Nobody sits in a dead zone below the first rung.")
tiers = [("sparkles", "Spark", "Any points", "You took part. That is the whole entry fee.", PAL["TF_EMERALD"]),
         ("star", "Rising Star", "30%+", "Getting going.", PAL["TF_EMERALD"]),
         ("glowing_star", "Star", "50%+", "Solid and consistent.", PAL["TF_EMERALD"]),
         ("dizzy_star", "Bright Star", "70%+", "Reliably strong across chapters.", PAL["GOLD"]),
         ("fire", "Supernova", "85%+", "Outstanding.", PAL["GOLD"]),
         ("milky_way", "Galaxy", "95%+", "Exceptional.", PAL["GOLD"])]
# staircase
base_x, base_y = M, 720; stw = 168; sth = 58
for i, (em, name, rate, desc, col) in enumerate(tiers):
    x = base_x + i * (stw + 10); h = sth + i * 62; y = base_y - h
    sc.rect(x, y, stw, h, fill=col, rx=14, opacity=0.22 + i * 0.11)
    sc.add_twemoji(em, x + stw/2 - 22, y - 60, 44)
    sc.add_text(x, y + 10, stw, 30, name, size_px=18, weight="bold", align="center", color=PAL["INK"])
    sc.add_text(x, y + 38, stw, 24, rate, size_px=15, weight="bold", align="center", color=PAL["INK"])
sc.add_text(M, 736, 1070, 60, "Rank = points earned ÷ points available. Tier appears after 5 chapters attempted.",
            size_px=15, weight="medium", color=PAL["SLATE"], italic=True)
# right panel
px = 1190; pw = W - M - px
sc.card(px, 300, pw, 300, top_stripe=PAL["CORAL"])
sc.add_twemoji("stop", px + 30, 330, 30)
sc.add_text(px + 72, 334, 400, 28, "THE ACTIVITY FLOOR", size_px=13.5, weight="bold", color=PAL["CORAL"], letter_spacing=2)
sc.add_text(px + 30, 380, pw - 60, 100,
    "Rank is points earned ÷ points available — never a raw average — and only appears after 5 chapters attempted.",
    size_px=17.5, weight="medium", line_height=1.38)
sc.add_text(px + 30, 486, pw - 60, 100,
    "Without the floor, a student sits one easy quiz, scores 95% and quits — and out-ranks the student who showed up every week.",
    size_px=15.5, color=PAL["SLATE"], line_height=1.38)
sc.card(px, 624, pw, 176, fill=PAL["GOLD_BG"], stroke=PAL["GOLD_BDR"], top_stripe=PAL["GOLD"])
sc.add_twemoji("bug", px + 30, 656, 30)
sc.add_rich_text(px + 72, 652, pw - 100, 130,
    [[("Bug we found and fixed: ", {"weight": "bold", "size_px": 15.5, "color": PAL["GOLD"]}),
      ("the floor applied to the data but not to the screen — a one-quiz student still read “Galaxy” on their own result. Now the displayed tier is clamped too.", {"size_px": 15.5, "color": PAL["INK"]})]],
    line_height=1.36)
sc.add_footer("Participation alone earns the first rank. The programme dies if the bottom half decides there is nothing to play for.", "heart_green")

# =============================================================== 08 SCREENS
sc = S(8)
sc.add_header("What students see")
sc.add_eyebrow("What the student sees", "mobile")
sc.add_title("Three screens, ninety seconds", highlight="ninety seconds")
shots = [("mockup_01_home.png", "The chapter hub", "Every subject, every chapter, one tap to start.", "open_book"),
         ("mockup_02_result.png", "The payoff", "Points, rank tier, and how far they have come this month.", "party"),
         ("mockup_03_leaderboard.png", "The 16-school board", "All campuses together — plus the reach line, shown only when close.", "trophy")]
gap = 36; iw = (CW - gap * 2) / 3
for i, (fn, t, b, em) in enumerate(shots):
    x = M + i * (iw + gap)
    sc.card(x, 236, iw, 720, rx=24)
    sc.add_image(fn, x + 16, 252, iw - 32, 500, rx=16, fit="cover")
    sc.add_twemoji(em, x + 28, 780, 30)
    sc.add_text(x + 72, 780, iw - 100, 36, t, size_px=22, weight="bold")
    sc.add_text(x + 28, 826, iw - 56, 110, b, size_px=16, color=PAL["SLATE"], line_height=1.35)
sc.add_footer("Server-rendered HTML, ~40 lines of JavaScript, 2.5 KB per quiz page. Works on any phone.", "satellite")

# =============================================================== 09 UNCHEATABLE
sc = S(9)
sc.add_header("Integrity")
sc.add_eyebrow("Integrity", "shield")
sc.add_title("A quiz nobody can google", highlight="nobody can google",
             sub="Half the questions are about things that happened in that specific classroom, that week.")
half = (CW - 32) / 2
sc.card(M, 300, half, 360, top_stripe=PAL["MUTED"])
sc.add_twemoji("magnifying_glass", M + 30, 330, 28)
sc.add_text(M + 72, 334, 400, 28, "THE USUAL KIND", size_px=13.5, weight="bold", color=PAL["MUTED"], letter_spacing=2)
sc.add_text(M + 30, 384, half - 60, 90, "“A body travels 120 m in 15 s at constant speed. What is its speed?”",
            size_px=21, weight="semibold", line_height=1.38)
sc.add_text(M + 30, 500, half - 60, 110,
    "Searchable in four seconds. The prize goes to whoever has the fastest internet connection and the most willing relatives.",
    size_px=16, color=PAL["SLATE"], line_height=1.38)
x2 = M + half + 32
sc.card(x2, 300, half, 360, bg_image="processed/card_stars_ascend.jpg", rx=20, stroke=None)
sc.add_twemoji("grad_cap", x2 + 30, 330, 28)
sc.add_text(x2 + 72, 334, 400, 28, "THE KIND WE USE", size_px=13.5, weight="bold", color=PAL["GOLD_BRT"], letter_spacing=2)
sc.add_text(x2 + 30, 384, half - 60, 120,
    "“On the first day of the Motion unit, which classroom activity did we do?”\n“Our lab report was due on which date?”",
    size_px=19, weight="semibold", color=PAL["WHITE"], line_height=1.38)
sc.add_text(x2 + 30, 530, half - 60, 90,
    "Nobody can search these. Only a student who was there can answer — we are paying for attention, not for guessing.",
    size_px=16, color=PAL["TF_LIME_BRT"], line_height=1.38)
gap = 24; sw = (CW - gap * 3) / 4
for i, (big, small, em, col) in enumerate([("0", "answer keys sent to any device", "lock", PAL["TF_EMERALD"]),
                                           ("5", "chapters before a rank shows", "books", PAL["TF_EMERALD"]),
                                           ("1", "first attempt per chapter, enforced", "key", PAL["TF_EMERALD"]),
                                           ("2.5 KB", "per quiz page, gzipped", "satellite", PAL["GOLD"])]):
    stat_card(sc, M + i * (sw + gap), 690, sw, 200, big, small, em, col)
sc.add_footer("Options are shuffled server-side on every request; the start time is HMAC-signed so the timer cannot be dodged.", "lock")

# =============================================================== 10 GROWTH
sc = S(10)
sc.add_header("Motivation")
sc.add_eyebrow("Motivation", "chart_up")
sc.add_title("Show growth. Show the gap only when it is reachable.", highlight="only when it is reachable",
             sub="The most common mistake in school gamification is telling a child exactly how far they are from winning.")
gap = 28; cw3 = (CW - gap * 2) / 3
cols = [("ALWAYS", "check", PAL["TF_EMERALD"], PAL["TF_MINT"], PAL["TF_MINT_BDR"],
         "“You are 180 points ahead of where you were last month.”", "Progress against yourself. This is what sustains effort."),
        ("ONLY IF REACHABLE", "target", PAL["GOLD"], PAL["GOLD_BG"], PAL["GOLD_BDR"],
         "“240 more points puts you on the top 10 board.”", "A real nudge, shown only to students within striking distance."),
        ("NEVER", "cross", PAL["CORAL"], PAL["CORAL_BG"], PAL["CORAL_BDR"],
         "“You are 2,400 points short of the board.”", "The gap is too big to close, so the rational move is to stop trying.")]
for i, (lbl, em, col, bg, bd, quote, note) in enumerate(cols):
    x = M + i * (cw3 + gap)
    sc.card(x, 310, cw3, 390, fill=bg, stroke=bd, top_stripe=col)
    sc.add_twemoji(em, x + 30, 342, 28)
    sc.add_text(x + 72, 346, 400, 28, lbl, size_px=13.5, weight="bold", color=col, letter_spacing=2)
    sc.add_text(x + 30, 400, cw3 - 60, 150, quote, size_px=25, weight="extrabold", line_height=1.3)
    sc.add_text(x + 30, 570, cw3 - 60, 80, note, size_px=16, color=PAL["SLATE"], line_height=1.35)
sc.card(M, 730, CW, 150, rx=20)
sc.add_twemoji("bar_chart", M + 32, 786, 40)
sc.add_rich_text(M + 100, 746, 560, 120,
    [[("Publish three boards, always.", {"weight": "extrabold", "size_px": 22, "color": PAL["TF_EMERALD"]})]], v_align="middle")
bx = M + 620
for em, t, s in [("trophy", "Champions", "Top scorers"), ("rocket", "Most improved", "Biggest monthly gain"), ("handshake", "Participation rate", "How many took part")]:
    sc.rect(bx, 754, 340, 102, fill=PAL["CANVAS_ALT"], stroke=PAL["BORDER"], rx=16)
    sc.add_twemoji(em, bx + 20, 784, 40)
    sc.add_text(bx + 76, 770, 250, 30, t, size_px=19, weight="bold")
    sc.add_text(bx + 76, 804, 250, 30, s, size_px=14.5, color=PAL["SLATE"])
    bx += 362
sc.add_footer("The third board is scored on participation, not scores — which gives smaller and weaker campuses a genuine way to win.", "seedling")

# =============================================================== 11 BURSARY
sc = S(11)
sc.add_header("The economics")
sc.add_eyebrow("The economics", "money_bag")
sc.add_title("The school pays in tuition credit, not cash", highlight="not cash",
             sub="This is the trick that makes the whole programme affordable at scale.")
half = (CW - 32) / 2
sc.card(M, 300, half, 350, fill=PAL["TF_MINT"], stroke=PAL["TF_MINT_BDR"], top_stripe=PAL["TF_EMERALD"])
sc.add_twemoji("check", M + 30, 330, 28)
sc.add_text(M + 72, 334, 400, 28, "WHAT IT IS", size_px=13.5, weight="bold", color=PAL["TF_EMERALD"], letter_spacing=2)
sc.add_text(M + 30, 380, half - 60, 50, "Merit bursary", size_px=36, weight="extrabold")
sc.add_text(M + 30, 440, half - 60, 90, "Up to 10 bursaries a month, each worth up to 10% of one month's tuition fee, awarded on points earned.",
            size_px=18, weight="medium", line_height=1.38)
sc.add_text(M + 30, 548, half - 60, 90, "Cost to the school: foregone revenue on a student who already pays. Budgetable, capped, predictable.",
            size_px=16, color=PAL["SLATE"], line_height=1.38)
x2 = M + half + 32
sc.card(x2, 300, half, 350, fill=PAL["CORAL_BG"], stroke=PAL["CORAL_BDR"], top_stripe=PAL["CORAL"])
sc.add_twemoji("cross", x2 + 30, 330, 28)
sc.add_text(x2 + 72, 334, 500, 28, "WHAT IT MUST NOT BE CALLED", size_px=13.5, weight="bold", color=PAL["CORAL"], letter_spacing=2)
sc.add_text(x2 + 30, 380, half - 60, 50, "“Students earn their own fee.”", size_px=30, weight="extrabold")
sc.add_text(x2 + 30, 440, half - 60, 100, "Identical budget. But it replaces a student election with a leaderboard, invites fee-regulation scrutiny, and reads badly in a newspaper.",
            size_px=18, weight="medium", line_height=1.38)
sc.add_text(x2 + 30, 560, half - 60, 60, "Same money, completely different posture.", size_px=16, color=PAL["SLATE"], italic=True)
sc.card(M, 686, CW, 170, fill=PAL["GOLD_BG"], stroke=PAL["GOLD_BDR"], left_stripe=PAL["GOLD"])
sc.add_twemoji("scales", M + 34, 740, 44)
sc.add_rich_text(M + 110, 700, CW - 150, 150,
    [[("The honest caveat: ", {"weight": "bold", "size_px": 18, "color": PAL["GOLD"]}),
      ("a bursary helps a wealthy family more than a poor one, because a rich family can absorb the fee. Keep a small, separately-funded need-based component — and let sponsors underwrite that, because it is the strongest education-access outcome report available.", {"size_px": 18, "color": PAL["INK"]})]],
    v_align="middle", line_height=1.4)
sc.add_footer("Cap the total value at 0.5–1% of annual fee revenue. Publish the cap.", "pushpin")

# =============================================================== 12 CADENCE
sc = S(12)
sc.add_header("Rhythm")
sc.add_eyebrow("Rhythm", "calendar")
sc.add_title("Three cadences, three different jobs", highlight="three different jobs",
             sub="A yearly reward attached to a daily habit is how engagement dies around week six.")
gap = 28; cw3 = (CW - gap * 2) / 3
cols = [("WEEKLY", "Star of the Week", "star", PAL["TF_EMERALD"],
         "Recognition only. House points, a name on the school board, and nothing else. Theatre, and that is fine — as long as nobody expects cash."),
        ("MONTHLY", "The merit bursary", "medal", PAL["GOLD"],
         "The real reward. Fee credit, published, capped, and actually paid. This is the one that parents care about."),
        ("EVERY 2 MONTHS", "The inter-school championship", "trophy", PAL["TF_EMERALD_DK"],
         "The big one. Sixteen campuses, trophies, a ceremony, and a camera. This is what sponsors pay for.")]
for i, (freq, t, em, col, b) in enumerate(cols):
    x = M + i * (cw3 + gap)
    sc.card(x, 310, cw3, 400, top_stripe=col)
    sc.rect(x + 30, 340, 160, 34, fill=PAL["TF_MINT"] if col != PAL["GOLD"] else PAL["GOLD_BG"], rx=17)
    sc.add_text(x + 30, 340, 160, 34, freq, size_px=12.5, weight="bold", color=col, letter_spacing=1.6, align="center", v_align="middle")
    sc.icon_badge(x + cw3 - 100, 332, 64, emoji=em, bg=PAL["CANVAS_ALT"], rx=18)
    sc.add_text(x + 30, 420, cw3 - 60, 90, t, size_px=30, weight="extrabold", line_height=1.15)
    sc.add_text(x + 30, 526, cw3 - 60, 170, b, size_px=17, color=PAL["SLATE"], line_height=1.4)
tip_bar(sc, 752, "The monthly rhythm is what keeps the notebook open.",
        "The championship is the photo opportunity. Neither replaces the other.", emoji="notebook", h=90)
sc.add_footer("Weekly = habit. Monthly = reward. Bi-monthly = story.", "calendar")

# =============================================================== 13 CHAMPIONSHIP
sc = S(13)
sc.add_header("The big event")
sc.add_eyebrow("The big event", "trophy")
sc.add_title("Sixteen school champions, not five finalists", highlight="Sixteen school champions",
             sub="A live online final for 48 finalists is how you end up with a cheating scandal and a dead programme.")
half = (CW - 32) / 2
sc.card(M, 300, half, 320, top_stripe=PAL["TF_EMERALD"])
sc.add_twemoji("school", M + 30, 330, 28)
sc.add_text(M + 72, 334, 500, 28, "PHASE 1  ·  SCHOOL HEAT", size_px=13.5, weight="bold", color=PAL["TF_EMERALD"], letter_spacing=2)
sc.add_text(M + 30, 380, half - 60, 40, "Two weeks, asynchronous, in the app.", size_px=24, weight="extrabold")
sc.add_text(M + 30, 428, half - 60, 160,
    "Every student in the class can enter. Same questions, done in their own time inside a two-week window. No timing pressure, no dropped connections, no proctoring — and participation stays near total.",
    size_px=16.5, color=PAL["SLATE"], line_height=1.4)
x2 = M + half + 32
sc.card(x2, 300, half, 320, bg_image="processed/card_emerald_ribbons.jpg", rx=20, stroke=None)
sc.add_twemoji("trophy", x2 + 30, 330, 28)
sc.add_text(x2 + 72, 334, 500, 28, "PHASE 2  ·  CITY FINAL", size_px=13.5, weight="bold", color=PAL["GOLD_BRT"], letter_spacing=2)
sc.add_text(x2 + 30, 380, half - 60, 40, "Sixteen students. One afternoon.", size_px=24, weight="extrabold", color=PAL["WHITE"])
sc.add_text(x2 + 30, 428, half - 60, 160,
    "One champion per school. Live, but sixteen people, all on campus, on good connections, with staff in the room. Genuinely manageable — and it makes a real ceremony worth filming.",
    size_px=16.5, color=PAL["DARK_TEXT"], line_height=1.4)
rows = [["Place", "Reward", "How many"],
        [("school", "School champion"), "Bursary + trophy + name on the school banner + a slot in the final", "16"],
        [("medal", "City winner 1–3"), "Laptop or tablet", "3"],
        [("grad_cap", "City 4–5"), "Fee waiver", "2"],
        [("trophy", "Top school of the term"), "Inter-school trophy and banner", "1"]]
table(sc, M, 650, CW, rows, [440, 1060, 228], rh=50, fsize=16)
sc.add_footer("Sixteen champions means sixteen proud schools — and sixteen ceremonies' worth of photographs.", "party")

# =============================================================== 14 PRIZES
sc = S(14)
sc.add_header("The prize ladder")
sc.add_eyebrow("The prize ladder", "gem")
sc.add_title("Rewarding the middle, not just the peak", highlight="the middle",
             sub="The top 20% are already motivated by grades. The programme lives or dies in the middle.")
rows = [["Band", "Reward", "Cadence", "Why"],
        [("seedling", "Anyone taking part"), "Badge, name on the monthly board, a branded bookmark", "Monthly", "Participation is the goal, so reward the act of participating"],
        [("star", "50%+ (the middle half)"), "Merit bursary — real money off the fee", "Monthly", "The largest group, the biggest family impact, easiest for sponsors to fund"],
        [("glowing_star", "70%+"), "Certificate and merit gear", "Monthly", "Recognition, not material"],
        [("laptop", "Top 1 per year group"), "Laptop", "Annual", "A real trophy — eight winners, not one, which removes the incentive to cheat"],
        [("trophy", "House champion"), "Trophy at the ceremony", "Annual", "The photo opportunity, and the sponsor's logo"]]
table(sc, M, 300, CW, rows, [380, 520, 180, 648], rh=84, fsize=16.5)
sc.card(M, 836, CW, 100, fill=PAL["CORAL_BG"], stroke=PAL["CORAL_BDR"], left_stripe=PAL["CORAL"])
sc.add_twemoji("trash", M + 34, 868, 36)
sc.add_rich_text(M + 100, 846, CW - 140, 80,
    [[("Removed: ", {"weight": "bold", "size_px": 18, "color": PAL["CORAL"]}),
      ("“a branded pen for 40%.” It tells a child they did badly and hands them a consolation prize. That is worse than giving nothing.", {"size_px": 18, "color": PAL["INK"]})]],
    v_align="middle", line_height=1.38)
sc.add_footer("Eight laptops, not one. Spreading the top prize across year groups is what makes cheating pointless.", "laptop")

# =============================================================== 15 MARKETING
sc = S(15)
sc.add_header("Marketing engine")
sc.add_eyebrow("The marketing engine", "megaphone")
sc.add_title("Every printed batch carries its own tracked link", highlight="tracked link",
             sub="This is how the school answers the only question that matters: which notebooks actually worked?")
lw = 1000
sc.rect(M, 300, lw, 150, fill="url(#tf_dark_grad)", rx=20)
sc.add_lucide("qr-code", M + 30, 334, 48, color=PAL["TF_LIME_BRT"])
sc.add_text(M + 100, 326, lw - 130, 40, "https://<host>/t/{batch}/{subject}", size_px=26, family="DejaVu Sans Mono", weight="bold", color=PAL["GOLD_BRT"])
sc.add_text(M + 100, 380, lw - 130, 40, "→  redirects to the code entry screen, and records the scan", size_px=17, color=PAL["DARK_MUTED"])
y = 480
for ic, t, b in [("layers", "One link per print run", "Main campus Physics vs Capital campus Maths are separately attributable from day one."),
                 ("bar-chart-3", "Measured, not guessed", "Scans, participation and average score per batch, per campus, per subject — the real marketing number."),
                 ("coins", "Zero cost", "The tracking is a line of code. There is no extra spend to attribute it.")]:
    feature_card(sc, M, y, lw, 112, t, b, lucide=ic)
    y += 126
px = M + lw + 32; pw = W - M - px
sc.card(px, 300, pw, 556, bg_image="processed/card_stars_ascend.jpg", rx=24, stroke=None)
sc.add_twemoji("satellite", px + 32, 336, 36)
sc.add_text(px + 84, 342, pw - 100, 28, "AND THE BIGGEST LEVER", size_px=13.5, weight="bold", color=PAL["GOLD_BRT"], letter_spacing=2)
sc.add_text(px + 32, 400, pw - 64, 60, "Zero-rated data", size_px=40, weight="extrabold", color=PAL["WHITE"])
sc.add_text(px + 32, 470, pw - 64, 170,
    "Students are on metered mobile data. If the operator zero-rates this host, participation does not improve slightly — it changes order of magnitude.",
    size_px=18.5, weight="medium", color=PAL["WHITE"], line_height=1.42)
sc.add_text(px + 32, 650, pw - 64, 180,
    "A full quiz page already costs 2.5 KB gzipped, so this is a cheap ask with an enormous ceiling. It is the single most valuable thing an affiliated operator can contribute.",
    size_px=16.5, color=PAL["TF_LIME_BRT"], line_height=1.42)
sc.add_footer("report.js prints scans and participation by print batch — the question marketing has never been able to answer.", "bar_chart")

# =============================================================== 16 SPONSORSHIP
sc = S(16)
sc.add_header("Sponsorship")
sc.add_eyebrow("Sponsorship", "handshake")
sc.add_title("Sixteen schools changes the conversation", highlight="changes the conversation",
             sub="Stop selling “logo on a quiz”. Sell the championship.")
half = (CW - 32) / 2
sc.card(M, 300, half, 310, fill=PAL["CORAL_BG"], stroke=PAL["CORAL_BDR"], top_stripe=PAL["CORAL"])
sc.add_twemoji("cross", M + 30, 330, 28)
sc.add_text(M + 72, 334, 500, 28, "WHAT DOES NOT SELL", size_px=13.5, weight="bold", color=PAL["CORAL"], letter_spacing=2)
sc.add_text(M + 30, 380, half - 60, 40, "“Put your logo on our quiz.”", size_px=26, weight="extrabold")
sc.add_text(M + 30, 430, half - 60, 130,
    "This is a marketing sponsorship. Education CSR budgets are earmarked for scholarships, infrastructure and teaching — a completely different budget line at most corporates.",
    size_px=16.5, color=PAL["SLATE"], line_height=1.4)
x2 = M + half + 32
sc.card(x2, 300, half, 310, fill=PAL["TF_MINT"], stroke=PAL["TF_MINT_BDR"], top_stripe=PAL["TF_EMERALD"])
sc.add_twemoji("check", x2 + 30, 330, 28)
sc.add_text(x2 + 72, 334, 500, 28, "WHAT SELLS", size_px=13.5, weight="bold", color=PAL["TF_EMERALD"], letter_spacing=2)
sc.add_text(x2 + 30, 380, half - 60, 40, "“Title sponsor of a 16-school championship.”", size_px=24, weight="extrabold")
sc.add_text(x2 + 30, 430, half - 60, 130,
    "16 campuses, 2,000+ students, a recurring streamed event, trophies, media coverage, and a clean education-access outcome story. That is a headline CSR asset.",
    size_px=16.5, color=PAL["SLATE"], line_height=1.4)
rows = [["Tier", "What they buy", "How easy"],
        [("grad_cap", "Scholarship fund"), "“We underwrite N merit bursaries” — maps perfectly to education-access outcomes", "Easiest"],
        [("laptop", "In-kind prizes"), "Printers, tablets, ISP kit, local vouchers — hugely valuable, almost no cash", "Very easy"],
        [("medal", "Named prize"), "“This month's top scorer wins a [brand] kit”", "Moderate"],
        [("trophy", "Presented by"), "Title sponsor of the biennial championship ceremony", "Moderate"]]
table(sc, M, 640, CW, rows, [400, 1088, 240], rh=56, fsize=16)
sc.add_footer("Rule: run phase 1 with zero sponsors. The bursary model already funds the core. Sponsors are upside, not the business case.", "pushpin")

# =============================================================== 17 PRIVACY
sc = S(17)
sc.add_header("Privacy & safeguarding")
sc.add_eyebrow("Privacy and safeguarding", "lock")
sc.add_title("Built GDPR-K grade, by default", highlight="by default",
             sub="Pakistan has no enacted statute comparable to GDPR or COPPA. That is not a licence to collect loosely.")
items = [("eye-off", "Nothing personal is ever typed in", "No signup form. No name, no father's name, no class, no roll number. The student enters a 6-character printed code.", PAL["TF_EMERALD"]),
         ("shield-check", "Nothing identifying is ever shown", "Public boards show first name and campus only. No guardian names, no student numbers, no photographs.", PAL["TF_EMERALD"]),
         ("file-check", "Every point is traceable", "The points ledger is append-only. A parent can audit every single point their child has ever been awarded.", PAL["TF_EMERALD"]),
         ("phone-call", "A child can always reach an adult", "The front office number is printed inside the front cover, permanently, regardless of what the server is doing.", PAL["GOLD"])]
y = 300
for ic, t, b, col in items:
    sc.card(M, y, CW, 104, left_stripe=col)
    sc.icon_badge(M + 28, y + 26, 52, lucide=ic, bg=PAL["TF_MINT"] if col == PAL["TF_EMERALD"] else PAL["GOLD_BG"], icon_color=col)
    sc.add_text(M + 104, y, 560, 104, t, size_px=21, weight="bold", v_align="middle")
    sc.add_text(M + 690, y, CW - 720, 104, b, size_px=17, color=PAL["SLATE"], v_align="middle", line_height=1.35)
    y += 124
sc.card(M, 806, CW, 100, fill=PAL["GOLD_BG"], stroke=PAL["GOLD_BDR"], left_stripe=PAL["GOLD"])
sc.add_twemoji("clipboard", M + 34, 838, 36)
sc.add_rich_text(M + 100, 816, CW - 140, 80,
    [[("Before launch: ", {"weight": "bold", "size_px": 17.5, "color": PAL["GOLD"]}),
      ("obtain parental consent at enrolment, publish a plain-language privacy notice inside the front cover, and confirm ICT Directorate guidance with local counsel.", {"size_px": 17.5, "color": PAL["INK"]})]],
    v_align="middle", line_height=1.38)
sc.add_footer("Login is rate-limited to 10 tries per 15 minutes per IP; codes are rotatable per student.", "key")

# =============================================================== 18 ROLLOUT
sc = S(18)
sc.add_header("Execution")
sc.add_eyebrow("Execution", "rocket")
sc.add_title("Four phases, and a kill switch at every step", highlight="kill switch")
phases = [("PHASE 1", "4–6 weeks", "seedling", PAL["TF_EMERALD"], "One subject, one chapter, one class. No sponsors, no ceremony, no bursary. The only question: will they scan?"),
          ("PHASE 2", "Months 2–3", "books", PAL["TF_EMERALD"], "All subjects. Weekly house boards. First merit bursary actually paid out. Teacher dashboard switched on."),
          ("PHASE 3", "Months 4–6", "trophy", PAL["GOLD"], "First inter-school championship. Ceremonies, trophies, and the first sponsorship conversation."),
          ("PHASE 4", "Year 2", "rocket", PAL["TF_EMERALD_DK"], "Championship becomes a fixture. Sponsor renews. New campus cohorts onboarded.")]
gap = 28; cw4 = (CW - gap * 3) / 4
sc.bg_els.append(f'<line x1="{M+40}" y1="256" x2="{W-M-40}" y2="256" stroke="{PAL["TF_MINT_BDR"]}" stroke-width="3"/>')
for i, (p, dur, em, col, b) in enumerate(phases):
    x = M + i * (cw4 + gap)
    sc.bg_els.append(f'<circle cx="{x+40}" cy="256" r="12" fill="{col}" stroke="{PAL["CANVAS"]}" stroke-width="4"/>')
    sc.card(x, 290, cw4, 410, top_stripe=col)
    sc.icon_badge(x + 28, 322, 60, emoji=em, bg=PAL["CANVAS_ALT"], rx=16)
    sc.add_text(x + 104, 326, cw4 - 130, 24, p, size_px=13, weight="bold", color=col, letter_spacing=2)
    sc.add_text(x + 104, 352, cw4 - 130, 36, dur, size_px=26, weight="extrabold")
    sc.add_text(x + 28, 410, cw4 - 56, 240, b, size_px=17, color=PAL["SLATE"], line_height=1.42)
sc.rect(M, 736, CW, 150, fill="url(#tf_dark_grad)", rx=22)
sc.add_twemoji("stop", M + 34, 790, 44)
sc.add_rich_text(M + 110, 752, CW - 150, 120,
    [[("The kill switch. ", {"weight": "extrabold", "size_px": 20, "color": PAL["GOLD_BRT"]}),
      ("If monthly participation is below 50% at the end of phase 1, stop and fix it. Do not scale a weak programme across 16 campuses — that is how a good idea dies of bad management rather than bad design.", {"size_px": 19, "color": PAL["WHITE"]})]],
    v_align="middle", line_height=1.4)
sc.add_footer("Phase 1 needs one volunteer science teacher — not the most eager head of department.", "teacher")

# =============================================================== 19 METRICS
sc = S(19)
sc.add_header("Measurement")
sc.add_eyebrow("Measurement", "target")
sc.add_title("One number decides whether this lives", highlight="One number",
             sub="Track it weekly. Everything else is diagnostic.")
sc.rect(M, 300, CW, 170, fill="url(#tf_dark_grad)", rx=22)
sc.add_twemoji("bar_chart", M + 34, 330, 36)
sc.add_text(M + 86, 336, 700, 26, "MONTHLY PARTICIPATION", size_px=13.5, weight="bold", color=PAL["GOLD_BRT"], letter_spacing=2.2)
sc.add_text(M + 34, 376, 760, 80, "Share of enrolled students who opened at least one chapter this month", size_px=20, weight="medium", color=PAL["DARK_TEXT"], line_height=1.35)
# gauge
gx = M + 900
sc.rect(gx, 362, 720, 22, fill="rgba(255,255,255,0.10)", rx=11)
sc.rect(gx, 362, 180, 22, fill=PAL["CORAL_BRT"], rx=11)
sc.rect(gx + 180, 362, 180, 22, fill=PAL["GOLD_BRT"], rx=0)
sc.rect(gx + 360, 362, 360, 22, fill=PAL["TF_LIME_BRT"], rx=11)
sc.add_text(gx, 396, 180, 50, "Below 25%\nAt risk — stop and fix", size_px=14, weight="bold", color=PAL["CORAL_BRT"], line_height=1.3)
sc.add_text(gx + 360, 396, 360, 50, "Above 50%\nOn track — scale", size_px=14, weight="bold", color=PAL["TF_LIME_BRT"], align="right", line_height=1.3)
sc.add_text(gx, 324, 720, 30, "0%                                                     25%                                             50%                                                                            100%",
            size_px=12, weight="semibold", color=PAL["DARK_MUTED"])
rows = [["What we also watch", "Why it matters", "Who acts on it"],
        [("pushpin", "Participation rate per campus"), "Which campuses are engaged, and which need a teacher's nudge", "Campus principal"],
        [("megaphone", "Scans per printed batch"), "Which notebook print run actually worked — the marketing number", "Marketing / HQ"],
        [("books", "Average score per chapter"), "Which chapters the cohort actually struggles with", "Subject teacher"],
        [("chart_up", "Share of students reaching 50%+"), "Whether the programme is lifting the middle, not just the top", "Head of school"],
        [("money_bag", "Points redeemed as bursary"), "Actual cost to the school, against the 0.5–1% cap", "Finance"]]
table(sc, M, 506, CW, rows, [520, 880, 328], rh=64, fsize=16.5)
sc.add_footer("The teacher-facing report is not a by-product. It is the reason teachers support the programme instead of quietly resenting it.", "teacher")

# =============================================================== 20 COST
sc = S(20)
sc.add_header("What it costs")
sc.add_eyebrow("What it costs", "coin")
sc.add_title("Almost nothing to start", highlight="Almost nothing")
rows = [["Item", "Cost", "Note"],
        [("mobile", "QR code printed on the notebook cover"), "~PKR 0", "You are already printing these. This is a design change."],
        [("key", "Access code inside the front cover"), "~PKR 0", "Printed by the school alongside the class list."],
        [("laptop", "The application"), "PKR 0", "No licences, no hosting minimum, no vendor. Runs on one small server."],
        [("school", "Deployment to 16 campuses"), "Minimal", "Server-side software update, not a campus-by-campus installation."],
        [("grad_cap", "Merit bursary pool"), "0.5–1% of fee revenue", "Capped, published, and the real cost. Budget it deliberately."],
        [("trophy", "Inter-school championship"), "Per-event", "Sponsorship-funded. Do not run phase 1 on sponsor money."]]
table(sc, M, 270, CW, rows, [560, 300, 868], rh=62, fsize=16.5)
gap = 24; sw = (CW - gap * 2) / 3
for i, (big, small, em, col) in enumerate([("0", "new vendors or licences", "check", PAL["TF_EMERALD"]),
                                           ("16", "campuses from one server update", "school", PAL["TF_EMERALD"]),
                                           ("≤1%", "of fee revenue — the entire real cost", "coin", PAL["GOLD"])]):
    stat_card(sc, M + i * (sw + gap), 724, sw, 150, big, small, em, col)
# compress stat cards (shorter): adjust text positions by drawing over? Simpler: keep standard.
sc.add_footer("The expensive part is not software — it is teacher adoption, solved by giving teachers a live picture of their class's weak chapters.", "bulb")

# =============================================================== 21 ASKS
sc = S(21, dark=True, bg_image="processed/waves_dark_bg.jpg")
sc.add_header("What we need")
sc.add_eyebrow("What we need", "handshake", y=100)
sc.add_title("Three decisions", y=146, sub="Nothing here needs a new budget line. All three are policy choices.")
asks = [("01", "Name a pilot", "clipboard", "One class, one subject, one campus. Six weeks. A science teacher who volunteers, not the most eager head of department."),
        ("02", "Agree the framing", "scales", "“Merit bursary”, never “earn your own fee”. And quiz points never decide Head Boy, monitors or prefects — that stays exactly as it is today."),
        ("03", "Open the operator conversation", "satellite", "Zero-rated data on the quiz host, and a first look at sponsoring the inter-school championship. Both are worth more than the software.")]
y = 300
for num, t, em, b in asks:
    sc.rect(M, y, CW, 150, fill="rgba(14,71,47,0.78)", stroke=PAL["TF_DARK_LINE"], rx=24)
    sc.rect(M, y, 8, 150, fill=PAL["GOLD_BRT"], rx=4)
    sc.add_text(M + 40, y, 110, 150, num, size_px=72, family="Bebas Neue", color=PAL["GOLD_BRT"], v_align="middle")
    sc.add_twemoji(em, M + 160, y + 55, 40)
    sc.add_text(M + 224, y, 500, 150, t, size_px=28, weight="extrabold", color=PAL["WHITE"], v_align="middle", line_height=1.15)
    sc.add_text(M + 760, y, CW - 800, 150, b, size_px=18, color=PAL["DARK_TEXT"], v_align="middle", line_height=1.42)
    y += 170
sc.add_twemoji("sparkles", M, 830, 28)
sc.add_text(M + 40, 828, CW, 40, "Total cost to pilot: the price of six weeks of one teacher's goodwill.",
            size_px=20, weight="medium", color=PAL["GOLD_BRT"], italic=True)
sc.add_footer("All three can be decided in this meeting.", "check")

# =============================================================== 22 CLOSING
sc = S(22, dark=True, count=False, bg_image="processed/closing_dark_bg.jpg")
sc.bg_els.append(f'<rect x="0" y="0" width="{W}" height="8" fill="url(#tf_brand_grad)"/>')
sc.add_image("tf_logo_dark.png", M, 64, 420, 54)
sc.add_eyebrow("The point", "target", y=280)
sc.add_rich_text(M, 340, 1000, 300,
    [[("It is not a quiz app.\n", {"size_px": 78, "weight": "extrabold", "color": PAL["WHITE"]}),
      ("It is a reason to\nopen the notebook.", {"size_px": 60, "weight": "extrabold", "color": PAL["TF_LIME_BRT"]})]],
    line_height=1.08)
sc.bg_els.append(f'<rect x="{M}" y="700" width="160" height="6" rx="3" fill="url(#tf_gold_grad)"/>')
sc.add_text(M, 736, 900, 130,
    "Every other school initiative asks a student to do something extra. This one pays them for what they were already doing — which is why it will still be running in March.",
    size_px=21, color=PAL["DARK_TEXT"], line_height=1.45)
sc.add_text(M, H - 90, 900, 30, "TELECOM FOUNDATION EDUCATION SYSTEM  ·  TEFOS QUIZ", size_px=13, weight="bold", color=PAL["DARK_MUTED"], letter_spacing=2.2)
sc.add_text(M, H - 60, 900, 30, "Thank you  ·  Questions welcome", size_px=15, weight="medium", color=PAL["TF_LIME_BRT"])
sc.add_text(W - M - 500, H - 70, 500, 30, "Transforming Communities", size_px=15, weight="medium", color=PAL["TF_LIME_BRT"], align="right", italic=True)

# =============================================================== EXPORT
assert len(slides) == 22, len(slides)
export_deck(slides,
            pdf_paths=[os.path.join(HERE, "TEFOS-Quiz-Proposal-Designed.pdf")],
            pptx_paths=[os.path.join(HERE, "TEFOS-Quiz-Proposal-Designed.pptx")])
print("Built 22 slides → TEFOS-Quiz-Proposal-Designed.pdf / .pptx / slides/*.png")
