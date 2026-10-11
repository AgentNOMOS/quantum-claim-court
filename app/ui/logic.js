// Pure logic for the Quantum Claim Court UI (no DOM). Tested in Node.
// Evidence texts arrive from Python as exact strings. This module PARSES them for display and
// cross-checks, but never re-serialises them: the export shown to the user is Python's own text.
import { sha256Hex } from "./sha256.js";

export const VERDICTS = {
  SUPPORTED: { label: "Supported", cls: "v-supported", gloss: "All required witnesses agree within the stated scope." },
  DISPUTED: { label: "Disputed", cls: "v-disputed", gloss: "Mathematics and/or this run's measurement disagree with the claim." },
  INSUFFICIENT: { label: "Insufficient", cls: "v-insufficient", gloss: "The available evidence cannot decide the claim." },
  REWRITE: { label: "Rewrite", cls: "v-rewrite", gloss: "Close to defensible, but over-reaching or mis-cited." },
  BLOCK: { label: "Blocked", cls: "v-block", gloss: "Contradicts an established result or cites a defective reference." },
};

export const WITNESS = {
  SUPPORTS: { label: "Supports", tone: "good" },
  CONSISTENT: { label: "Consistent", tone: "good" },
  CONTRADICTS: { label: "Contradicts", tone: "bad" },
  INCONSISTENT: { label: "Disagrees", tone: "bad" },
  FAILS: { label: "Reference fails", tone: "bad" },
  INSUFFICIENT: { label: "Not established", tone: "warn" },
  MISSING: { label: "Missing", tone: "warn" },
  SILENT: { label: "Silent", tone: "muted" },
  NOT_NEEDED: { label: "Not needed", tone: "muted" },
  CONTEXT: { label: "Context only", tone: "muted" },
};

export function parseEnvelope(raw) {
  let env;
  try {
    env = typeof raw === "string" ? JSON.parse(raw) : null;
  } catch (e) {
    return { ok: false, error: "The Python bridge returned text that is not JSON." };
  }
  if (!env || env.schema !== "uqcc-r2-envelope/1") return { ok: false, error: "Unexpected bridge response (schema)." };
  if (env.status !== "ok") return { ok: false, error: env.message || "Run failed.", status: env.status, jobAttempted: !!env.job_attempted };
  for (const k of ["r1_evidence_text", "r1_evidence_sha256", "court_text", "court_sha256", "manifest_text", "export_text", "view"]) {
    if (!(k in env)) return { ok: false, error: `Bridge response lacks ${k}.` };
  }
  let evidence, court, manifest;
  try {
    evidence = JSON.parse(env.r1_evidence_text);
    court = JSON.parse(env.court_text);
    manifest = JSON.parse(env.manifest_text);
  } catch (e) {
    return { ok: false, error: "Evidence text is not valid JSON." };
  }
  return { ok: true, env, evidence, court, manifest };
}

export function extractBlock(exportText, name) {
  const lines = exportText.split("\n").map((l) => (l.endsWith("\r") ? l.slice(0, -1) : l));
  const shaLine = lines.find((l) => l.startsWith(`${name}_SHA256=`));
  const b = lines.indexOf(`${name}_BEGIN`);
  const e = lines.indexOf(`${name}_END`);
  if (!shaLine || b < 0 || e !== b + 2) return null;
  return { sha: shaLine.split("=", 2)[1], line: lines[b + 1] };
}

// Bit order (frozen R1): key = clone[1] clone[0]; clone A = clbit 0 = RIGHTMOST character.
export function decodeCounts(counts) {
  const rows = Object.keys(counts).sort().map((key) => ({ key, n: counts[key], cloneA: key[1], cloneB: key[0] }));
  const shots = rows.reduce((s, r) => s + r.n, 0);
  const hits = {
    A: rows.filter((r) => r.cloneA === "0").reduce((s, r) => s + r.n, 0),
    B: rows.filter((r) => r.cloneB === "0").reduce((s, r) => s + r.n, 0),
    AB: counts["00"] || 0,
  };
  return { rows, shots, hits };
}

export function crossCheck(parsed, hash = sha256Hex) {
  const { env, evidence, court } = parsed;
  const checks = [];
  const add = (label, ok, detail) => checks.push({ label, ok: !!ok, detail });
  const r1 = extractBlock(env.export_text, "UQCC_R1_EVIDENCE");
  const r2 = extractBlock(env.export_text, "UQCC_R2_COURT");
  add("Export contains both evidence blocks", r1 && r2, r1 && r2 ? "R1 evidence + R2 court addendum" : "block missing");
  if (r1) {
    const h = hash(r1.line);
    add("R1 evidence SHA-256 recomputed in browser", h === r1.sha && h === env.r1_evidence_sha256, h.slice(0, 16) + "…");
    add("Exported R1 line is byte-identical to the Python text", r1.line === env.r1_evidence_text, `${r1.line.length} characters`);
  }
  if (r2) {
    const h = hash(r2.line);
    add("Court addendum SHA-256 recomputed in browser", h === r2.sha && h === env.court_sha256, h.slice(0, 16) + "…");
  }
  add("Court addendum is bound to this R1 evidence", court.r1_evidence_sha256 === env.r1_evidence_sha256, "r1_evidence_sha256 field");
  add("Manifest SHA-256 matches the evidence", hash(env.manifest_text) === evidence.manifest_sha256, "frozen offline manifest");
  const dec = decodeCounts(evidence.counts);
  add("Counts sum to the requested shots", dec.shots === evidence.shots_requested, `${dec.shots} / ${evidence.shots_requested}`);
  add("All bitstrings are 2-bit binary", dec.rows.every((r) => /^[01]{2}$/.test(r.key)), dec.rows.map((r) => r.key).join(" "));
  const obs = evidence.measurement && evidence.measurement.observables;
  add("Clone A / B / joint hits re-decoded from raw counts",
    obs && ["A", "B", "AB"].every((k) => obs[k].hits === dec.hits[k]),
    `A=${dec.hits.A} B=${dec.hits.B} AB=${dec.hits.AB}`);
  add("Exactly one quantum job in this Run", evidence.jobs_submitted === 1, `jobs_submitted=${evidence.jobs_submitted}`);
  return checks;
}

export function challengeLookup(challenge, s, c, f) {
  const row = challenge.matrix.find((m) => m[0] === s && m[1] === c && m[2] === f);
  if (!row) return null;
  return { verdict: row[3], reason: challenge.reasons[row[4]], rewrite: row[3] === "SUPPORTED" ? null : challenge.statement_rewrite[s] };
}

export function verdictCounts(docket) {
  const out = {};
  for (const d of docket) out[d.decision.verdict] = (out[d.decision.verdict] || 0) + 1;
  return out;
}

export function fmtFraction(estimate) {
  return estimate; // already "hits/shots" from Python
}

// Copy with graceful fallback for sandboxed frames (clipboard API often blocked, origin null).
export async function copyText(text, env) {
  try {
    if (env.clipboard && env.clipboard.writeText) {
      await env.clipboard.writeText(text);
      return "clipboard";
    }
  } catch (e) { /* fall through */ }
  try {
    env.select();
    if (env.execCommand && env.execCommand("copy")) return "execCommand";
  } catch (e) { /* fall through */ }
  env.select();
  return "manual";
}
