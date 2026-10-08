// vt_wasm.js — node wrapper for the vtracer 1.0 WASM engine.
// usage: node vt_wasm.js INPUT OUTPUT '{"simplify":2,...}'
const { convertFileSync } = require("@visioncortex/vtracer");
const [,, inp, out, opts] = process.argv;
convertFileSync(inp, out, JSON.parse(opts || "{}"));
