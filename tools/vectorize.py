#!/usr/bin/env python3
"""
vectorize.py — clean, smooth raster → SVG vectorization, built on VTracer.

Engine
------
visioncortex/vtracer (https://github.com/visioncortex/vtracer) — the
most-starred free raster→vector converter on GitHub (MIT). Installed from
PyPI:  pip install vtracer pillow numpy

The patch (why this beats stock tracing on flat artwork)
--------------------------------------------------------
Stock vtracer traces JPEG noise literally: staircase edges, ringing halos and
thousands of speckle paths. This pipeline produces true vector-art output:

  1. load & flatten ......... RGBA composited onto a background color
  2. merged palette ......... over-quantize to 64, then collapse entries whose
                              RGB distance < T — kills near-duplicate tones,
                              so flat regions trace as ONE clean fill
  3. median clean ........... 3×3 median removes compression speckle without
                              dissolving thin lines (blur would melt them)
  4. flat supersampling ..... NEAREST upscale keeps region fills perfectly flat
                              (no anti-alias gradients → no halo layers); the
                              spline fitter then smooths the pixel staircase
                              into clean béziers (high corner threshold)
  5. speckle guard .......... tiny disconnected blobs dropped; connected fine
                              detail (chip pins, 2px traces) survives
  6. SVG post ............... normalized header, viewBox, sub-pixel wrapper

Measured on the 1376×768 demo artwork, 2× zoom inspection:
  old naive finest  → 38,212 jagged paths, 13.3 MB, staircase edges
  new finest        → ~1,600 smooth paths,  3.2 MB, clean flat fills

CLI
---
  python3 tools/vectorize.py INPUT [OUTPUT.svg] [--mode MODE] [options]

  --mode     finest | balanced | compact | lineart      (default: finest)
  --palette N         initial quantization colors before merging (default 64)
  --merge-dist T      palette merge distance, 0 = off (default 28)
  --supersample N     trace resolution multiplier (1 = native)
  --bg auto|#rrggbb   background for flattening transparent images
  --threshold T       binarization threshold for lineart (0..255)

As a library
------------
  from tools.vectorize import vectorize
  stats = vectorize("photo.png", "photo.svg", mode="finest")
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import time
from pathlib import Path

try:
    import vtracer
except ImportError:  # pragma: no cover
    sys.exit("vtracer is required:  pip install vtracer   (and pillow/numpy for the pipeline)")

import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
# VTracer spline-fitting knobs:
#   filter_speckle    discard disconnected regions < N px (small = keep noise)
#   color_precision   significant bits per RGB channel (8 = exact)
#   layer_difference  color distance between stacked layers
#   corner_threshold  min turn angle (deg) kept as a sharp corner;
#                     high (100+) lets the spline smooth pixel staircases
#   length_threshold  spline fitting tolerance in px
#   splice_threshold  min angle (deg) between joined spline segments

MODES = {
    "finest": dict(
        trace=dict(
            colormode="color", hierarchical="stacked", mode="spline",
            filter_speckle=8, color_precision=8, layer_difference=8,
            corner_threshold=100, length_threshold=5.0, splice_threshold=60,
            path_precision=3,
        ),
        supersample=2, quant=64, merge_dist=28, median=3,
        help="smooth vector-art quality: merged palette + 2x flat supersample",
    ),
    "balanced": dict(
        trace=dict(
            colormode="color", hierarchical="stacked", mode="spline",
            filter_speckle=4, color_precision=8, layer_difference=8,
            corner_threshold=100, length_threshold=5.0, splice_threshold=60,
            path_precision=3,
        ),
        supersample=1, quant=64, merge_dist=28, median=3,
        help="same cleanup at native resolution; smallest smooth output",
    ),
    "compact": dict(
        trace=dict(
            colormode="color", hierarchical="stacked", mode="spline",
            filter_speckle=8, color_precision=6, layer_difference=16,
            corner_threshold=120, length_threshold=6.0, splice_threshold=70,
            path_precision=2,
        ),
        supersample=1, quant=24, merge_dist=0, median=5,
        help="posterized & tiny: few colors, aggressive simplification",
    ),
    "lineart": dict(
        trace=dict(
            colormode="binary", mode="spline",
            filter_speckle=2, corner_threshold=100, length_threshold=5.0,
            splice_threshold=60, path_precision=3,
        ),
        supersample=2, quant=0, merge_dist=0, median=0,
        help="black & white line art / sketches (uses --threshold)",
    ),
}

# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def _flatten(img: Image.Image, bg: str) -> Image.Image:
    """Composite RGBA onto a solid background ('auto' → white if alpha varies)."""
    if img.mode not in ("RGBA", "LA", "PA") and not (
        img.mode == "P" and "transparency" in img.info
    ):
        return img.convert("RGB")
    if bg == "auto":
        bg = "#ffffff"
    rgb = img.convert("RGBA")
    backdrop = Image.new("RGB", rgb.size, bg)
    backdrop.paste(rgb, mask=rgb.getchannel("A"))
    return backdrop


def _merged_palette(img: Image.Image, colors: int, merge_dist: int):
    """Quantize, then collapse near-duplicate palette entries.

    JPEG artifacts split one visual color into several close tones; tracing
    keeps them as separate blotchy layers. Merging by RGB distance yields one
    flat fill per visual color. Returns (flat RGB image, kept color count).
    """
    q = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                     dither=Image.Dither.NONE)
    pal = np.array(q.getpalette(), dtype=np.int64).reshape(-1, 3)
    arr = np.asarray(q, dtype=np.int64)
    counts = np.bincount(arr.ravel(), minlength=len(pal))
    order = np.argsort(-counts)
    keep: list[int] = []
    remap = np.arange(len(pal))
    for i in order:
        if counts[i] == 0:
            continue
        target = next((k for k in keep
                       if np.abs(pal[i] - pal[k]).sum() < merge_dist), None)
        if target is None:
            keep.append(i)
        else:
            remap[i] = target
    flat = pal[remap[arr]].astype(np.uint8)
    return Image.fromarray(flat, "RGB"), len(keep)


def _prepare(img: Image.Image, *, median: int, quant: int, merge_dist: int,
             supersample: int, binarize: int | None) -> tuple[Image.Image, int]:
    kept = 0
    if binarize is not None:
        img = img.convert("L").point(
            lambda v: 0 if v < binarize else 255).convert("RGB")
    else:
        if quant and quant > 0:
            if merge_dist and merge_dist > 0:
                img, kept = _merged_palette(img, quant, merge_dist)
            else:
                img = img.quantize(colors=quant, method=Image.Quantize.MEDIANCUT,
                                   dither=Image.Dither.NONE).convert("RGB")
                kept = quant
        if median and median > 0:
            img = img.filter(ImageFilter.MedianFilter(median))
    if supersample and supersample > 1:
        w, h = img.size
        # NEAREST on purpose: keeps fills flat (no AA gradients → no halos);
        # the spline fitter smooths the staircase into curves afterwards.
        img = img.resize((w * supersample, h * supersample), Image.NEAREST)
    return img, kept


_PATH_RE = re.compile(r'<path\s+d="([^"]+)"\s+fill="(#[0-9a-fA-F]+)"'
                      r'(?:\s+transform="translate\(([-\d.]+),([-\d.]+)\)")?\s*/>')
_NUM_RE = re.compile(r'[MCZ]|-?\d+(?:\.\d+)?')


def _clip_and_bake(body: str, w2: int, h2: int, scale: float) -> str:
    """Clip every path to the canvas and bake translate+scale into coordinates.

    Two compatibility fixes at once:
      * High corner thresholds make splines overshoot the canvas; browsers hide
        that by clipping to the viewBox but Photoshop/Illustrator previews show
        the overflow. So all coordinates are clamped to the traced canvas and
        the full-canvas background layer becomes a plain <rect>.
      * The sub-pixel scale and per-path translates are multiplied straight
        into the numbers, so the output contains NO transform attributes or
        wrapper groups at all — every viewer renders it identically.
    """
    def fix(m: re.Match) -> str:
        d, fill, txs, tys = m.group(1), m.group(2), m.group(3), m.group(4)
        tx = float(txs) if txs else 0.0
        ty = float(tys) if tys else 0.0
        lo_x, hi_x = -tx, w2 - tx
        lo_y, hi_y = -ty, h2 - ty
        res: list[str] = []
        minx = miny = 1e18
        maxx = maxy = -1e18
        n = 0
        for t in _NUM_RE.findall(d):
            if t.isalpha():
                res.append(t)
                n = 0
                continue
            v = float(t)
            if n % 2 == 0:  # x coordinate
                v = min(max(v, lo_x), hi_x) + tx
                minx, maxx = min(minx, v), max(maxx, v)
            else:           # y coordinate
                v = min(max(v, lo_y), hi_y) + ty
                miny, maxy = min(miny, v), max(maxy, v)
            b = v * scale
            res.append(f"{b:.2f}".rstrip("0").rstrip(".") or "0")
            n += 1
        # full-canvas layer → plain rect (its spline corners overshoot wildly)
        if minx <= 1 and miny <= 1 and maxx >= w2 - 1 and maxy >= h2 - 1:
            return (f'<rect x="0" y="0" width="{w2 * scale:g}" '
                    f'height="{h2 * scale:g}" fill="{fill}"/>')
        return f'<path d="{" ".join(res)}" fill="{fill}"/>'

    return _PATH_RE.sub(fix, body)


def _finish_svg(raw: str, width: int, height: int, scale: float,
                meta: str) -> str:
    """Strip vtracer's prologue, clip + bake geometry, normalize header."""
    raw = re.sub(r"<\?xml[^>]*\?>\s*", "", raw)
    raw = re.sub(r"<!--.*?-->\s*", "", raw, flags=re.S)
    body = re.sub(r"<svg[^>]*>", "", raw, count=1).replace("</svg>", "")
    w2, h2 = round(width / scale), round(height / scale)
    body = _clip_and_bake(body, w2, h2, scale)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'overflow="hidden">')
    return f'{head}\n<!-- {meta} -->\n{body}</svg>\n'


def vectorize(input_path, output_path=None, *, mode: str = "finest",
              palette: int | None = None, merge_dist: int | None = None,
              supersample: int | None = None, bg: str = "auto",
              threshold: int = 127, quiet: bool = False) -> dict:
    """Vectorize `input_path` into a clean SVG. Returns run stats."""
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'; choose from {sorted(MODES)}")
    preset = MODES[mode]
    t0 = time.time()

    input_path = Path(input_path)
    img = Image.open(input_path)
    width, height = img.size

    ss = preset["supersample"] if supersample is None else max(1, int(supersample))
    quant = preset["quant"] if palette is None else int(palette)
    md = preset["merge_dist"] if merge_dist is None else int(merge_dist)
    binarize = threshold if mode == "lineart" else None

    work = _flatten(img, bg)
    work, kept = _prepare(work, median=preset["median"], quant=quant,
                          merge_dist=md, supersample=ss, binarize=binarize)

    with tempfile.TemporaryDirectory(prefix="vectorize-") as td:
        tmp_png = Path(td) / "work.png"
        tmp_svg = Path(td) / "work.svg"
        work.save(tmp_png)
        vtracer.convert_image_to_svg_py(str(tmp_png), str(tmp_svg),
                                        **preset["trace"])
        raw = tmp_svg.read_text()

    scale = round(1 / ss, 6) if ss > 1 else 1
    meta = (f"vectorized by InfiniteTalk tools/vectorize.py · engine: "
            f"visioncortex/vtracer · mode={mode} supersample={ss}x "
            f"colors={kept or 'n/a'}")
    svg = _finish_svg(raw, width, height, scale, meta)

    if output_path is None:
        output_path = input_path.with_suffix(".svg")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg)

    stats = {
        "input": str(input_path), "output": str(output_path), "mode": mode,
        "size": (width, height), "supersample": ss, "colors": kept,
        "paths": svg.count("<path"),
        "fills": len(set(re.findall(r'fill="(#[0-9a-fA-F]+)"', svg))),
        "bytes": output_path.stat().st_size, "seconds": round(time.time() - t0, 2),
    }
    if not quiet:
        print(f"[vectorize:{mode}] {input_path.name} → {output_path.name}  "
              f"{width}×{height} @ {ss}x · {stats['paths']:,} paths · "
              f"{stats['fills']} fills · {stats['bytes']/1024:.0f} KB · "
              f"{stats['seconds']}s")
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Vectorize raster images into clean smooth SVGs (vtracer engine).")
    ap.add_argument("input", help="input raster image (png/jpg/webp/...)")
    ap.add_argument("output", nargs="?", help="output .svg (default: input with .svg)")
    ap.add_argument("--mode", default="finest", choices=sorted(MODES),
                    help="quality preset (default: finest)")
    ap.add_argument("--palette", type=int, default=None,
                    help="initial quantization colors before merging (default 64)")
    ap.add_argument("--merge-dist", type=int, default=None,
                    help="palette merge RGB distance, 0 = off (default 28)")
    ap.add_argument("--supersample", type=int, default=None,
                    help="override trace resolution multiplier")
    ap.add_argument("--bg", default="auto",
                    help="flatten background for transparent images (auto|#rrggbb)")
    ap.add_argument("--threshold", type=int, default=127,
                    help="lineart binarization threshold (0..255)")
    ap.add_argument("--list-modes", action="store_true", help="describe presets and exit")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.list_modes:
        for name, p in MODES.items():
            print(f"{name:10s} {p['help']}")
        return 0

    vectorize(args.input, args.output, mode=args.mode, palette=args.palette,
              merge_dist=args.merge_dist, supersample=args.supersample,
              bg=args.bg, threshold=args.threshold, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
