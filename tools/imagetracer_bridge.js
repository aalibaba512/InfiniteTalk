// imagetracer_bridge.js — thin Node bridge for tools/vectorize.py
// usage: node imagetracer_bridge.js <lib.js> <rawRGBA> <w> <h> <out.svg> <optsJson>
const fs = require("fs");
const ImageTracer = require(process.argv[2]);
const [, , , rawPath, w, h, outPath, optsJson] = process.argv;
const buf = fs.readFileSync(rawPath);
const imgd = {
  width: +w,
  height: +h,
  data: new Uint8ClampedArray(buf.buffer, buf.byteOffset, buf.length),
};
const opts = JSON.parse(optsJson || "{}");
const svg = ImageTracer.imagedataToSVG(imgd, opts);
fs.writeFileSync(outPath, svg);
console.log("ok");
