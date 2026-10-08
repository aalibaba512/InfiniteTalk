// potrace_bridge.js — multilayer potrace tracing bridge for tools/vectorize.py
// usage: node potrace_bridge.js <libdir> <out.svg> <layersJsonFile> <paramsJson>
// layersJson: [{"file": "mask.png", "fill": "#rrggbb"}, ...] (back to front)
const fs = require("fs");
const potrace = require(require("path").join(process.argv[2], "node_modules", "potrace"));
const [, , libdir, outSvg, layersFile, paramsJson] = process.argv;
const layers = JSON.parse(fs.readFileSync(layersFile, "utf8"));
const base = JSON.parse(paramsJson || "{}");

function traceOne(file, fill, params) {
  return new Promise((res, rej) =>
    potrace.trace(file, { ...params, color: fill }, (err, svg) =>
      err ? rej(err) : res(svg)));
}

(async () => {
  const paths = [];
  for (const { file, fill } of layers) {
    const svg = await traceOne(file, fill, base);
    const m = svg.match(/<path[^>]*\/?>/g);
    if (m) paths.push(...m);
  }
  fs.writeFileSync(outSvg, "<svg>" + paths.join("\n") + "</svg>");
  console.log("ok", paths.length);
})().catch((e) => { console.error(e); process.exit(1); });
