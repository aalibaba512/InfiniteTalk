#!/usr/bin/env python3
"""
vectorize.py — clean raster → SVG vectorization with two engines.

Engines
-------
  imagetracer (default for color) ... jankovicsandras/imagetracerjs (MIT, ~1.5k★)
        smooth layered cartoon vectorization; auto-downloaded into .toolkit/
  vtracer (lineart / --engine vtracer) ... visioncortex/vtracer (MIT, ~7.2k★)
        pip install vtracer

Pipeline (color modes)
----------------------
  1. flatten RGBA onto background
  2. merged palette ......... over-quantize to 64, collapse near-duplicate tones
  3. median clean ........... kills compression speckle, keeps thin lines
  4. flat supersample ....... NEAREST ×2 keeps fills flat (finest)
  5. engine trace ........... imagetracer fits smooth quadratic/cubic splines
                              (ltres/qtres tolerances, pathomit speckle guard)
  6. bake & clip ............ scale + clamp baked into coordinates: output has
                              NO transforms, nothing outside the viewBox, so
                              browsers AND Photoshop/Illustrator render it alike

CLI
---
  python3 tools/vectorize.py INPUT [OUT.svg] [--mode finest|balanced|compact|lineart]
      [--engine imagetracer|vtracer] [--palette N] [--merge-dist T]
      [--supersample N] [--bg auto|#hex] [--threshold T]

As a library:  from tools.vectorize import vectorize
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO = Path(__file__).resolve().parent.parent
IT_DIR = REPO / ".toolkit" / "imagetracerjs"
IT_LIB = IT_DIR / "imagetracer_v1.2.6.js"
IT_URL = ("https://codeload.github.com/jankovicsandras/imagetracerjs/"
          "tar.gz/refs/heads/master")
BRIDGE = Path(__file__).resolve().parent / "imagetracer_bridge.js"
POTRACE_BRIDGE = Path(__file__).resolve().parent / "potrace_bridge.js"
POTRACE_DIR = REPO / ".toolkit" / "potrace-engine"

MODES = {
    "finest": dict(engine="imagetracer", supersample=2, quant=64, merge_dist=32,
                   median=5, it=dict(ltres=2, qtres=2, pathomit=12, blurradius=0),
                   help="smooth vector-art quality: merged palette + 2x flat supersample"),
    "balanced": dict(engine="imagetracer", supersample=1, quant=64, merge_dist=32,
                     median=3, it=dict(ltres=2, qtres=2, pathomit=8, blurradius=0),
                     help="same cleanup at native resolution"),
    "compact": dict(engine="imagetracer", supersample=1, quant=64, merge_dist=56,
                    median=5, it=dict(ltres=3, qtres=3, pathomit=16, blurradius=0),
                    help="posterized & tiny"),
    "lineart": dict(engine="vtracer", supersample=2, quant=0, merge_dist=0, median=0,
                    trace=dict(colormode="binary", mode="spline", filter_speckle=2,
                               corner_threshold=100, length_threshold=5.0,
                               splice_threshold=60, path_precision=3),
                    help="black & white line art / sketches (uses --threshold)"),
}

# legacy vtracer color settings (fallback engine)
VTRACER_COLOR = dict(colormode="color", hierarchical="stacked", mode="spline",
                     filter_speckle=8, color_precision=8, layer_difference=8,
                     corner_threshold=100, length_threshold=5.0, splice_threshold=60,
                     path_precision=3)

# ---------------------------------------------------------------- helpers

def _flatten(img: Image.Image, bg: str) -> Image.Image:
    if img.mode not in ("RGBA", "LA", "PA") and not (
            img.mode == "P" and "transparency" in img.info):
        return img.convert("RGB")
    if bg == "auto":
        bg = "#ffffff"
    rgb = img.convert("RGBA")
    backdrop = Image.new("RGB", rgb.size, bg)
    backdrop.paste(rgb, mask=rgb.getchannel("A"))
    return backdrop


def _merged_palette(img: Image.Image, colors: int, merge_dist: int):
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
    return Image.fromarray(pal[remap[arr]].astype(np.uint8), "RGB"), len(keep)


def _prepare(img, *, median, quant, merge_dist, supersample, binarize):
    kept = 0
    if binarize is not None:
        img = img.convert("L").point(lambda v: 0 if v < binarize else 255).convert("RGB")
    else:
        if quant and quant > 0 and merge_dist and merge_dist > 0:
            img, kept = _merged_palette(img, quant, merge_dist)
        elif quant and quant > 0:
            img = img.quantize(colors=quant, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE).convert("RGB")
            kept = quant
        if median:
            img = img.filter(ImageFilter.MedianFilter(median))
    if supersample and supersample > 1:
        w, h = img.size
        img = img.resize((w * supersample, h * supersample), Image.NEAREST)
    return img, kept


def _ensure_imagetracer() -> Path:
    if IT_LIB.exists():
        return IT_LIB
    IT_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(IT_URL) as r:  # fixed github URL
        data = r.read()
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.name.endswith("imagetracer_v1.2.6.js"):
                tf.extract(m, IT_DIR, filter="data")
                (IT_DIR / m.name).rename(IT_LIB)
                break
    if not IT_LIB.exists():
        raise RuntimeError("imagetracerjs bootstrap failed")
    return IT_LIB


def _ensure_potrace() -> Path:
    if (POTRACE_DIR / "node_modules" / "potrace").exists():
        return POTRACE_DIR
    POTRACE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npm", "init", "-y"], cwd=POTRACE_DIR, check=True,
                   capture_output=True)
    subprocess.run(["npm", "install", "potrace", "--no-audit", "--no-fund"],
                   cwd=POTRACE_DIR, check=True, capture_output=True)
    return POTRACE_DIR


def _trace_potrace(img: Image.Image, opts: dict) -> str:
    """Multicolor potrace (the Inkscape/vectormaker.co approach): one binary
    potrace trace per palette color, stacked back-to-front with 1px dilated
    seams. Smooth optimal béziers; best on crisp flat input."""
    import numpy as _np
    _ensure_potrace()
    arr = _np.asarray(img)
    cols, counts = _np.unique(arr.reshape(-1, 3), axis=0, return_counts=True)
    order = _np.argsort(-counts)
    with tempfile.TemporaryDirectory(prefix="pt-") as td:
        layers = []
        for rank, i in enumerate(order):
            c = cols[i]
            mask = _np.all(arr == c, axis=-1)
            m = Image.fromarray((~mask * 255).astype(_np.uint8))
            if rank > 0:
                m = m.filter(ImageFilter.MinFilter(3))
            f = str(Path(td) / f"mask-{rank:02d}.png")
            m.save(f)
            layers.append({"file": f, "fill": "#%02x%02x%02x" % tuple(int(v) for v in c)})
        lj = Path(td) / "layers.json"
        lj.write_text(json.dumps(layers))
        o = dict(turdSize=5, alphaMax=1.2, optTolerance=0.4, optCurve=True,
                 threshold=127, **opts)
        out = Path(td) / "out.svg"
        subprocess.run(["node", str(POTRACE_BRIDGE), str(POTRACE_DIR), str(out),
                        str(lj), json.dumps(o)], check=True, capture_output=True)
        return out.read_text()


def _trace_imagetracer(img: Image.Image, opts: dict) -> str:
    lib = _ensure_imagetracer()
    w, h = img.size
    o = dict(colorquantcycles=3, rightangleenhance=True, roundcoords=2,
             layering=0, linefilter=False, strokewidth=1, mincolorratio=0,
             colorsampling=0, viewbox=True, desc=False, **opts)
    cols = np.unique(np.asarray(img).reshape(-1, 3), axis=0)
    o["pal"] = [{"r": int(c[0]), "g": int(c[1]), "b": int(c[2]), "a": 255}
                for c in cols]
    with tempfile.TemporaryDirectory(prefix="vec-") as td:
        raw = Path(td) / "in.raw"
        raw.write_bytes(img.convert("RGBA").tobytes())
        out = Path(td) / "out.svg"
        subprocess.run(["node", str(BRIDGE), str(lib), str(raw), str(w), str(h),
                        str(out), json.dumps(o)], check=True, capture_output=True)
        return out.read_text()


# ------------------------------------------------------- generic bake & clip

def _bake_paths(body: str, w2: int, h2: int, scale: float) -> str:
    """Clamp every path to the canvas and bake the supersample scale into the
    coordinates (supports M/L/Q/C/Z absolute commands — both engines)."""

    def fix(m: re.Match) -> str:
        d, rest = m.group(1), m.group(2)
        toks = re.findall(r"[MLQCZ]|-?\d+(?:\.\d+)?", d)
        res: list[str] = []
        bbox = [1e18, 1e18, -1e18, -1e18]
        n = 0
        for t in toks:
            if t.isalpha():
                n = 0
                res.append(t)
                continue
            v = float(t)
            if n % 2 == 0:
                v = min(max(v, 0), w2)
                bbox[0], bbox[2] = min(bbox[0], v), max(bbox[2], v)
            else:
                v = min(max(v, 0), h2)
                bbox[1], bbox[3] = min(bbox[1], v), max(bbox[3], v)
            res.append(f"{v * scale:.2f}".rstrip("0").rstrip(".") or "0")
            n += 1
        if bbox[0] <= 1 and bbox[1] <= 1 and bbox[2] >= w2 - 1 and bbox[3] >= h2 - 1:
            fill = re.search(r'fill="([^"]+)"', rest)
            fc = fill.group(1) if fill else "#000"
            return (f'<path d="M0,0 L{w2 * scale:g},0 L{w2 * scale:g},'
                    f'{h2 * scale:g} L0,{h2 * scale:g} Z" fill="{fc}"{rest}/>')
        return f'<path d="{" ".join(res)}"{rest}/>'

    return re.sub(r'<path d="([^"]+)"([^>]*)/>', fix, body)


def _finish_svg(raw: str, width: int, height: int, scale: float, meta: str) -> str:
    raw = re.sub(r"<\?xml[^>]*\?>\s*", "", raw)
    raw = re.sub(r"<!--.*?-->\s*", "", raw, flags=re.S)
    body = re.sub(r"<svg[^>]*>", "", raw, count=1).replace("</svg>", "")
    w2, h2 = round(width / scale), round(height / scale)
    body = _bake_paths(body, w2, h2, scale)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" overflow="hidden">')
    return f'{head}\n<!-- {meta} -->\n{body}</svg>\n'


# ------------------------------------------------------------------ API

def vectorize(input_path, output_path=None, *, mode: str = "finest",
              engine: str | None = None, palette: int | None = None,
              merge_dist: int | None = None, supersample: int | None = None,
              bg: str = "auto", threshold: int = 127, quiet: bool = False) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'; choose from {sorted(MODES)}")
    preset = MODES[mode]
    eng = engine or preset["engine"]
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
                          merge_dist=md if eng == "imagetracer" else 0,
                          supersample=ss, binarize=binarize)

    if eng == "imagetracer" and mode != "lineart":
        raw_svg = _trace_imagetracer(work, preset.get("it", {}))
    elif eng == "potrace" and mode != "lineart":
        raw_svg = _trace_potrace(work, preset.get("pt", {}))
    else:  # vtracer
        try:
            import vtracer
        except ImportError:
            sys.exit("vtracer engine requires: pip install vtracer")
        with tempfile.TemporaryDirectory(prefix="vec-") as td:
            p = Path(td) / "in.png"
            o = Path(td) / "o.svg"
            work.save(p)
            vtracer.convert_image_to_svg_py(
                str(p), str(o),
                **(preset["trace"] if mode == "lineart" else VTRACER_COLOR))
            raw_svg = o.read_text()

    scale = round(1 / ss, 6) if ss > 1 else 1
    meta = (f"vectorized by InfiniteTalk tools/vectorize.py · engine: {eng} · "
            f"mode={mode} supersample={ss}x colors={kept or 'n/a'}")
    svg = _finish_svg(raw_svg, width, height, scale, meta)

    if output_path is None:
        output_path = input_path.with_suffix(".svg")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg)

    stats = {"input": str(input_path), "output": str(output_path), "mode": mode,
             "engine": eng, "size": (width, height), "supersample": ss,
             "colors": kept, "paths": svg.count("<path"),
             "bytes": output_path.stat().st_size,
             "seconds": round(time.time() - t0, 2)}
    if not quiet:
        print(f"[vectorize:{mode}/{eng}] {input_path.name} → {output_path.name}  "
              f"{width}×{height} @ {ss}x · {stats['paths']:,} paths · "
              f"{stats['bytes'] / 1024:.0f} KB · {stats['seconds']}s")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Vectorize raster images into clean smooth SVGs.")
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--mode", default="finest", choices=sorted(MODES))
    ap.add_argument("--engine", choices=["imagetracer", "potrace", "vtracer"],
                    help="override tracing engine")
    ap.add_argument("--palette", type=int)
    ap.add_argument("--merge-dist", type=int)
    ap.add_argument("--supersample", type=int)
    ap.add_argument("--bg", default="auto")
    ap.add_argument("--threshold", type=int, default=127)
    ap.add_argument("--list-modes", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if a.list_modes:
        for name, p in MODES.items():
            print(f"{name:10s} [{p['engine']}] {p['help']}")
        return 0
    vectorize(a.input, a.output, mode=a.mode, engine=a.engine, palette=a.palette,
              merge_dist=a.merge_dist, supersample=a.supersample, bg=a.bg,
              threshold=a.threshold, quiet=a.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
