// Test-only stand-in for Qollab's `uqcc_app.js_api` module (mapped in via an import map).
// Returns fixture strings produced by the REAL Python bridge (dev/make_fixtures.py).
globalThis.__bridgeCalls = globalThis.__bridgeCalls || [];
const fx = globalThis.__FIXTURE || "ok";
const base = globalThis.__FIXTURE_BASE || "/dev/fixtures/";

export const run_court = {
  async callPromising(backend, ...rest) {
    globalThis.__bridgeCalls.push({ fn: "run_court", nargs: 1 + rest.length, backendIsMock: !!(backend && backend.mock) });
    if (fx === "reject") throw new Error("PythonError: simulated bridge failure");
    if (fx === "garbage") return "<<not json>>";
    const r = await fetch(base + fx + ".txt");
    return await r.text();
  },
};
