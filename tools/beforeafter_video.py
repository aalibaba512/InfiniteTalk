#!/usr/bin/env python3
"""
Before/After reveal video builder.

Reads a PDF (or folders of images) containing BEFORE | AFTER pairs laid out
side by side, splits each pair, and renders a video where the BEFORE image is
shown first, then wipes away to reveal the AFTER image ("this was before ...
and now it looks like this").

Pipeline
    PDF -> pages -> (before, after) pairs -> wipe-reveal video -> .mp4

Modes
    --probe    extract + split only; write JPGs + JSON report, no video
    default    extract + render the video

Examples
    python3 tools/beforeafter_video.py --pdf deck.pdf --probe --inspect out/pairs
    python3 tools/beforeafter_video.py --pdf deck.pdf --out out/reveal.mp4
    python3 tools/beforeafter_video.py --pdf deck.pdf --wipe lr --hold-before 2.5
"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    import pymupdf  # PyMuPDF >= 1.24
except ImportError:  # pragma: no cover
    import fitz as pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def find_ffmpeg() -> str:
    for c in (os.path.join(REPO, ".toolkit", "bin", "ffmpeg"), shutil.which("ffmpeg")):
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    sys.exit("ffmpeg not found (install it, or drop a static build at .toolkit/bin/ffmpeg)")


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB"))


def save_jpg(arr, path, quality=95):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    Image.fromarray(arr).save(path, "JPEG", quality=quality, subsampling=0, optimize=True)


def center_crop_to_aspect(img: Image.Image, aspect: float) -> Image.Image:
    """Center-crop a PIL image to the given width/height aspect ratio."""
    w, h = img.size
    cur = w / h
    if abs(cur - aspect) < 1e-3:
        return img
    if cur > aspect:                      # too wide -> trim sides
        nw = max(1, int(round(h * aspect)))
        x = (w - nw) // 2
        return img.crop((x, 0, x + nw, h))
    nh = max(1, int(round(w / aspect)))   # too tall -> trim top/bottom
    y = (h - nh) // 2
    return img.crop((0, y, w, y + nh))


def upscale_to(arr, target_h, max_scale=2.5):
    h, w = arr.shape[:2]
    s = min(target_h / max(h, 1), max_scale)
    if s <= 1.0:
        return arr
    return np.asarray(Image.fromarray(arr).resize((int(w * s), int(h * s)), Image.LANCZOS))


# --------------------------------------------------------------------------
# page geometry: find the content, find the gutter, crop the margins
# --------------------------------------------------------------------------


def content_mask(arr, tol=14):
    """
    Boolean mask of pixels that differ from the page background.

    The background is estimated from the border frame of the image. This is what
    lets us find real photo edges on a slide with large white margins.
    """
    h, w = arr.shape[:2]
    b = max(2, min(h, w) // 100)
    edges = np.concatenate(
        [
            arr[:b, :, :].reshape(-1, 3),
            arr[-b:, :, :].reshape(-1, 3),
            arr[:, :b, :].reshape(-1, 3),
            arr[:, -b:, :].reshape(-1, 3),
        ]
    )
    bg = np.median(edges, axis=0)
    diff = np.abs(arr.astype(np.float32) - bg).max(axis=2)
    return diff > tol, bg


def content_bbox(mask, min_frac=0.01):
    """Tight bbox of content, ignoring stray specks (line needs min share)."""
    h, w = mask.shape
    rows = mask.sum(axis=1) > max(2, int(w * min_frac))
    cols = mask.sum(axis=0) > max(2, int(h * min_frac))
    if not rows.any() or not cols.any():
        return None
    ys, xs = np.where(rows)[0], np.where(cols)[0]
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def content_gaps(mask, min_frac=0.004, min_width=2):
    """Empty (background-only) vertical column runs inside the content, widest first."""
    h, w = mask.shape
    has = mask.sum(axis=0) > max(2, int(h * min_frac))
    gaps, s = [], None
    for x in range(w):
        if not has[x] and s is None:
            s = x
        elif has[x] and s is not None:
            if x - s >= min_width:
                gaps.append((s, x))
            s = None
    if s is not None and w - s >= min_width:
        gaps.append((s, w))
    gaps.sort(key=lambda g: g[1] - g[0], reverse=True)
    return gaps


def runs_of(flags, min_len=10):
    """Contiguous True runs in a boolean array, as (start, end) half-open."""
    out, s = [], None
    for i, f in enumerate(flags):
        if f and s is None:
            s = i
        elif not f and s is not None:
            if i - s >= min_len:
                out.append((s, i))
            s = None
    if s is not None and len(flags) - s >= min_len:
        out.append((s, len(flags)))
    return out


def find_photo_boxes(arr, tol=14, row_frac=0.30, col_frac=0.45, min_len=12):
    """
    Locate the photo blocks on a page as (x0, y0, x1, y1) boxes.

    A photo row/column is *solidly* covered by non-background pixels, which is
    what separates a photo from headline text: a text row only touches a few
    percent of the width, a photo row touches nearly all of it. This is why a
    coverage threshold is used rather than "any non-white pixel".
    """
    mask, bg = content_mask(arr, tol=tol)
    h, w = mask.shape
    rowcov = mask.sum(axis=1) / max(w, 1)

    boxes = []
    for y0, y1 in runs_of(rowcov > row_frac, min_len):
        within = mask[y0:y1]
        colcov = within.sum(axis=0) / max(y1 - y0, 1)
        for x0, x1 in runs_of(colcov > col_frac, min_len):
            boxes.append((x0, y0, x1, y1))
    return boxes


def crop_box(arr, box, pad=2):
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = box
    return arr[max(0, y0 - pad) : min(h, y1 + pad), max(0, x0 - pad) : min(w, x1 + pad)]


def cluster_rows(boxes, min_overlap=0.35):
    """
    Group photo boxes into horizontal rows by vertical overlap.

    One page can hold several before/after pairs stacked vertically, so the
    rows are what actually map to pairs.
    """
    rows = []
    for b in sorted(boxes, key=lambda b: b[1]):
        for row in rows:
            y0 = min(r[1] for r in row)
            y1 = max(r[3] for r in row)
            ov = min(y1, b[3]) - max(y0, b[1])
            span = min(y1 - y0, b[3] - b[1])
            if span > 0 and ov / span >= min_overlap:
                row.append(b)
                break
        else:
            rows.append([b])
    for row in rows:
        row.sort(key=lambda b: b[0])
    rows.sort(key=lambda row: min(b[1] for b in row))
    return rows


def pairs_from_page(arr, tol=14):
    """
    All (before, after) crops on one page render, top row first.

    Each row of two side-by-side photo blocks is one pair; both halves are cut
    to a shared vertical band so the wipe lines up exactly.
    """
    h, w = arr.shape[:2]
    out = []

    for row in cluster_rows(find_photo_boxes(arr, tol=tol)):
        if len(row) != 2:
            continue
        (lx0, ly0, lx1, ly1), (rx0, ry0, rx1, ry1) = row
        y0, y1 = min(ly0, ry0), max(ly1, ry1)
        left = crop_box(arr, (lx0, y0, lx1, y1))
        right = crop_box(arr, (rx0, y0, rx1, y1))
        if left.size and right.size:
            out.append((left, right))

    if out:
        return out

    # ---- fallback: no two side-by-side blocks; split at the widest gutter ---
    mask, _ = content_mask(arr, tol=tol)
    split = None
    for s, e in content_gaps(mask):
        c = (s + e) // 2
        if 0.20 * w <= c <= 0.80 * w:
            split = c
            break
    if split is None:
        bb = content_bbox(mask)
        split = (bb[0] + bb[2]) // 2 if bb else w // 2
    return [(arr[:, :split], arr[:, split:])]


def split_page(arr, tol=14):
    """First before/after pair on the page (kept for single-pair pages)."""
    return pairs_from_page(arr, tol=tol)[0]


# --------------------------------------------------------------------------
# PDF extraction
# --------------------------------------------------------------------------


@dataclass
class Pair:
    index: int
    page: int
    before_jpg: str
    after_jpg: str
    before_size: tuple
    after_size: tuple
    method: str
    split_x: int = 0


def _native_image(doc, xref):
    d = doc.extract_image(xref)
    return np.asarray(Image.open(io.BytesIO(d["image"])).convert("RGB"))


def _cluster_rows(items, tol_frac=0.5):
    """
    Group (rect, xref) items into visual rows by vertical centre.
    Returns a list of rows, each sorted left-to-right.
    """
    if not items:
        return []
    hs = sorted(r.height for r, _ in items)
    tol = max(8.0, hs[len(hs) // 2] * tol_frac)
    rows = []
    for rect, xref in sorted(items, key=lambda t: t[0].y0 + t[0].height / 2):
        cy = rect.y0 + rect.height / 2
        for row in rows:
            rcy = sum(r.y0 + r.height / 2 for r, _ in row) / len(row)
            if abs(cy - rcy) <= tol:
                row.append((rect, xref))
                break
        else:
            rows.append([(rect, xref)])
    for row in rows:
        row.sort(key=lambda t: t[0].x0)
    return rows


def extract_pairs_from_pdf(pdf_path, dpi=220, inspect_dir=None, jpg_quality=95, pages=None):
    """
    Pull one BEFORE/AFTER pair per visual row of two side-by-side images.

    Native embedded images are used when a row holds exactly two comparable
    photos (keeps full original resolution). Otherwise the page is rendered at
    `dpi` and split at the whitespace gutter.
    """
    doc = pymupdf.open(pdf_path)
    pairs, notes = [], []
    want = set(pages) if pages else None

    for pno, page in enumerate(doc, start=1):
        if want and pno not in want:
            continue

        produced = 0

        # ---- 1) native embedded images ----------------------------------
        items = []
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            for r in rects:
                if r.width > 60 and r.height > 60:
                    items.append((r, xref))

        for row in _cluster_rows(items):
            if len(row) != 2:
                continue
            (r0, x0), (r1, x1) = row
            if r0.intersects(r1):
                continue
            a0, a1 = r0.width * r0.height, r1.width * r1.height
            if not (0.4 < a0 / max(a1, 1) < 2.5):
                continue
            try:
                before, after = _native_image(doc, x0), _native_image(doc, x1)
            except Exception as e:
                notes.append(f"page {pno}: native extract failed ({e}); falling back")
                break
            pairs.append(_record(pairs, pno, before, after, "native-image", inspect_dir, jpg_quality))
            produced += 1

        if produced:
            continue

        # ---- 2) rendered page, split at the gutter -----------------------
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        arr = np.asarray(
            Image.frombytes(
                "RGBA" if pix.n == 4 else ("RGB" if pix.n == 3 else "L"),
                (pix.width, pix.height),
                pix.samples,
            ).convert("RGB")
        )
        found = pairs_from_page(arr)
        if not found:
            notes.append(f"page {pno}: no before/after pair found, skipped")
            continue
        for before, after in found:
            if before.size == 0 or after.size == 0:
                continue
            pairs.append(_record(pairs, pno, before, after, "page-render", inspect_dir, jpg_quality))

    doc.close()
    return pairs, notes


def _record(pairs, page, before, after, method, inspect_dir, quality, split_x=0):
    idx = len(pairs) + 1
    before = upscale_to(before, 900)
    after = upscale_to(after, 900)
    bp = ap = ""
    if inspect_dir:
        bp = os.path.join(inspect_dir, f"pair{idx:02d}_before.jpg")
        ap = os.path.join(inspect_dir, f"pair{idx:02d}_after.jpg")
        save_jpg(before, bp, quality)
        save_jpg(after, ap, quality)
    return Pair(
        index=idx,
        page=page,
        before_jpg=bp,
        after_jpg=ap,
        before_size=(int(before.shape[1]), int(before.shape[0])),
        after_size=(int(after.shape[1]), int(after.shape[0])),
        method=method,
        split_x=int(split_x),
    )


# --------------------------------------------------------------------------
# frame composition
# --------------------------------------------------------------------------


class Canvas:
    """A source photo prepared as a video frame: blurred cover background +
    the photo fitted inside, optionally centre-cropped to a common aspect."""

    def __init__(self, arr, W, H, aspect=None, blur=48, darken=0.58, pad_frac=0.93):
        img = Image.fromarray(arr)
        if aspect:
            img = center_crop_to_aspect(img, aspect)

        sw, sh = img.size
        bw, bh = W / sw, H / sh
        s = max(bw, bh)
        bg = img.resize((max(W, int(sw * s) + 1), max(H, int(sh * s) + 1)), Image.LANCZOS)
        bx, by = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(blur))
        bg = Image.fromarray((np.asarray(bg).astype(np.float32) * darken).astype(np.uint8))

        s = min(W * pad_frac / sw, H * pad_frac / sh)
        fg = img.resize((max(1, int(sw * s)), max(1, int(sh * s))), Image.LANCZOS)

        self.base = bg.copy()
        ox, oy = (W - fg.width) // 2, (H - fg.height) // 2
        self.base.paste(fg, (ox, oy))
        self.fg_box = (ox, oy, fg.width, fg.height)

    def arr(self):
        return np.asarray(self.base)


def ken_burns(arr, t, z0=1.0, z1=1.06, pan=(0.0, 0.0)):
    """Zoom about the centre with optional pan; returns the full-size frame."""
    h, w = arr.shape[:2]
    z = z0 + (z1 - z0) * max(0.0, min(1.0, t))
    if abs(z - 1.0) < 1e-4:
        return arr.copy()
    cw, ch = max(2, int(w / z)), max(2, int(h / z))
    cx = int((w - cw) / 2 + pan[0] * (w - cw) / 2)
    cy = int((h - ch) / 2 + pan[1] * (h - ch) / 2)
    cx, cy = max(0, min(cx, w - cw)), max(0, min(cy, h - ch))
    # np.array (not asarray): PIL-backed buffers are read-only and frames get
    # drawn on in place afterwards.
    return np.array(
        Image.fromarray(arr[cy : cy + ch, cx : cx + cw]).resize((w, h), Image.BILINEAR)
    )


class Stamp:
    """
    A pre-rendered static overlay (badge, caption).

    Only the overlay's own bounding box is blended into each frame, so a small
    badge costs a small badge's worth of work rather than a full 1080p pass.
    """

    __slots__ = ("rgb", "alpha", "y0", "y1", "x0", "x1")

    def __init__(self, rgb, alpha):
        self.rgb, self.alpha = rgb, alpha
        ys, xs = np.where(alpha[:, :, 0] > 0.004)
        if ys.size == 0:
            self.y0 = self.y1 = self.x0 = self.x1 = 0
            self.rgb = self.alpha = None
            return
        self.y0, self.y1 = int(ys.min()), int(ys.max()) + 1
        self.x0, self.x1 = int(xs.min()), int(xs.max()) + 1
        self.rgb = rgb[self.y0 : self.y1, self.x0 : self.x1]
        self.alpha = alpha[self.y0 : self.y1, self.x0 : self.x1]

    def apply(self, frame):
        if self.rgb is None:
            return frame
        y0, y1, x0, x1 = self.y0, self.y1, self.x0, self.x1
        sub = frame[y0:y1, x0:x1].astype(np.float32)
        a = self.alpha
        frame[y0:y1, x0:x1] = (sub * (1 - a) + self.rgb * a).astype(np.uint8)
        return frame


def badge(W, H, text, size, color, where="top-left", alpha=185):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(FONT_BOLD, size)
    tb = d.textbbox((0, 0), text, font=f)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    px, py = int(size * 0.8), int(size * 0.45)
    bw, bh = tw + 2 * px, th + 2 * py
    m = int(size * 0.95)
    x = m if where.endswith("left") else W - bw - m
    y = m if where.startswith("top") else H - bh - m
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=bh // 2, fill=(0, 0, 0, alpha))
    d.rounded_rectangle(
        [x, y, x + bw, y + bh], radius=bh // 2,
        outline=(255, 255, 255, 80), width=max(2, size // 26),
    )
    d.text((x + px - tb[0], y + py - tb[1]), text, font=f, fill=color)
    a = np.asarray(ov).astype(np.float32)
    return Stamp(a[:, :, :3], a[:, :, 3:4] / 255.0)


def progress_bar(frame, frac, h=6):
    """Write the progress bar straight into the bottom rows of the frame."""
    H, W = frame.shape[:2]
    frac = max(0.0, min(1.0, frac))
    y = H - h
    strip = frame[y:H]
    strip[:] = (strip.astype(np.uint16) * 0 + 55).astype(np.uint8)  # dim base
    cut = int(W * frac)
    if cut > 0:
        frame[y:H, :cut] = (235, 235, 235)
    return frame


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def draw_divider(frame, pos, box, vertical=True, width=4, knob=True):
    """Sweeping divider line + knob, drawn only across the photo box."""
    H, W = frame.shape[:2]
    bx, by, bw, bh = box
    img = Image.fromarray(frame)
    d = ImageDraw.Draw(img, "RGBA")

    if vertical:
        x = max(bx, min(int(pos), bx + bw))
        d.rectangle([x - width // 2, by, x - width // 2 + width, by + bh], fill=(255, 255, 255, 250))
        d.rectangle([x + width // 2, by, x + width // 2 + 8, by + bh], fill=(0, 0, 0, 70))
        if knob:
            r = max(13, int(min(W, H) * 0.017))
            cy = by + bh // 2
            d.ellipse([x - r, cy - r, x + r, cy + r], fill=(255, 255, 255, 240), outline=(0, 0, 0, 55), width=2)
            s = max(4, r // 2)
            d.polygon([(x - s, cy), (x - s - s + 2, cy - s), (x - s - s + 2, cy + s)], fill=(45, 45, 45, 230))
            d.polygon([(x + s, cy), (x + s + s - 2, cy - s), (x + s + s - 2, cy + s)], fill=(45, 45, 45, 230))
    else:
        y = max(by, min(int(pos), by + bh))
        d.rectangle([bx, y - width // 2, bx + bw, y - width // 2 + width], fill=(255, 255, 255, 250))
        d.rectangle([bx, y + width // 2, bx + bw, y + width // 2 + 8], fill=(0, 0, 0, 70))
        if knob:
            r = max(13, int(min(W, H) * 0.017))
            cx = bx + bw // 2
            d.ellipse([cx - r, y - r, cx + r, y + r], fill=(255, 255, 255, 240), outline=(0, 0, 0, 55), width=2)
    return np.array(img)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def build_timeline(n, hold_b, wipe, hold_a, xfade, fps):
    segs = []
    for i in range(n):
        segs.append(("before", i, max(1, int(round(hold_b * fps)))))
        segs.append(("wipe", i, max(2, int(round(wipe * fps)))))
        segs.append(("after", i, max(1, int(round(hold_a * fps)))))
        if i < n - 1 and xfade > 0:
            segs.append(("xfade", i, max(1, int(round(xfade * fps)))))
    return segs


def render(pairs, args):
    W, H, fps = args.width, args.height, args.fps
    ffmpeg = find_ffmpeg()
    zmid = args.zoom / 3.0
    zend = args.zoom

    before_imgs = [load_rgb(p) for p in args.before_list]
    after_imgs = [load_rgb(p) for p in args.after_list]

    canvases = []
    for b, a in zip(before_imgs, after_imgs):
        if args.aspect == "common":
            keep = 0.75  # don't crop more than 25% of the area away
            raw = (b.shape[1] / b.shape[0] + a.shape[1] / a.shape[0]) / 2
            bh, bw = b.shape[:2]
            ah, aw = a.shape[:2]
            aspect = raw
            # if the common aspect would waste too much of either image, skip it
            for (hh, ww) in ((bh, bw), (ah, aw)):
                ar = ww / hh
                if ar > aspect:
                    frac = (hh * aspect) / ww
                else:
                    frac = (ww / aspect) / hh
                if frac < keep:
                    aspect = None
                    break
        else:
            aspect = None
        canvases.append((Canvas(b, W, H, aspect=aspect), Canvas(a, W, H, aspect=aspect)))

    lbl_b = badge(W, H, args.label_before, int(H * 0.048), (255, 255, 255), "top-left") if not args.no_labels else None
    lbl_a = badge(W, H, args.label_after, int(H * 0.048), (150, 255, 170), "top-left") if not args.no_labels else None

    ttl = badge(W, H, args.title, int(H * 0.042), (255, 255, 255), "bottom-left", alpha=150) if args.title else None

    segs = build_timeline(len(pairs), args.hold_before, args.wipe_dur, args.hold_after, args.transition, fps)
    total = sum(s[2] for s in segs)

    tmp = os.path.join(tempfile.gettempdir(), "ba_silent.mp4")
    proc = subprocess.Popen(
        [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp,
        ],
        stdin=subprocess.PIPE,
    )

    done = 0
    for kind, i, n in segs:
        cb, ca = canvases[i]
        bb, ba = cb.arr(), ca.arr()
        box = cb.fg_box
        vertical = args.wipe in ("lr", "rl")

        for k in range(n):
            t = k / max(1, n - 1)

            if kind == "before":
                f = ken_burns(bb, t, 1.0, 1.0 + zmid, pan=(0.0, -0.03))
                if lbl_b:
                    lbl_b.apply(f)

            elif kind == "after":
                f = ken_burns(ba, t, 1.0 + zmid, 1.0 + zend, pan=(0.0, 0.03))
                if lbl_a:
                    lbl_a.apply(f)

            elif kind == "wipe":
                e = ease(t)
                fb = ken_burns(bb, 0.5, 1.0 + zmid, 1.0 + zmid)
                fa = ken_burns(ba, 0.5, 1.0 + zmid, 1.0 + zmid)
                f = np.array(fa, copy=True)
                bx, by, bw, bh = box
                if args.wipe == "lr":
                    x = bx + int(round(e * bw))
                    f[:, x:] = fb[:, x:]
                    f = draw_divider(f, x, box, True, width=max(3, W // 500), knob=not args.no_knob)
                elif args.wipe == "rl":
                    x = bx + bw - int(round(e * bw))
                    f[:, :x] = fb[:, :x]
                    f = draw_divider(f, x, box, True, width=max(3, W // 500), knob=not args.no_knob)
                elif args.wipe == "tb":
                    y = by + int(round(e * bh))
                    f[y:, :] = fb[y:, :]
                    f = draw_divider(f, y, box, False, width=max(3, W // 500), knob=not args.no_knob)
                else:  # bt
                    y = by + bh - int(round(e * bh))
                    f[:y, :] = fb[:y, :]
                    f = draw_divider(f, y, box, False, width=max(3, W // 500), knob=not args.no_knob)
                lab = lbl_b if e < 0.55 else lbl_a
                if lab:
                    lab.apply(f)

            else:  # crossfade into the next pair
                fa = ken_burns(ba, 1.0, 1.0 + zend, 1.0 + zend)
                if lbl_a:
                    lbl_a.apply(fa)
                nb = canvases[i + 1][0].arr()
                fb = ken_burns(nb, 0.0, 1.0, 1.0)
                if lbl_b:
                    lbl_b.apply(fb)
                f = (fa.astype(np.float32) * (1 - t) + fb.astype(np.float32) * t).astype(np.uint8)

            if ttl:
                ttl.apply(f)
            progress_bar(f, (done + k) / max(1, total - 1))

            proc.stdin.write(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
            done += 1

    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed while encoding frames")
    return tmp, total, done


def mux(video, audio, out):
    subprocess.run(
        [find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-i", audio,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
        check=True,
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Before/After reveal video from a PDF or image folders.")
    ap.add_argument("--pdf")
    ap.add_argument("--before-dir")
    ap.add_argument("--after-dir")
    ap.add_argument("--dpi", type=int, default=220, help="page render DPI (fallback path)")
    ap.add_argument("--pages", help="only these pages, e.g. 1,3,5-8")

    ap.add_argument("--out", default="out/before_after.mp4")
    ap.add_argument("--inspect", help="dump extracted pairs here as JPG")
    ap.add_argument("--probe", action="store_true", help="extract only, no video")
    ap.add_argument("--report")

    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--zoom", type=float, default=0.06, help="total Ken Burns zoom (0 = none)")
    ap.add_argument("--aspect", choices=["common", "none"], default="common",
                    help="force both halves to one aspect so the wipe aligns")
    ap.add_argument("--wipe", choices=["lr", "rl", "tb", "bt"], default="lr")
    ap.add_argument("--label-before", default="BEFORE")
    ap.add_argument("--label-after", default="AFTER")
    ap.add_argument("--title", help="caption pinned bottom-left for the whole video")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--no-knob", action="store_true", help="plain divider line, no handle")

    ap.add_argument("--hold-before", type=float, default=2.2)
    ap.add_argument("--wipe-dur", type=float, default=1.1, dest="wipe_dur")
    ap.add_argument("--hold-after", type=float, default=2.2)
    ap.add_argument("--transition", type=float, default=0.45, help="crossfade between pairs")
    ap.add_argument("--audio", help="optional narration/music to mux in")

    args = ap.parse_args()

    pages = None
    if args.pages:
        pages = []
        for part in args.pages.split(","):
            if "-" in part:
                a, b = part.split("-")
                pages += list(range(int(a), int(b) + 1))
            else:
                pages.append(int(part))

    # ---- gather --------------------------------------------------------
    # Frames are read back from disk, so we always need the pairs written out.
    dump_dir = args.inspect
    if dump_dir is None and not args.probe:
        dump_dir = os.path.join(tempfile.gettempdir(), "ba_pairs")
    if dump_dir:
        os.makedirs(dump_dir, exist_ok=True)

    if args.pdf:
        pairs, notes = extract_pairs_from_pdf(
            args.pdf, dpi=args.dpi, inspect_dir=dump_dir, pages=pages
        )
    elif args.before_dir and args.after_dir:
        pick = lambda d: sorted(f for f in os.listdir(d) if f.lower().endswith(IMG_EXT))
        bs, as_ = pick(args.before_dir), pick(args.after_dir)
        if len(bs) != len(as_):
            sys.exit(f"before={len(bs)} after={len(as_)} — counts must match")
        pairs, notes = [], []
        for i, (bf, af) in enumerate(zip(bs, as_), 1):
            bp, ap2 = os.path.join(args.before_dir, bf), os.path.join(args.after_dir, af)
            b, a = load_rgb(bp), load_rgb(ap2)
            if dump_dir:
                save_jpg(b, os.path.join(dump_dir, f"pair{i:02d}_before.jpg"))
                save_jpg(a, os.path.join(dump_dir, f"pair{i:02d}_after.jpg"))
            pairs.append(Pair(i, i, bp, ap2, (b.shape[1], b.shape[0]), (a.shape[1], a.shape[0]), "folder"))
    else:
        sys.exit("give me --pdf, or --before-dir with --after-dir")

    if not pairs:
        sys.exit("No before/after pairs found — check the PDF layout (see --probe --inspect).")

    print(f"Found {len(pairs)} pair(s):")
    for p in pairs:
        print(f"  [{p.index:2d}] page {p.page:<3d} before {p.before_size}  after {p.after_size}  ({p.method})")
    for n in notes:
        print("  note:", n)

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w") as fh:
            json.dump({
                "source": args.pdf or f"{args.before_dir} + {args.after_dir}",
                "pairs": [asdict(p) for p in pairs],
                "notes": notes,
                "render": {
                    "size": [args.width, args.height], "fps": args.fps, "wipe": args.wipe,
                    "hold_before": args.hold_before, "wipe_dur": args.wipe_dur,
                    "hold_after": args.hold_after, "transition": args.transition,
                    "zoom": args.zoom, "aspect": args.aspect,
                },
            }, fh, indent=2)
        print("report ->", args.report)

    if args.probe:
        print("probe mode: nothing rendered.")
        return

    # ---- render --------------------------------------------------------
    args.before_list = [p.before_jpg for p in pairs]
    args.after_list = [p.after_jpg for p in pairs]
    if not all(args.before_list) or not all(args.after_list):
        sys.exit("extracted pair files missing on disk; re-run with --inspect DIR")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    silent, total, done = render(pairs, args)
    if args.audio:
        mux(silent, args.audio, args.out)
    else:
        shutil.move(silent, args.out)
    print(f"rendered {done} frames ({done / args.fps:.1f}s @ {args.fps}fps) -> {args.out}")


if __name__ == "__main__":
    main()
