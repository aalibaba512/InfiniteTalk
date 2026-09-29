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

### Captions

Each pair's caption is read from the PDF: the nearest text block above the row
(or, failing that, below it), requiring horizontal overlap so a neighbouring
column's caption is never borrowed. Trailing gloss like `before | after`,
`BEFORE/AFTER` or `before vs after` is stripped, so what lands on screen is the
location or subject. Nearest wins; ties within ~12pt are broken by which block is
centred over the pair, so a small corner label can't beat the real caption.

The caption fades in and sits above the title badge.

Three things that matter on real decks:

- **Labels are not captions.** A slide that prints `Before` and `After` under the
  two photos has those read as *labels*. They are matched to the photo they sit
  under (by horizontal overlap plus depth), never shown as text, and their
  presence is recorded as `labelled` in the report.
- **Orientation is checked.** If a row is printed `After | Before`, the pair is
  swapped back and a note is emitted. A video with the reveal backwards is the
  worst possible failure, so it is worth the extra lookup.
- **Page furniture is filtered.** Text repeating across ~40% of the document
  (running headers, logos, footers) is boilerplate and never becomes a caption.
  Among the rest, the largest type near the pair wins, so a slide's real caption
  beats an incidental promo line.

Overrides, for the last mile:

```bash
--caption "text"              # same caption on every pair
--no-captions                 # none at all
--caption-map overrides.json  # per page: {"8": "", "3": "Distemper, 1000 sqm"}
```

An empty string in the map silences one page; `"index:3"` addresses the 3rd pair
instead of a page number.

### Mixed decks

Decks often interleave real before/after pages with promo or admissions slides
that still have two images side by side. `--only-labelled` keeps only the rows
whose slide actually prints `Before`/`After`, which drops the promo pages.
Check the report's `labelled` column before relying on it.

```bash
python3 tools/beforeafter_video.py --pdf deck.pdf --probe --only-labelled --report r.json
python3 -c "import json;[print(p['page'], p['labelled'], p['caption']) for p in json.load(open('r.json'))['pairs']]"
```

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
`--fps`, `--crf`, `--no-labels`, `--no-knob`, `--caption`, `--no-captions`,
`--caption-map`, `--only-labelled`, `--source`, `--music`, `--audio`, `--report`.

Timing defaults are deliberately unhurried (`--hold-before 3.4 --wipe-dur 1.7
--hold-after 3.4`, so ~8.5s per pair) to give each transformation time to land.
`--report out.json` records the extracted pairs, their captions and the settings,
which doubles as a check that the right columns were picked.

### Expected input

A PDF where before and after appear **side by side**. One pair per page, or several
stacked rows per page — both work. Works on flattened PDFs (a single embedded image
per page) as well as ones with the original photos embedded.

### Music

`--music uplifting|calm` generates an original music bed with `tools/make_music.py`,
cut to exactly the video's length, and muxes it in — one command, no asset to
source:

```bash
python3 tools/beforeafter_video.py --pdf deck.pdf --out reveal.mp4 --music uplifting
```

Everything is synthesised from scratch with numpy — no samples, no network, no
licence and no attribution. Useful here because the sandbox can only reach GitHub
and PyPI, so every stock-music host is unreachable.

## `make_music.py`

Composes and renders the bed offline.

| Mood | Feel |
|---|---|
| `uplifting` (default) | 76 BPM, I–V–vi–IV in C, warm pad + arpeggio + soft kick, gentle build |
| `calm` | 68 BPM, no percussion, longer reverb |

```bash
python3 tools/make_music.py --duration 241.6 --mood uplifting --out music.wav
```

Voices are built from harmonic partials with per-partial decay, then sent through
a synthetic plate reverb (block FFT convolution). The arrangement eases each
instrument in over its own range rather than switching it on, and the level is
deliberately flat through the middle so the bed does not swell under the video.
Output is normalised to about -19.6 dBFS RMS, which sits under a voiceover
without competing with it.

### Environment notes

- Needs `pymupdf`, `pillow`, `numpy`. If apt is unavailable in the sandbox:
  `pip install --target .toolkit/pylibs pymupdf pillow numpy`, then run with
  `PYTHONPATH=.toolkit/pylibs`.
- ffmpeg is looked up at `.toolkit/bin/ffmpeg` first, then `PATH`.
  `.toolkit/` is gitignored and disposable.
- Rendering is CPU-only and does not need a GPU: 1080p30 runs ~15-25 fps of
  video per second of wall time on 2 vCPUs.
