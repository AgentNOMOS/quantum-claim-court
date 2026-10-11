import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import * as L from "../../app/ui/logic.js";
import { sha256Hex } from "../../app/ui/sha256.js";

const fx = (n) => readFileSync(new URL(`../fixtures/${n}.txt`, import.meta.url), "utf8");

test("sha256 matches node crypto incl. padding edges and UTF-8", () => {
  for (const s of ["", "abc", "a".repeat(55), "a".repeat(56), "a".repeat(64), "Bužek ß ψ ⟩", "x".repeat(20000)]) {
    assert.equal(sha256Hex(s), createHash("sha256").update(s, "utf8").digest("hex"));
  }
});

test("ok envelope parses and every cross-check passes", () => {
  const p = L.parseEnvelope(fx("ok"));
  assert.ok(p.ok);
  const checks = L.crossCheck(p);
  assert.ok(checks.length >= 9);
  for (const c of checks) assert.ok(c.ok, c.label);
});

test("browser hash equals Python digest of the exact evidence line", () => {
  const p = L.parseEnvelope(fx("ok"));
  assert.equal(sha256Hex(p.env.r1_evidence_text), p.env.r1_evidence_sha256);
  assert.equal(sha256Hex(p.env.court_text), p.env.court_sha256);
});

test("bit order: clone A = rightmost bit, clone B = leftmost", () => {
  const d = L.decodeCounts({ "00": 5, "01": 3, "10": 2 });
  assert.deepEqual(d.hits, { A: 7, B: 8, AB: 5 });
  assert.equal(d.shots, 10);
  const row = d.rows.find((r) => r.key === "01");
  assert.equal(row.cloneA, "1");
  assert.equal(row.cloneB, "0");
});

test("decoded hits equal Python's for live fixture", () => {
  const p = L.parseEnvelope(fx("ok"));
  const d = L.decodeCounts(p.evidence.counts);
  for (const k of ["A", "B", "AB"]) assert.equal(d.hits[k], p.evidence.measurement.observables[k].hits);
});

test("tampered evidence text fails the browser cross-check", () => {
  const p = L.parseEnvelope(fx("ok"));
  const k = Object.keys(p.evidence.counts)[0];
  p.env.export_text = p.env.export_text.replace(`"${k}":${p.evidence.counts[k]}`, `"${k}":${p.evidence.counts[k] + 1}`);
  const bad = L.crossCheck(p).filter((c) => !c.ok).map((c) => c.label);
  assert.ok(bad.some((l) => l.includes("R1 evidence SHA-256")));
});

test("failure envelopes are reported, never rendered as data", () => {
  for (const n of ["refused", "error"]) {
    const p = L.parseEnvelope(fx(n));
    assert.equal(p.ok, false);
    assert.equal(p.status, n);
    assert.ok(p.error.length > 5);
  }
  assert.equal(L.parseEnvelope("<<not json>>").ok, false);
  assert.equal(L.parseEnvelope(JSON.stringify({ schema: "other" })).ok, false);
  const p = JSON.parse(fx("ok")); delete p.export_text;
  assert.equal(L.parseEnvelope(JSON.stringify(p)).ok, false);
});

test("challenge lookup covers the whole matrix and labels rewrites", () => {
  const { court } = L.parseEnvelope(fx("ok"));
  const ch = court.challenge;
  assert.equal(ch.matrix.length, ch.statements.length * ch.citations.length * ch.framings.length);
  assert.equal(L.challengeLookup(ch, "S3", "BDEFMS98", "as_stated").verdict, "SUPPORTED");
  assert.equal(L.challengeLookup(ch, "S3", "BDEFMS98", "as_stated").rewrite, null);
  const irr = L.challengeLookup(ch, "S3", "DJ92", "as_stated");
  assert.equal(irr.verdict, "REWRITE");
  assert.match(irr.rewrite, /Bru/);
  assert.equal(L.challengeLookup(ch, "S1", "WZ82", "run_proves").verdict, "REWRITE");
  assert.equal(L.challengeLookup(ch, "S3", "FORGED", "as_stated").verdict, "BLOCK");
  assert.equal(L.challengeLookup(ch, "S9", "x", "y"), null);
});

test("docket verdicts match the court's decisions and frozen R1 decisions", () => {
  const { env, evidence, court } = L.parseEnvelope(fx("ok"));
  const byId = Object.fromEntries(env.view.docket.map((d) => [d.id, d.decision.verdict]));
  for (const d of evidence.decisions) assert.equal(byId[d.id], d.verdict);
  for (const d of court.value_decisions) assert.equal(byId[d.id], d.verdict);
  assert.equal(env.view.docket.length, 18);
});

test("statistical disagreement fixture: C1 and V1 DISPUTED, measurement witness disagrees", () => {
  const { env } = L.parseEnvelope(fx("disputed"));
  const byId = Object.fromEntries(env.view.docket.map((d) => [d.id, d]));
  assert.equal(byId.C1.decision.verdict, "DISPUTED");
  assert.equal(byId.V1.decision.verdict, "DISPUTED");
  assert.equal(byId.V1.witness.measurement, "INCONSISTENT");
  assert.equal(byId.V1.witness.mathematics, "SUPPORTS");
  // literature-only claims are untouched by the measurement
  assert.equal(byId.C3.decision.verdict, "SUPPORTED");
  assert.equal(byId.C3.witness.measurement, "NOT_NEEDED");
});

test("copyText falls back: clipboard -> execCommand -> manual", async () => {
  let selected = 0;
  const sel = () => { selected++; };
  assert.equal(await L.copyText("t", { clipboard: { writeText: async () => {} }, select: sel }), "clipboard");
  assert.equal(await L.copyText("t", { clipboard: { writeText: async () => { throw new Error("denied"); } }, select: sel, execCommand: () => true }), "execCommand");
  assert.equal(await L.copyText("t", { clipboard: undefined, select: sel, execCommand: () => false }), "manual");
  assert.ok(selected >= 2);
});
