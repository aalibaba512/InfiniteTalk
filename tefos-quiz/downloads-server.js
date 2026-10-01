'use strict';
/**
 * Minimal download server for the TEFOS deliverables.
 * Serves only an explicit whitelist, as attachments, so nothing else in the
 * repository is reachable over HTTP.
 */
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const DIR = '/home/user/InfiniteTalk/tefos-quiz';
const PORT = Number(process.env.PORT || 8080);
const HOST = '0.0.0.0';

// Whitelist: what may be downloaded, and how to describe it.
const FILES = {
  'TEFOS-Quiz-Proposal.pptx': {
    title: 'TEFOS Quiz - Proposal Deck',
    note: '22 slides. Board-ready pitch: the insight, participation rules, points arithmetic, rank ladder, screens, bursary economics, championship, sponsorship, privacy, rollout, metrics, cost, and the three asks.',
    size: '5.8 MB',
  },
  'TEFOS-Quiz-Whitepaper.docx': {
    title: 'TEFOS Quiz - Whitepaper',
    note: '17 sections, 11 tables. Design principles with the arithmetic, rank activity floor, uncheatable quiz design, anti-gaming controls, privacy posture, data model, economics, championship, measurement, risk register, and open questions.',
    size: '52 KB',
  },
  'WHITEPAPER.md': {
    title: 'Whitepaper (Markdown source)',
    note: 'Plain-text source of the whitepaper, in case you want to paste sections into an email or a wiki.',
    size: '31 KB',
  },
  'VIDEO-SCRIPT.md': {
    title: 'Video Demonstration Script',
    note: '2m15s master with per-shot visual / voice-over / on-screen text, a clean narration read, sound direction, B-roll shot list, plus 60s and 30s vertical cuts.',
    size: '12 KB',
  },
  'README.md': {
    title: 'Prototype README',
    note: 'How to run the working prototype, and why each design decision was made.',
    size: '8 KB',
  },
};

const TYPES = {
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.md': 'text/markdown; charset=utf-8',
  '.png': 'image/png',
};

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function index() {
  const rows = Object.entries(FILES).map(([name, meta]) => {
    const exists = fs.existsSync(path.join(DIR, name));
    const actual = exists
      ? `${(fs.statSync(path.join(DIR, name)).size / 1048576).toFixed(1)} MB`
      : 'missing';
    return `
    <div class="card${exists ? '' : ' gone'}">
      <div class="row">
        <div>
          <a class="name" href="/d/${encodeURIComponent(name)}">${esc(meta.title)}</a>
          <div class="fname">${esc(name)}</div>
          <p>${esc(meta.note)}</p>
        </div>
        <div class="right">
          <div class="size">${actual}</div>
          <a class="btn${exists ? '' : ' dis'}" href="/d/${encodeURIComponent(name)}">Download</a>
        </div>
      </div>
    </div>`;
  }).join('');

  return `<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TEFOS Quiz - Downloads</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f6f7f8;color:#16232b}
header{background:#0f3d4a;color:#fff;padding:1.4rem 1.2rem}
header .wrap{max-width:820px;margin:0 auto}
header b{display:block;letter-spacing:.16em;font-size:.8rem;color:#ffd98a;margin-bottom:.3rem}
header h1{margin:0;font-size:1.6rem}
header p{margin:.5rem 0 0;color:#7fd3e0;font-size:.95rem;max-width:60ch}
main{max-width:820px;margin:0 auto;padding:1.2rem}
.card{background:#fff;border-radius:14px;padding:1rem 1.1rem;margin-bottom:.8rem;
      box-shadow:0 1px 3px rgba(16,40,50,.08);border-left:5px solid #0b6b7d}
.card.gone{opacity:.5;border-left-color:#b03535}
.row{display:flex;gap:1rem;justify-content:space-between;align-items:flex-start}
a.name{color:#0b6b7d;font-weight:700;font-size:1.05rem;text-decoration:none}
a.name:hover{text-decoration:underline}
.fname{font:12px Consolas,monospace;color:#8b98a1;margin:2px 0 6px}
.card p{margin:0;font-size:.88rem;color:#5c6b75}
.right{text-align:right;flex-shrink:0}
.size{font-size:.8rem;color:#8b98a1;margin-bottom:.4rem}
.btn{display:inline-block;background:#0b6b7d;color:#fff;text-decoration:none;font-weight:700;
     font-size:.85rem;padding:.55rem 1.1rem;border-radius:8px}
.btn:hover{background:#095766}
.btn.dis{background:#9aa7b0;pointer-events:none}
footer{max-width:820px;margin:0 auto;padding:0 1.2rem 2rem;color:#8b98a1;font-size:.8rem}
</style></head><body>
<header><div class="wrap">
  <b>TELECOM FOUNDATION EDUCATION SYSTEM</b>
  <h1>TEFOS Quiz &mdash; Downloads</h1>
  <p>Proposal deck, whitepaper, video script, and the working prototype's documentation.</p>
</div></header>
<main>${rows}</main>
<footer>
  These files are also committed to the <code>arena/01a0ed18-infinitetalk</code> branch,
  so they remain recoverable from git.
</footer>
</body></html>`;
}

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');

  if (url.pathname === '/' || url.pathname === '/index.html') {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    return res.end(index());
  }

  if (url.pathname.startsWith('/d/')) {
    const name = decodeURIComponent(url.pathname.slice(3));
    // Strict whitelist. No path traversal, no directory listing.
    if (!Object.prototype.hasOwnProperty.call(FILES, name)) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('Not found');
    }
    const file = path.join(DIR, name);
    if (!fs.existsSync(file)) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('File missing');
    }
    res.writeHead(200, {
      'content-type': TYPES[path.extname(name)] || 'application/octet-stream',
      'content-length': fs.statSync(file).size,
      'content-disposition': `attachment; filename="${name}"`,
      'x-content-type-options': 'nosniff',
    });
    return fs.createReadStream(file).pipe(res);
  }

  res.writeHead(404, { 'content-type': 'text/plain' });
  res.end('Not found');
}).listen(PORT, HOST, () => {
  console.log(`Downloads on http://${HOST}:${PORT}`);
});
