# 🧰 Project Toolkit — Curated GitHub Tools

> Researched via GitHub Explore (topics + awesome lists) on 2026-09-23.
> Categories: Video Editing · Design · Strategy & Digital Media Strategy · Data Scraping.
> Star counts are approximate (as of research date). Add the ones you want into the repo as needed.

### ⚡ These repos are now registered in this repository
- **Registry:** `toolkit.repos.toml` (machine-readable source of truth — 66 repos)
- **Fetcher:** `python3 tools/toolkit.py clone core|<category>|<name>` → shallow-clones into gitignored `.toolkit/`
- **Browse:** `python3 tools/toolkit.py list` · `python3 tools/toolkit.py search ai`
- Future working sessions: see **`AGENTS.md`** for task → tool mapping and ground rules.

---

## 🎬 1. Video Editing

### Full Editors (GUI)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Shotcut | https://github.com/mltframework/shotcut | Most-starred actively maintained open-source NLE; cross-platform, 4K | ~14k |
| Olive | https://github.com/olive-editor/olive | Modern, node/nonlinear editor; clean Premiere-like UX | ~9k |
| OpenShot | https://github.com/OpenShot/openshot-qt | Easiest entry point; drag-and-drop, 400+ transitions | ~5.7k |
| Kdenlive | https://github.com/KDE/kdenlive | Best Premiere-Pro-style workflow; proxy editing, VST audio | ~5k |
| Cap | https://github.com/CapSoftware/Cap | Open-source CapCut/Loom alternative (screen + video editing) | ~12k |
| OpenCut | https://github.com/OpenCut-app/OpenCut | Open-source CapCut alternative for web/desktop | ~26k |

### Programmatic / CLI Editing (great for automation pipelines)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| FFmpeg | https://github.com/FFmpeg/FFmpeg | The backbone of everything video. Non-negotiable | ~50k |
| MoviePy | https://github.com/Zulko/moviepy | Video editing with Python — scriptable cuts, compositing, subtitles | ~14.9k |
| Remotion | https://github.com/remotion-dev/remotion | Make videos in React — perfect for templated social content | ~25k |
| Editly | https://github.com/mifi/editly | Declarative CLI video editing + API | ~4k |
| Auto-Editor | https://github.com/WyattBlue/auto-editor | Automatically removes silence/dead footage | ~4k |
| LosslessCut | https://github.com/mifi/lossless-cut | Swiss-army knife for lossless trimming without re-encoding | ~38k |
| PySceneDetect | https://github.com/Breakthrough/PySceneDetect | Scene-change detection — feed into auto-clipping workflows | ~3k |
| HandBrake | https://github.com/HandBrake/HandBrake | Batch transcoding with sensible presets | ~20k |
| backgroundremover | https://github.com/nadermx/backgroundremover | AI background removal from images AND video via CLI | ~8k |

### Capture & AI (pairs directly with InfiniteTalk)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| OBS Studio | https://github.com/obsproject/obs-studio | Recording + live streaming standard | ~65k |
| Blender (VSE + 3D) | https://github.com/blender/blender | Compositing, VFX, motion tracking, 3D titles | ~15k |
| LivePortrait | https://github.com/KlingAIResearch/LivePortrait | Portrait animation — strong synergy with InfiniteTalk talking-head work | ~19k |
| autoclip | https://github.com/zhouxiaoka/autoclip | AI highlight extraction & clipping from long videos | ~8.8k |
| OpenCreator | https://github.com/krillinai/OpenCreator | All-in-one AI creator workspace (video, voice, avatars, translation) | ~12k |

### Meta lists (more options)
- Awesome Video Production — https://github.com/ad-si/awesome-video-production
- Awesome Video — https://github.com/sitkevij/awesome-video
- GitHub Explore: https://github.com/topics/video-editing

---

## 🎨 2. Design

### Core open-source apps
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Penpot | https://github.com/penpot/penpot | The open-source Figma alternative; real-time team design + prototyping | ~60k |
| Excalidraw | https://github.com/excalidraw/excalidraw | Hand-drawn-style whiteboarding, diagrams, quick mockups | ~100k |
| tldraw | https://github.com/tldraw/tldraw | Infinite-canvas SDK — embed collaborative whiteboards in your own apps | ~50k |
| GIMP | https://github.com/GNOME/gimp | Photoshop-class raster editing | ~6k (gitlab mirror is canonical) |
| Inkscape | https://github.com/inkscape/inkscape | Vector graphics / logo / SVG editing | ~3k |
| **VTracer** | https://github.com/visioncortex/vtracer | **Best free raster→SVG tracer** — engine behind `tools/vectorize.py` (finest/balanced/compact/lineart presets) | ~7.2k |
| DiffVG | https://github.com/BachiLi/diffvg | Research-grade differentiable SVG (AI-style vector optimization, CUDA build) | ~1.3k |
| Krita | https://github.com/KDE/krita | Digital painting & illustration | ~6k |
| Darktable | https://github.com/darktable-org/darktable | Photography workflow + raw processing | ~4k |
| Photopea (free, web) | https://www.photopea.com | Browser PSD editor (not OSS, but zero-cost Photoshop stand-in) | — |

**Vectorize any image (finest-shape raster → SVG):**
```bash
pip install pillow numpy                 # pipeline deps
npm install @visioncortex/vtracer        # 1.0 WASM engine (preferred; auto-detected)
pip install vtracer                      # optional 0.6 fallback engine
python3 tools/vectorize.py photo.png out.svg --mode finest  # presets: finest|balanced|compact|lineart
python3 tools/vectorize_app.py                              # web UI on http://0.0.0.0:7860
```
Demo pair lives in `assets/vectorize-demo/`. `finest` = merged-palette cleanup + 2× flat
supersample into the **vtracer 1.0 WASM engine** (seam-free cutout + curve simplification):
~1.4k smooth paths / 456 KB where the old PyPI engine's naive tracing gave 38k jagged / 13 MB.

### UI kits & design systems (for web/app projects)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| shadcn/ui | https://github.com/shadcn-ui/ui | The de-facto standard component collection for React/Tailwind | ~85k |
| Storybook | https://github.com/storybookjs/storybook | Build & document UI components in isolation | ~88k |
| Storyteller note: Bulma | https://github.com/jgthms/bulma | Modern CSS framework, no JS required | ~50k |

### Meta lists (hundreds more tools)
- Awesome Design Tools — https://github.com/goabstract/Awesome-Design-Tools (~41k ⭐)
- Design Resources for Developers — https://github.com/bradtraversy/design-resources-for-developers (~370k ⭐)
- GitHub Explore: https://github.com/topics/design · https://github.com/topics/design-tools

---

## 📈 3. Strategy & Digital Media Strategy

### Publishing, scheduling & audience (the "digital media" stack)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Postiz | https://github.com/gitroomhq/postiz-app | Open-source Buffer/Hootsuite alternative. Schedule to 30+ networks, built-in AI content, self-hostable | ~35k |
| Socioboard | https://github.com/socioboard/Socioboard-5.0 | Open-source social media management, analytics & reporting platform | ~1k |
| Ghost | https://github.com/TryGhost/Ghost | The standard open-source publishing/newsletter platform | ~50k |
| Listmonk | https://github.com/knadh/listmonk | High-performance self-hosted newsletter + mailing lists | ~17k |

### Marketing automation, CRM & analytics (measurement = strategy)
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Mautic | https://github.com/mautic/mautic | World's largest open-source marketing automation platform | ~8k |
| Twenty | https://github.com/twentyhq/twenty | Open-source Salesforce-alternative CRM, AI-ready | ~57k |
| Plausible Analytics | https://github.com/plausible/analytics | Privacy-first web analytics, self-hosted | ~29k |
| Matomo | https://github.com/matomo-org/matomo | Full-featured Google Analytics alternative | ~22k |
| Umami | https://github.com/umami-software/umami | Lightweight, privacy-focused analytics | ~28k |
| n8n | https://github.com/n8n-io/n8n | Workflow automation — glue your whole marketing/data pipeline together | ~130k |

### Strategy frameworks & playbooks
| Resource | Link | Why it's here |
|---|---|---|
| latticework | https://github.com/l4ci/latticework | 50+ thinking/strategy frameworks (SWOT, Porter's Five Forces, OKR, Cynefin) packaged as AI-agent skills |
| marketingskills | https://github.com/coreyhaines31/marketingskills | Marketing skills for AI agents: CRO, copywriting, SEO, analytics, growth engineering (~51k ⭐) |
| Awesome Marketing | https://github.com/ronakganatra/awesome-marketing | Hand-picked strategy & growth resources (PLG, funnels, metrics, org design) |
| Awesome Marketing Tools | https://github.com/tractiongroup/awesome-marketing-tools | Curated ads/SEO/email/CRO/influencer tool lists |
| Awesome Content Marketing | https://github.com/awesomelistsio/awesome-content-marketing | Content strategy, distribution & optimization resources |

### Meta
- GitHub Explore: https://github.com/topics/marketing · https://github.com/topics/social-media-marketing · https://github.com/topics/business-frameworks

---

## 🕷️ 4. Data Scraping

### Frameworks & crawlers
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Firecrawl | https://github.com/firecrawl/firecrawl | #1 AI-era scraper — turns websites into LLM-ready markdown; search, scrape, crawl at scale | ~184k |
| Scrapling | https://github.com/D4Vinci/Scrapling | Adaptive stealth scraping framework; auto-heals selectors when pages change | ~83k |
| Scrapy | https://github.com/scrapy/scrapy | The battle-tested production Python crawling framework | ~64k |
| Crawlee | https://github.com/apify/crawlee | Best all-in-one Node.js/TS scraping framework (browser + HTTP) | ~25k |
| Colly | https://github.com/gocolly/colly | Fast & elegant Go scraper | ~25k |
| Katana | https://github.com/projectdiscovery/katana | Go crawler for URL discovery / security recon | ~17k |

### Browser automation & anti-detection
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Playwright | https://github.com/microsoft/playwright | Microsoft's cross-browser automation default for JS-heavy sites | ~92k |
| Puppeteer | https://github.com/puppeteer/puppeteer | Chrome-first automation | ~95k |
| Camoufox | https://github.com/daijro/camoufox | Anti-detect Firefox — for fingerprint-heavy targets | ~11k |
| browser-use | https://github.com/browser-use/browser-use | Let AI agents drive the browser (scraping + interaction) | ~100k |

### AI / no-code & vertical
| Tool | Link | Why it's here | Stars |
|---|---|---|---|
| Crawl4AI | https://github.com/unclecode/crawl4ai | LLM-friendly crawler built for RAG pipelines | ~70k |
| Maxun | https://github.com/maxun-dev/maxun | No-code, self-hosted "robots" that scrape like a human | ~17k |
| MediaCrawler | https://github.com/NanmiCoder/MediaCrawler | Social-media data (XHS/Douyin/Kuaishou/Bilibili/Weibo/Tieba) — great for digital-media research | ~63k |
| google-maps-scraper | https://github.com/gosom/google-maps-scraper | Local-business & POI lead scraping with geo-targeting | ~5.5k |

### Meta lists
- Awesome Web Scraping — https://github.com/lorien/awesome-web-scraping
- GitHub Explore: https://github.com/topics/web-scraping

---

## ✅ Suggested "starter picks" (if you only add a few)

| Category | Pick | One-liner |
|---|---|---|
| Video editing | FFmpeg + LosslessCut + MoviePy | Encode/trim anything + Python automation |
| Design | Penpot + Excalidraw | Figma alternative + instant mockups |
| Strategy | Postiz + Plausible + Mautic | Publish → measure → automate loop |
| Scraping | Firecrawl + Scrapy + Crawl4AI | Modern AI-ready + production-grade crawling |

## ⚖️ Licensing & etiquette notes
- Check each license before commercial use: most above are GPL/Apache/MIT/AGPL — AGPL (Firecrawl, Maxun, Postiz, Crawl4AI) requires releasing source if you offer it as a network service.
- For scraping: respect `robots.txt`, platform ToS, and rate limits. Use proxies responsibly; several tools above list proxy requirements in their docs.
