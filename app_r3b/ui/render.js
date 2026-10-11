// DOM rendering for the Quantum Claim Court. All data goes through textContent (never innerHTML).
import { VERDICTS, WITNESS, decodeCounts, challengeLookup, verdictCounts, copyText } from "./logic.js";

const $ = (id) => document.getElementById(id);

export function h(tag, attrs = {}, ...kids) {
  const el = tag === "svg" || attrs.__svg ? document.createElementNS("http://www.w3.org/2000/svg", tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "__svg" || v === undefined || v === null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.setAttribute("class", v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
const svg = (tag, attrs = {}, ...kids) => h(tag, { ...attrs, __svg: true }, ...kids);

function verdictBadge(v) {
  const meta = VERDICTS[v] || { label: v, cls: "" };
  return h("span", { class: `verdict ${meta.cls}`, title: meta.gloss }, meta.label);
}
function chip(code) {
  const w = WITNESS[code] || { label: code, tone: "muted" };
  return h("span", { class: `chip t-${w.tone}`, "data-code": code }, w.label);
}

export function setStatus(kind, text) {
  const el = $("run-status");
  el.className = `status status-${kind}`;
  $("run-status-text").textContent = text;
}

// ------------------------------------------------------------------ failure
export function renderFailure(f) {
  setStatus("failed", f.status === "refused" ? "Run refused — no quantum job submitted" : "Run failed — no live evidence");
  const box = $("failure");
  box.hidden = false;
  box.replaceChildren(
    h("h2", {}, f.status === "refused" ? "The court cannot sit: run refused" : "The court cannot sit: run failed"),
    h("p", {}, f.error || f.message || "Unknown failure."),
    h("p", {}, f.status === "refused"
      ? "Zero quantum jobs were submitted. Nothing on this page is a measurement."
      : (f.jobAttempted ? "One job was attempted and failed. It is NOT retried and there is NO fallback simulator."
        : "It is unknown whether a job reached the backend. It is NOT retried and there is NO fallback simulator.")),
    h("p", {}, "Start a new Run in Qollab with the built-in simulator or a free IonQ remote simulator selected. "
      + "IonQ quantum computers (hardware, credits) are always refused."));
  for (const id of ["docket", "witness-table", "citation-bench", "sources"]) {
    $(id).replaceChildren(h("p", { class: "placeholder" }, "No ruling: this Run produced no evidence."));
  }
  $("export").value = "No evidence: this Run produced no measurement.";
}

// ------------------------------------------------------------------ scene A
export function renderDocket(docket, onSelect, state) {
  const counts = verdictCounts(docket);
  const filters = $("docket-filters");
  const order = ["ALL", "SUPPORTED", "DISPUTED", "INSUFFICIENT", "REWRITE", "BLOCK", "MEASUREMENT"];
  const label = (k) => k === "ALL" ? `All (${docket.length})`
    : k === "MEASUREMENT" ? `Needs measurement (${docket.filter((d) => d.needs_measurement).length})`
      : `${VERDICTS[k].label} (${counts[k] || 0})`;
  const draw = () => {
    filters.replaceChildren(...order.map((k) => h("button", {
      type: "button", "aria-pressed": state.filter === k ? "true" : "false", "data-filter": k,
      onclick: () => { state.filter = k; draw(); },
    }, label(k))));
    const shown = docket.filter((d) => state.filter === "ALL" ? true
      : state.filter === "MEASUREMENT" ? d.needs_measurement : d.decision.verdict === state.filter);
    $("docket").replaceChildren(...shown.map((d) => h("li", {
      class: `docket-item${state.selected === d.id ? " is-selected" : ""}`, "data-id": d.id, "data-verdict": d.decision.verdict,
    }, h("button", { type: "button", onclick: () => onSelect(d.id, true) },
      h("span", { class: "d-head" }, h("span", { class: "d-id" }, d.id), verdictBadge(d.decision.verdict)),
      h("span", { class: "d-text" }, d.text),
      h("span", { class: "d-tags" },
        d.needs_measurement ? h("span", { class: "tag tag-meas" }, "needs measurement")
          : h("span", { class: "tag tag-lit" }, "literature / mathematics"),
        d.addendum ? h("span", { class: "tag tag-add" }, "R2 addendum") : null)))));
    if (!shown.length) $("docket").replaceChildren(h("li", { class: "placeholder" }, "No claims with this verdict in this Run."));
  };
  state.redrawDocket = draw;
  draw();
}

// ------------------------------------------------------------------ scene B
const PRIMARY = ["WZ82", "BH96", "BDEFMS98"];
const STATEMENT_TEXT = {
  S_NO_PERFECT_UNIVERSAL_CLONING: "Perfect cloning of an unknown quantum state is impossible.",
  S_APPROX_UNIVERSAL_COPIER_EXISTS: "An approximate universal copier with input-independent quality exists.",
  S_OPTIMAL_UNIVERSAL_1TO2_FIDELITY_5_6: "5/6 is the maximal fidelity of universal 1→2 cloning.",
  S_CLONING_GATE_NETWORK: "A gate network produces two imperfect copies of an arbitrary qubit.",
  S_NM_CLONING_OPTIMALITY_PROVED: "Optimality of N→M cloning machines is proved.",
};

export function renderSources(manifest, authors) {
  const cards = PRIMARY.map((sid) => {
    const s = manifest.sources.find((x) => x.id === sid);
    const lv = s.levels;
    const level = (k, label) => h("li", { class: lv[k].value ? "lv-yes" : "lv-no" },
      `${label}: ${lv[k].value ? "yes" : "no"}`, lv[k].how ? h("span", { class: "detail" }, ` — ${lv[k].how}${lv[k].utc ? ` (${lv[k].utc})` : ""}`) : null);
    return h("article", { class: "source", "data-source": sid },
      h("h3", {}, s.title),
      h("dl", {},
        h("dt", {}, "Authors"), h("dd", {}, (authors[sid] || [s.first_author]).join(", ")),
        h("dt", {}, "Year"), h("dd", {}, String(s.year)),
        h("dt", {}, "Venue"), h("dd", {}, `${s.venue} ${s.volume}, ${s.pages}`),
        h("dt", {}, "DOI"), h("dd", { class: "mono" }, s.doi)),
      h("ul", { class: "levels" },
        level("SOURCE_METADATA_VERIFIED", "Metadata verified"),
        level("SOURCE_ABSTRACT_CHECKED", "Abstract text checked"),
        level("SOURCE_TEXT_VERIFIED", "Full text reviewed")),
      ...s.statements.map((st) => h("div", {},
        h("p", {}, h("strong", {}, "Supports: "), STATEMENT_TEXT[st.statement] || st.statement,
          h("span", { class: "detail" }, ` (${st.basis === "TITLE_TEXT" ? "title level" : "abstract level"})`)),
        h("blockquote", { class: "quote" }, `“${st.quote}”`))),
      sid === "BH96" ? h("p", { class: "note" }, "Not credited with 5/6 or optimality: its checked abstract states neither.") : null);
  });
  $("sources").replaceChildren(...cards);
}

const BENCH = [
  ["C3", "Valid reference", "Bruß et al. 1998 cited for the 5/6 optimum: the abstract states it."],
  ["RT6", "Fabricated DOI", "Crossref returned 404 for this DOI: the publication does not exist."],
  ["RT10", "Wrong DOI ↔ title", "The title is Bužek & Hillery's, but the DOI belongs to Cory et al., “Experimental Quantum Error Correction”."],
  ["RT5", "Genuine but irrelevant", "Deutsch & Jozsa 1992 is real, but it is about quantum algorithms, not cloning."],
  ["RT7", "Genuine, text does not establish it", "Bužek & Hillery 1996 is relevant, but its checked abstract does not state the 5/6 optimum."],
];
export function renderBench(byId, onSelect) {
  $("citation-bench").replaceChildren(...BENCH.map(([id, kind, why]) => {
    const d = byId[id];
    return h("div", { class: "bench-row", "data-id": id },
      h("span", { class: "bench-kind" }, kind),
      h("span", { class: "why" }, why, " ", h("a", { href: "#scene-e", onclick: (e) => { e.preventDefault(); onSelect(id, true); } }, `Open ${id}`)),
      verdictBadge(d.decision.verdict));
  }));
}

// ------------------------------------------------------------------ scene C
export const BACKEND_KIND = {
  builtin_basic_simulator: "Qollab built-in simulator (Qiskit BasicSimulator, ideal, free)",
  ionq_remote_simulator: "IonQ remote simulator (free; noise model, not hardware)",
};

export function renderBackend(ev, court) {
  const b = ev.backend;
  const ctx = court.backend_context;
  $("backend-context").hidden = false;
  $("backend-context").className = `notice ${ctx.ideal_reference_applies ? "notice-ideal" : "notice-noisy"}`;
  $("backend-context").replaceChildren(h("strong", {}, ctx.ideal_reference_applies ? "Ideal reference applies. " : "Noise-model simulator. "),
    ctx.interpretation);
  $("backend-card").replaceChildren(h("h3", {}, "This Run"), h("dl", { class: "kv" },
    h("dt", {}, "Backend"), h("dd", { class: "mono", id: "backend-name" }, `${b.name} (${b.class})`),
    h("dt", {}, "Backend type"), h("dd", { id: "backend-kind" }, BACKEND_KIND[ctx.kind] || ctx.kind),
    h("dt", {}, "Noise model"), h("dd", { class: "mono", id: "noise-model" }, ctx.noise_model),
    h("dt", {}, "Quantum jobs"), h("dd", { id: "jobs" }, `${ev.jobs_submitted} (one bare QuantumCircuit; no retry, no fallback)`),
    h("dt", {}, "Shots"), h("dd", {}, String(ev.shots_requested)),
    h("dt", {}, "Input state"), h("dd", {}, `|ψ⟩ = Rz(${ev.input_state.phi})·Ry(${ev.input_state.theta})|0⟩`),
    h("dt", {}, "Circuit"), h("dd", {}, `${ev.circuit.metrics.qubits} qubits, ${ev.circuit.metrics.clbits} classical bits, depth ${ev.circuit.metrics.depth}, `
      + Object.entries(ev.circuit.metrics.ops).map(([k, v]) => `${v} ${k}`).join(", ")),
    h("dt", {}, "Runtime"), h("dd", {}, `Python ${ev.runtime.python}, Qiskit ${ev.runtime.qiskit}`)));
}

export function renderCircuit(ops) {
  const lanes = 3, cols = [], last = [0, 0, 0];
  for (const op of ops) {
    const qs = op.qubits, lo = Math.min(...qs), hi = Math.max(...qs);
    let c = 0;
    for (let q = lo; q <= hi; q++) c = Math.max(c, last[q]);
    for (let q = lo; q <= hi; q++) last[q] = c + 1;
    cols.push([c, op]);
  }
  const W = 50, X0 = 74, Y0 = 34, DY = 52, ncol = Math.max(...last);
  const width = X0 + ncol * W + 50, height = Y0 + (lanes - 1) * DY + 62;
  const y = (q) => Y0 + q * DY, x = (c) => X0 + c * W + W / 2;
  const g = [];
  const names = ["q0 · A", "q1 · B", "q2 · M"];
  for (let q = 0; q < lanes; q++) {
    g.push(svg("text", { x: 6, y: y(q) + 5, "font-size": 13, "font-family": "system-ui, sans-serif", fill: "#1d1b16" }, names[q]));
    g.push(svg("line", { x1: X0 - 8, y1: y(q), x2: width - 10, y2: y(q), stroke: "#4a463d", "stroke-width": 1.4 }));
  }
  const box = (cx, cy, label, fill) => [
    svg("rect", { x: cx - 19, y: cy - 14, width: 38, height: 28, rx: 4, fill, stroke: "#1d1b16", "stroke-width": 1 }),
    svg("text", { x: cx, y: cy + 4, "text-anchor": "middle", "font-size": 11, "font-family": "system-ui, sans-serif", fill: "#fff" }, label)];
  const ang = (p) => Number(p).toFixed(2);
  for (const [c, op] of cols) {
    const cx = x(c);
    if (op.name === "ry" || op.name === "rz") {
      const neg = Number(op.params[0]) < 0;
      g.push(...box(cx, y(op.qubits[0]), `${op.name === "ry" ? "Ry" : "Rz"}`, neg ? "#1f5f7a" : (op.qubits[0] === 0 ? "#6b3fa0" : "#7a2e1d")));
      g.push(svg("text", { x: cx, y: y(op.qubits[0]) + 26, "text-anchor": "middle", "font-size": 9, "font-family": "system-ui, sans-serif", fill: "#4a463d" }, ang(op.params[0])));
    } else if (op.name === "cx" || op.name === "cry") {
      const [ct, tg] = op.qubits;
      g.push(svg("line", { x1: cx, y1: y(ct), x2: cx, y2: y(tg), stroke: "#1d1b16", "stroke-width": 1.4 }));
      g.push(svg("circle", { cx, cy: y(ct), r: 5, fill: "#1d1b16" }));
      if (op.name === "cx") {
        g.push(svg("circle", { cx, cy: y(tg), r: 11, fill: "#fff", stroke: "#1d1b16", "stroke-width": 1.4 }));
        g.push(svg("line", { x1: cx - 11, y1: y(tg), x2: cx + 11, y2: y(tg), stroke: "#1d1b16", "stroke-width": 1.4 }));
        g.push(svg("line", { x1: cx, y1: y(tg) - 11, x2: cx, y2: y(tg) + 11, stroke: "#1d1b16", "stroke-width": 1.4 }));
      } else {
        g.push(...box(cx, y(tg), "Ry", "#7a2e1d"));
        g.push(svg("text", { x: cx, y: y(tg) + 26, "text-anchor": "middle", "font-size": 9, "font-family": "system-ui, sans-serif", fill: "#4a463d" }, ang(op.params[0])));
      }
    } else if (op.name === "measure") {
      g.push(...box(cx, y(op.qubits[0]), "M", "#1d1b16"));
      g.push(svg("text", { x: cx + 22, y: y(op.qubits[0]) - 16, "font-size": 10, "font-family": "system-ui, sans-serif", fill: "#4a463d" }, `c${op.clbits[0]}`));
    }
  }
  const legend = svg("text", { x: 6, y: height - 6, "font-size": 10, "font-family": "system-ui, sans-serif", fill: "#6f695c" },
    "purple: input prep · rust: machine prep · black: copy (4 CNOT) · teal: undo input · M: measure");
  $("circuit").replaceChildren(svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
    "aria-label": `Circuit with ${ops.length} operations on 3 qubits` }, svg("title", {}, "Bužek–Braunstein–Hillery–Bruß cloning circuit"), ...g, legend));
}

export function renderCounts(ev) {
  const dec = decodeCounts(ev.counts);
  const all = ["00", "01", "10", "11"].map((k) => ({ key: k, n: ev.counts[k] || 0 }));
  $("counts").replaceChildren(h("h3", {}, "Raw counts (this Run)"),
    h("table", { class: "counts" },
      h("thead", {}, h("tr", {}, h("th", {}, "bitstring"), h("th", {}, "clone A"), h("th", {}, "clone B"), h("th", {}, "count"))),
      h("tbody", {}, ...all.map((r) => h("tr", { "data-key": r.key },
        h("td", { class: "mono" }, r.key), h("td", {}, r.key[1] === "0" ? "matches |ψ⟩" : "differs"),
        h("td", {}, r.key[0] === "0" ? "matches |ψ⟩" : "differs"), h("td", { class: "num" }, String(r.n)))))),
    h("p", { class: "note" }, `Bit order: key = clone[1] clone[0]. Clone A is the rightmost bit, clone B the leftmost. Total ${dec.shots} shots. `
      + "“11” (both clones wrong) has exact probability 0 for this circuit."));
}

export function renderChart(ev) {
  const o = ev.measurement.observables, lo = 0.5, hi = 1.0;
  const pct = (v) => `${((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * 100}%`;
  const rows = [["A", "Clone A"], ["B", "Clone B"], ["AB", "Joint (both clones)"]].map(([k, name]) => {
    const r = o[k], exact = k === "AB" ? 2 / 3 : 5 / 6;
    const l = Number(r.ci_low), u = Number(r.ci_high), est = Number(r.estimate_dec);
    return h("div", { class: "fid-row", "data-obs": k },
      h("div", { class: "fid-label" }, h("strong", {}, name),
        h("span", {}, `${r.estimate} = ${r.estimate_dec} · 99% CI [${r.ci_low}, ${r.ci_high}] · exact ${r.expected} · `,
          h("span", { class: `chip ${r.contains_expected ? "t-good" : "t-bad"}` }, r.contains_expected ? "interval contains exact" : "interval EXCLUDES exact"))),
      h("div", { class: "fid-track", role: "img", "aria-label": `${name}: measured ${r.estimate_dec}, interval ${r.ci_low} to ${r.ci_high}, exact ${r.expected}` },
        h("span", { class: "fid-ci", style: `left:${pct(l)};width:calc(${pct(u)} - ${pct(l)})` }),
        h("span", { class: "fid-exact", style: `left:${pct(exact)}`, title: `exact ${r.expected}` }),
        h("span", { class: "fid-dot", style: `left:${pct(est)}`, title: `measured ${r.estimate_dec}` }),
        h("span", { class: "fid-perfect", title: "perfect copy (1.0)" })));
  });
  $("fid-chart").replaceChildren(h("h3", {}, "Measured fidelity vs exact prediction"),
    h("div", { class: "fid" }, ...rows),
    h("div", { class: "fid-axis", "aria-hidden": "true" }, h("span", {}, "0.50"), h("span", {}, "0.75"), h("span", {}, "1.00")),
    h("div", { class: "legend" },
      h("span", {}, h("i", { style: "background:#7a2e1d;border-radius:50%" }), "measured"),
      h("span", {}, h("i", { style: "background:rgba(122,46,29,.28);border:1px solid #7a2e1d" }), "99% family-wise interval"),
      h("span", {}, h("i", { style: "border-left:3px solid #1f5f7a" }), "exact (5/6, 5/6, 2/3)"),
      h("span", {}, h("i", { style: "border-left:2px dashed #9b1c1c" }), "perfect copy = 1 (impossible for unknown states)")));
}

// ------------------------------------------------------------------ scene D
export function renderWitnessTable(docket, onSelect) {
  const head = h("div", { class: "wt-row wt-head", "aria-hidden": "true" },
    h("span", {}, "Claim"), h("span", {}, "Literature"), h("span", {}, "Mathematics"), h("span", {}, "Measurement"), h("span", {}, "Verdict"));
  $("witness-table").replaceChildren(head, ...docket.map((d) => h("button", {
    type: "button", class: "wt-row", "data-id": d.id, onclick: () => onSelect(d.id, true),
    "aria-label": `${d.id}: literature ${d.witness.literature}, mathematics ${d.witness.mathematics}, measurement ${d.witness.measurement}, verdict ${d.decision.verdict}`,
  }, h("span", { class: "wt-claim" }, h("strong", {}, d.id), " ", d.text),
    chip(d.witness.literature), chip(d.witness.mathematics), chip(d.witness.measurement),
    h("span", { class: "wt-verdict" }, verdictBadge(d.decision.verdict)))));
}

// ------------------------------------------------------------------ scene E
export function populateSelect(docket, onSelect) {
  const sel = $("claim-select");
  sel.replaceChildren(...docket.map((d) => h("option", { value: d.id }, `${d.id} — ${VERDICTS[d.decision.verdict].label}: ${d.text.slice(0, 70)}${d.text.length > 70 ? "…" : ""}`)));
  sel.disabled = false;
  sel.onchange = () => onSelect(sel.value, false);
}

const LIT_EXPLAIN = { NOT_NEEDED: "No citation needed: the claim is about this circuit or is judged by a rule." };
export function renderClaimDetail(d) {
  $("claim-select").value = d.id;
  const ev = d.decision.evidence;
  const w = (cls, title, code, text) => h("div", { class: `case-w ${cls}` }, h("h4", {}, title, " ", chip(code)), h("p", { class: "mono" }, text));
  $("claim-detail").replaceChildren(
    h("div", { class: "d-head" }, h("span", { class: "d-id" }, `Case ${d.id}${d.addendum ? " · R2 addendum" : ""}`), verdictBadge(d.decision.verdict)),
    h("p", { class: "case-claim" }, `“${d.text}”`),
    d.cites.length ? h("p", {}, h("strong", {}, "Cited: "), d.cites.map((c) => `${c.first_author} (${c.year}), “${c.title}”, doi:${c.doi}`).join("; "))
      : h("p", { class: "note" }, "No reference cited."),
    h("div", { class: "case-grid" },
      w("w-lit", "Literature", d.witness.literature, ev.literature === "NOT_REQUIRED" ? LIT_EXPLAIN.NOT_NEEDED : ev.literature),
      w("w-math", "Mathematics", d.witness.mathematics, ev.mathematics === "NOT_APPLICABLE" ? "Not applicable to this claim." : ev.mathematics),
      w("w-meas", "Measurement (this Run)", d.witness.measurement, ev.measurement === "NOT_USED" ? "Not used: this claim is not decided by measurement." : ev.measurement)),
    h("p", { class: "case-reason" }, h("strong", {}, "Ruling: "), d.decision.reason),
    d.rewrite ? h("div", { class: "rewrite" }, h("strong", {}, "Permissible revised claim"), h("p", {}, d.rewrite)) : null);
}

export function renderChallenge(challenge) {
  // rows: statements [id, asserts, label]; citations [id, label, cite]; framings [id, label, overreach]
  const fill = (id, rows, labelIdx, sel) => {
    const el = $(id);
    el.replaceChildren(...rows.map((r) => h("option", { value: r[0] }, r[labelIdx])));
    el.value = sel; el.disabled = false;
  };
  fill("ch-statement", challenge.statements, 2, "S3");
  fill("ch-citation", challenge.citations, 1, "DJ92");
  fill("ch-framing", challenge.framings, 1, "as_stated");
  const update = () => {
    const s = $("ch-statement").value, c = $("ch-citation").value, f = $("ch-framing").value;
    const r = challengeLookup(challenge, s, c, f);
    $("challenge-out").replaceChildren(h("div", { class: "local-result", "data-verdict": r.verdict },
      h("div", { class: "d-head" }, h("span", { class: "badge-local" }, "LOCAL EVALUATION · no new quantum job"), verdictBadge(r.verdict)),
      h("p", { class: "case-reason" }, r.reason),
      r.rewrite ? h("div", { class: "rewrite" }, h("strong", {}, "What the court would accept"), h("p", {}, r.rewrite)) : null));
  };
  for (const id of ["ch-statement", "ch-citation", "ch-framing"]) $(id).onchange = update;
  update();
}

// ------------------------------------------------------------------ scene F
export function renderCrossCheck(checks) {
  $("crosscheck").replaceChildren(...checks.map((c) => h("li", { class: c.ok ? "ok" : "bad" }, c.label, " ", h("span", { class: "detail" }, `(${c.detail})`))));
}

export function renderExport(text) {
  const ta = $("export");
  ta.value = text;
  const msg = $("copy-msg");
  const select = () => { ta.focus(); ta.select(); ta.setSelectionRange(0, ta.value.length); };
  $("btn-select").disabled = false;
  $("btn-copy").disabled = false;
  $("btn-select").onclick = () => { select(); msg.textContent = "Selected. Press Ctrl+C / ⌘C to copy."; };
  $("btn-copy").onclick = async () => {
    const how = await copyText(ta.value, {
      clipboard: navigator.clipboard, select,
      execCommand: (c) => document.execCommand && document.execCommand(c),
    });
    msg.textContent = how === "clipboard" ? "Copied to clipboard (exact text)."
      : how === "execCommand" ? "Copied (fallback method). Paste into evidence.txt."
        : "Clipboard blocked in this frame. Text is selected: press Ctrl+C / ⌘C.";
    msg.dataset.method = how;
  };
}
