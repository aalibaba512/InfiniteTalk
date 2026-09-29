# tools/

Repo-internal helper scripts (not part of the InfiniteTalk inference path).

## `beforeafter_video.py`

Turns a PDF (or two image folders) of **side-by-side BEFORE | AFTER pairs** into a
video where the before image is shown first, then wipes away to reveal the after
image — instead of the two sitting next to each other on a slide.

### How it finds the pairs

1. **Native images first.** If a row of two comparable photos is embedded in the
   PDF, the originals are extracted at full resolution.
2. **Page render fallback.** Otherwise the page is rasterised at `--dpi` and the
   photos are located by *coverage*: a photo row is solidly non-background across
   nearly the full width, whereas a headline row only touches a few percent. That
   threshold is what stops titles and captions being swallowed into a crop.
3. **Rows become pairs.** Photo boxes are clustered into visual rows, so several
   before/after pairs stacked on one page each become their own pair.

Both halves of a pair are always cut to a **shared vertical band**, so they have
identical dimensions and the wipe lines up exactly.

### Usage

```bash
# check what would be extracted, without rendering (recommended first run)
python3 tools/beforeafter_video.py --pdf deck.pdf --probe --inspect out/pairs

# render the video
python3 tools/beforeafter_video.py --pdf deck.pdf --out out/reveal.mp4

# tuned: slower reveal, counter-clockwise wipe dir, no labels
python3 tools/beforeafter_video.py --pdf deck.pdf --out out/reveal.mp4 \
    --hold-before 2.6 --wipe-dur 1.6 --hold-after 3.0 \
    --label-before "BEFORE" --label-after "AFTER" --title "Quetta — before & after"
```

Key options: `--wipe lr|rl|tb|bt`, `--zoom`, `--aspect common|none`, `--pages 1,3-5`,
`--fps`, `--crf`, `--no-labels`, `--no-knob`, `--audio narration.wav`, `--report r.json`.

### Expected input

A PDF where before and after appear **side by side**. One pair per page, or several
stacked rows per page — both work. Works on flattened PDFs (a single embedded image
per page) as well as ones with the original photos embedded.

### Environment notes

- Needs `pymupdf`, `pillow`, `numpy`. If apt is unavailable in the sandbox:
  `pip install --target .toolkit/pylibs pymupdf pillow numpy`, then run with
  `PYTHONPATH=.toolkit/pylibs`.
- ffmpeg is looked up at `.toolkit/bin/ffmpeg` first, then `PATH`.
  `.toolkit/` is gitignored and disposable.
- Rendering is CPU-only and does not need a GPU: 1080p30 runs ~15-25 fps of
  video per second of wall time on 2 vCPUs.
