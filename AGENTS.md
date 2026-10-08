# AGENTS.md — Working Notes for AI Sessions (and Humans)

This project (InfiniteTalk) maintains a **curated external toolkit**: battle-tested open-source
repos for **video editing, design, strategy / digital-media strategy, and data scraping** that we
reuse across projects.

## Where the toolkit lives

| File | Purpose |
|---|---|
| `toolkit.repos.toml` | **Source of truth.** Machine-readable registry of all 66 curated repos (name, URL, category, tags, use-case, license). |
| `TOOLKIT.md` | Human-readable catalog with descriptions and GitHub Explore links. |
| `tools/toolkit.py` | CLI to list / search / shallow-clone / update any of them. |

## Which repos to reach for (task → tool)

- **Cut / trim / encode video** → `ffmpeg` (anything), `lossless-cut` (lossless trims), `handbrake` (batch transcode)
- **Automate edits in code** → `moviepy` (Python), `remotion` (React templating), `editly` (declarative CLI), `auto-editor` (silence removal), `pyscenedetect` (scene cuts)
- **AI video / talking-head extras** → `liveportrait`, `autoclip`, `opencreator`, `backgroundremover`
- **Design assets & UI** → `penpot` (Figma alt), `excalidraw` (mockups), `gimp`/`inkscape`/`krita`, `ui-shadcn` + `bulma` (web UI)
- **Vectorize images (raster → SVG, finest shapes)** → `tools/vectorize.py` (vtracer engine; presets `finest`/`balanced`/`compact`/`lineart`; web UI: `python3 tools/vectorize_app.py`)
- **Publish & grow (digital media strategy)** → `postiz` (scheduling hub), `ghost`/`listmonk` (content/email), `plausible`/`umami`/`matomo` (analytics), `mautic` (automation), `twenty` (CRM), `n8n` (glue)
- **Strategy frameworks with AI agents** → `latticework`, `marketingskills`
- **Scrape data** → `firecrawl` or `crawl4ai` (LLM-ready output), `scrapy` (production Python crawls), `scrapling` (stealth/adaptive), `playwright` (JS-heavy sites), `browser-use` (agent-driven), `maxun` (no-code), `mediacrawler` (social platforms — **research/ToS caution**), `google-maps-scraper` (local leads)
- **Need something not listed?** → check the `awesome-*` meta lists first; don't guess random repos.

## How to fetch (never commit these repos)

```bash
python3 tools/toolkit.py list            # see everything
python3 tools/toolkit.py clone core      # the 11 starter repos
python3 tools/toolkit.py clone scraping  # a whole category
python3 tools/toolkit.py clone moviepy   # one repo → .toolkit/<category>/<name>/
python3 tools/toolkit.py update all      # refresh clones
```

Clones go to `.toolkit/` which is **gitignored** — shallow, on-demand, disposable.
Do **not** vendor toolkit code into this repo; pip/npm-install the library ones or shell out to the CLI ones from `.toolkit/`.

## Ground rules

1. **Check licenses before commercial use.** AGPL entries (`firecrawl`, `postiz`, `plausible`, `maxun`, `listmonk`, `twenty`, `cap`, `opencut`) require releasing source if offered as a network service. `mediacrawler` is education/non-commercial — verify before any use.
2. **Scrape responsibly:** respect `robots.txt`, platform ToS, and rate limits; proxies per each tool's docs.
3. **Adding a new tool:** append a `[[repo]]` block to `toolkit.repos.toml` *and* a row in `TOOLKIT.md`, then commit both.
