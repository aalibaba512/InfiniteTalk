#!/usr/bin/env python3
"""
vectorize_app.py — tiny web UI for tools/vectorize.py (vtracer engine).

    python3 tools/vectorize_app.py            # http://0.0.0.0:7860

Drag & drop an image, pick a quality preset, get a finest-shape SVG with a
side-by-side preview and one-click download. Everything runs locally.
"""

import io
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vectorize import MODES, vectorize  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vectorize — finest-shape raster → SVG</title>
<style>
:root{color-scheme:dark;--bg:#0d1117;--panel:#161b22;--line:#30363d;--txt:#e6edf3;
--dim:#8b949e;--acc:#7c5cff;--ok:#3fb950}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,sans-serif;
background:var(--bg);color:var(--txt)}
header{padding:18px 24px;border-bottom:1px solid var(--line);display:flex;
align-items:baseline;gap:12px;flex-wrap:wrap}
header h1{font-size:18px;margin:0}header .sub{color:var(--dim);font-size:12px}
main{max-width:1200px;margin:0 auto;padding:24px}
#drop{border:2px dashed var(--line);border-radius:12px;padding:36px;text-align:center;
color:var(--dim);cursor:pointer;background:var(--panel);transition:.15s}
#drop.over{border-color:var(--acc);color:var(--txt);background:#1b2030}
#drop b{color:var(--txt)}
.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:16px 0}
.controls label{color:var(--dim);font-size:12px;display:flex;flex-direction:column;gap:4px}
select,input[type=number],input[type=color]{background:var(--panel);color:var(--txt);
border:1px solid var(--line);border-radius:8px;padding:7px 10px;font:inherit}
button{background:var(--acc);border:0;color:#fff;font:inherit;font-weight:600;
padding:10px 20px;border-radius:8px;cursor:pointer}
button:disabled{opacity:.45;cursor:wait}
button.ghost{background:transparent;border:1px solid var(--line);color:var(--txt)}
#status{color:var(--dim);min-height:20px;margin:8px 0}
#stats{color:var(--ok);font-size:12px;margin-bottom:12px;white-space:pre-wrap}
.panes{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pane{background:var(--panel);border:1px solid var(--line);border-radius:12px;
overflow:hidden;display:none}
.pane h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);
margin:0;padding:10px 14px;border-bottom:1px solid var(--line)}
.stage{height:520px;display:flex;align-items:center;justify-content:center;overflow:auto;
background:repeating-conic-gradient(#1c2129 0% 25%,#14181f 0% 50%) 0 0/24px 24px}
.stage img{max-width:100%;max-height:100%;object-fit:contain}
@media(max-width:800px){.panes{grid-template-columns:1fr}}
footer{color:var(--dim);font-size:12px;margin-top:24px;text-align:center}
</style></head><body>
<header><h1>⚡ Vectorize</h1>
<span class="sub">finest-shape raster → SVG · engine: visioncortex/vtracer (MIT) ·
patched pipeline: supersampling + tuned spline fitting</span></header>
<main>
<div id="drop">Drop an image here or <b>click to browse</b><br>
<small>PNG · JPG · WEBP · up to 32 MB — processed 100% locally</small></div>
<input type="file" id="file" accept="image/*" hidden>
<div class="controls">
<label>Quality preset<select id="mode"></select></label>
<label>Supersample<input type="number" id="ss" min="1" max="4" placeholder="auto" style="width:74px"></label>
<label>Palette colors<input type="number" id="pal" min="0" step="1" placeholder="auto" style="width:84px"></label>
<label>Background<input type="color" id="bg" value="#ffffff"></label>
<label>&nbsp;<button id="go" disabled>Vectorize →</button></label>
<label>&nbsp;<button id="dl" class="ghost" style="display:none">Download SVG</button></label>
</div>
<div id="status"></div><div id="stats"></div>
<div class="panes">
<div class="pane" id="p-orig"><h2>Original (raster)</h2><div class="stage"><img id="orig"></div></div>
<div class="pane" id="p-vec"><h2>Vectorized (SVG)</h2><div class="stage"><img id="vec"></div></div>
</div>
<footer>tools/vectorize.py — InfiniteTalk toolkit · presets:
finest (RMSE 9.3) · balanced (12.2) · compact (16.2) vs stock tracing</footer>
<script>
const MODES = __MODES__;
const $=id=>document.getElementById(id);
const sel=$("mode");
for(const [k,v] of Object.entries(MODES)){
  const o=document.createElement("option");o.value=k;o.textContent=k;
  if(k==="finest")o.selected=true;sel.appendChild(o);
}
let file=null,svgText=null;
const drop=$("drop");
drop.onclick=()=>$("file").click();
$("file").onchange=e=>setFile(e.target.files[0]);
["dragover","dragenter"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add("over")}));
["dragleave","drop"].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove("over")}));
drop.addEventListener("drop",e=>setFile(e.dataTransfer.files[0]));
function setFile(f){
  if(!f||!f.type.startsWith("image/"))return;
  file=f;svgText=null;$("dl").style.display="none";$("stats").textContent="";
  drop.innerHTML=`Loaded <b>${f.name}</b> (${(f.size/1048576).toFixed(2)} MB) — drop another to replace`;
  $("orig").src=URL.createObjectURL(f);
  $("p-orig").style.display="block";$("p-vec").style.display="none";
  $("go").disabled=false;
}
$("go").onclick=async()=>{
  if(!file)return;
  const fd=new FormData();fd.append("file",file);fd.append("mode",sel.value);
  if($("ss").value)fd.append("supersample",$("ss").value);
  if($("pal").value)fd.append("palette",$("pal").value);
  fd.append("bg",$("bg").value);
  $("go").disabled=true;$("status").textContent="Vectorizing… (finest mode can take a few seconds)";
  try{
    const r=await fetch("/vectorize",{method:"POST",body:fd});
    const j=await r.json();
    if(!r.ok||j.error){throw new Error(j.error||r.statusText)}
    svgText=j.svg;
    $("vec").src=URL.createObjectURL(new Blob([svgText],{type:"image/svg+xml"}));
    $("p-vec").style.display="block";$("dl").style.display="";
    $("status").textContent="Done ✓";
    $("stats").textContent=`${j.stats.paths.toLocaleString()} paths · ${j.stats.colors} colors · `+
      `${(j.stats.bytes/1024).toFixed(0)} KB · traced at ${j.stats.supersample}× · ${j.stats.seconds}s`;
  }catch(e){$("status").textContent="✗ "+e.message}
  $("go").disabled=false;
};
$("dl").onclick=()=>{
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([svgText],{type:"image/svg+xml"}));
  a.download=(file.name.replace(/\\.[^.]+$/,"")||"vectorized")+".svg";a.click();
};
</script></main></body></html>
"""


@app.get("/")
def index():
    modes = {k: v["help"] for k, v in MODES.items()}
    return PAGE.replace("__MODES__", str(modes).replace("'", '"'))


@app.post("/vectorize")
def vectorize_endpoint():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify(error="no image uploaded"), 400
    mode = request.form.get("mode", "finest")
    if mode not in MODES:
        return jsonify(error=f"unknown mode '{mode}'"), 400

    kwargs = dict(mode=mode, quiet=True, bg=request.form.get("bg", "auto"))
    if request.form.get("supersample"):
        kwargs["supersample"] = int(request.form["supersample"])
    if request.form.get("palette"):
        kwargs["palette"] = int(request.form["palette"])

    name = secure_filename(f.filename) or "upload.png"
    try:
        data = f.read()
        in_path = Path(app.instance_path) / "uploads"
        in_path.mkdir(parents=True, exist_ok=True)
        src = in_path / name
        src.write_bytes(data)
        stats = vectorize(src, src.with_suffix(".svg"), **kwargs)
        svg = src.with_suffix(".svg").read_text()
    except Exception:
        return jsonify(error=traceback.format_exc(limit=3)), 500
    return jsonify(svg=svg, stats=stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
