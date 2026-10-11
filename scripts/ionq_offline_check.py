"""Offline IonQ interface check for UQCC-R3b (needs qiskit-ionq; NO network: sockets are disabled).

Uses the REAL qiskit-ionq backend classes with a dummy token. It never submits a job: the one
backend.run call is intercepted on the instance and returns synthetic counts. It checks:
  * backend_policy accepts IonQSimulatorBackend (noise models ideal / aria-1 / forte-1),
  * backend_policy refuses IonQQPUBackend (ionq_qpu, forte-1, forte-enterprise-1),
  * the frozen circuit passes the frozen gate-support check on the IonQ target,
  * qiskit-ionq serialises the frozen circuit as ONE ionq.circuit.v1 payload (gates listed),
  * the whole bridge produces evidence that verify_uqcc_r3b.py accepts, with exactly one run call.

This is an interface check. It is NOT an IonQ run and proves nothing about Qollab's live IonQ service.

Usage: python scripts/ionq_offline_check.py <staged_r3b_package_dir>
"""
import contextlib
import io
import json
import socket
import subprocess
import sys
import tempfile


def _no_network(*a, **k):
    raise RuntimeError("network disabled in offline check")


def main(stage):
    socket.socket.connect = _no_network          # belt and braces: no request can leave this process
    socket.create_connection = _no_network
    sys.path.insert(0, stage)
    from qiskit_ionq import IonQProvider, helpers
    from uqcc_r1 import app as r1_app, circuit
    from uqcc_app import backend_policy, js_api

    out = {}
    prov = IonQProvider(token="offline-dummy-no-network")
    qc = circuit.build()
    for nm in ("qpu", "qpu.forte-1", "qpu.forte-enterprise-1", "qpu.aria-1"):
        be = prov.get_backend(nm)
        try:
            backend_policy.classify(be)
            out[nm] = "ACCEPTED (DEFECT)"
        except backend_policy.Refused:
            out[nm] = "REFUSED"
    for noise in ("ideal", "aria-1", "forte-1"):
        be = prov.get_backend("simulator")
        be.set_options(noise_model=noise)
        ctx = backend_policy.classify(be)
        out[f"simulator/{noise}"] = f"ACCEPTED kind={ctx['kind']} ideal_reference={ctx['ideal_reference_applies']}"
    be = prov.get_backend("simulator")
    out["gate_support_check"] = r1_app.check_gate_support(be, qc)
    payload = helpers.qiskit_to_ionq(qc, be)
    p = json.loads(payload) if isinstance(payload, str) else payload
    gates = p["input"]["circuit"]
    out["serialisation"] = {"type": p.get("type"), "gate_count": len(gates),
                            "gates": [g["gate"] + ("(ctrl)" if "controls" in g or "control" in g else "") for g in gates]}

    be.set_options(noise_model="forte-1")
    calls = []

    class _Res:
        results = [type("R", (), {"shots": 2000})()]

        def get_counts(self):
            return {"00": 1250, "01": 360, "10": 350, "11": 40}   # synthetic noisy-looking counts

    def fake_run(circ, **kw):
        calls.append((circ.num_qubits, kw))
        return type("J", (), {"result": lambda self: _Res()})()

    be.run = fake_run
    js_api._reset_for_tests()
    with contextlib.redirect_stdout(io.StringIO()):
        env = json.loads(js_api.run_court(be))
    out["bridge_status"] = env["status"]
    out["run_calls"] = len(calls)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(env["export_text"])
    ver = subprocess.run([sys.executable, "-I", f"{stage}/verifier/verify_uqcc_r3b.py", fh.name, stage],
                         capture_output=True, text=True)
    rep = json.loads(ver.stdout)
    out["verifier"] = {"exit": ver.returncode, "status": rep["status"], "backend": rep.get("backend"),
                       "value_verdicts": rep.get("value_verdicts"), "c1": rep.get("c1_verdict")}
    print(json.dumps(out, indent=1))
    ok = (all(out[n] == "REFUSED" for n in ("qpu", "qpu.forte-1", "qpu.forte-enterprise-1", "qpu.aria-1"))
          and out["run_calls"] == 1 and out["bridge_status"] == "ok" and ver.returncode in (0, 2)
          and out["serialisation"]["type"] == "ionq.circuit.v1")
    print("OFFLINE_IONQ_INTERFACE_CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
