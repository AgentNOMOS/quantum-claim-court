// Quantum Claim Court — Qollab entry point.
// Exactly ONE bridge call per Run: run_court.callPromising(backend) -> one bare circuit, one backend.run.
// Every later interaction (docket, filters, case files, challenges) is local: no Python call, no quantum job.
import * as L from "./ui/logic.js";
import * as R from "./ui/render.js";
import * as api from "uqcc_app.js_api";

const state = { filter: "ALL", selected: null, started: false, docket: [], byId: {} };

function select(id, scroll) {
  const d = state.byId[id];
  if (!d) return;
  state.selected = id;
  R.renderClaimDetail(d);
  if (state.redrawDocket) state.redrawDocket();
  if (scroll) document.getElementById("scene-e").scrollIntoView({ block: "start" });
}

async function start() {
  if (state.started) return;          // guard: never a second job
  state.started = true;
  const injected = typeof backend !== "undefined" ? backend : undefined; // eslint-disable-line no-undef
  if (injected === undefined || injected === null) {
    R.renderFailure({ status: "refused", message: "No injected backend in this Run. Zero quantum jobs submitted." });
    return;
  }
  R.setStatus("running", "Running ONE quantum job on the injected backend…");
  let raw;
  try {
    raw = await api.run_court.callPromising(injected);
  } catch (e) {
    R.renderFailure({ status: "error", message: `Bridge call failed: ${e && e.message ? e.message : e}`, jobAttempted: false });
    return;
  }
  const parsed = L.parseEnvelope(typeof raw === "string" ? raw : String(raw));
  if (!parsed.ok) {
    R.renderFailure(parsed);
    return;
  }
  const { env, evidence, court, manifest } = parsed;
  state.docket = env.view.docket;
  state.byId = Object.fromEntries(state.docket.map((d) => [d.id, d]));
  R.setStatus("live", `LIVE · ${evidence.backend.name} · ${evidence.jobs_submitted} job · ${evidence.shots_requested} shots · counts from this Run`);
  R.renderDocket(state.docket, select, state);
  R.renderSources(manifest, env.view.authors);
  R.renderBench(state.byId, select);
  R.renderBackend(evidence);
  R.renderCircuit(evidence.circuit.ops);
  R.renderCounts(evidence);
  R.renderChart(evidence);
  R.renderWitnessTable(state.docket, select);
  R.populateSelect(state.docket, select);
  select("C1", false);
  R.renderChallenge(court.challenge);
  R.renderCrossCheck(L.crossCheck(parsed));
  R.renderExport(env.export_text);
}

start();
