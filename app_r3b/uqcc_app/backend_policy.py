"""UQCC-R3b backend authorization: positive identification, fail closed.

Allowed (exactly two kinds):
  * builtin_basic_simulator  - Qiskit BasicSimulator, by the FROZEN R1 rule (name "basic_simulator"
                               or class name "BasicSimulator"); unchanged from R1/R2.
  * ionq_remote_simulator    - IonQ's cloud simulator as implemented by qiskit-ionq. ALL must hold:
      1. the class MRO contains qiskit_ionq.*.IonQSimulatorBackend (module checked, not just the name);
      2. the class MRO contains NO IonQQPUBackend;
      3. the backend's own simulator flag (`_simulator`, set by qiskit-ionq) is exactly True;
      4. the name matches ^ionq_simulator(\\.[a-z0-9-]{1,32})?$ (anchored, never a substring test);
      5. options.noise_model is a short plain string (recorded; it selects the simulated noise, not the cost).

Everything else is refused before any job is sent: IonQ QPUs (credits), any other provider, unknown
classes, duck-typed objects, missing or ambiguous metadata. Identities were taken from qiskit-ionq 1.1.1
source (offline). Qollab does not document the Python class it injects; if it differs, the Run is refused
and the refusal message records the observed identity.
"""
import re

KIND_BASIC = "builtin_basic_simulator"
KIND_IONQ_SIM = "ionq_remote_simulator"
IONQ_SIM_CLASS = "IonQSimulatorBackend"
IONQ_QPU_CLASS = "IonQQPUBackend"
IONQ_MODULE_PREFIX = "qiskit_ionq."
IONQ_SIM_NAME = re.compile(r"^ionq_simulator(\.[a-z0-9-]{1,32})?$")
NOISE_MODEL = re.compile(r"^[a-z0-9._-]{1,40}$")
BASIC_NAMES = {"basic_simulator"}       # frozen R1 rule
BASIC_CLASSES = {"BasicSimulator"}      # frozen R1 rule


class Refused(Exception):
    pass


def _name(backend):
    name = getattr(backend, "name", None)
    return name() if callable(name) else name


def _mro(backend):
    return [f"{c.__module__}.{c.__qualname__}" for c in type(backend).__mro__ if c is not object]


def classify(backend):
    """Return a backend_context dict, or raise Refused. Never sends a job."""
    if backend is None:
        raise Refused("No injected backend. Zero jobs submitted.")
    name = _name(backend)
    cls = type(backend)
    mro = _mro(backend)
    observed = f"name={name!r}, class={cls.__module__}.{cls.__qualname__}"
    if not isinstance(name, str) or not name:
        raise Refused(f"Backend identity missing ({observed}). Zero jobs submitted.")

    if name in BASIC_NAMES or cls.__name__ in BASIC_CLASSES:
        if "qpu" in name.lower() or any(m.endswith("." + IONQ_QPU_CLASS) for m in mro):
            raise Refused(f"Ambiguous backend identity ({observed}). Zero jobs submitted.")
        return {"kind": KIND_BASIC, "free_simulator": True, "noise_model": "none (ideal statevector sampling)",
                "ideal_reference_applies": True, "mro": mro}

    ionq_sim = [m for m in mro if m.startswith(IONQ_MODULE_PREFIX) and m.endswith("." + IONQ_SIM_CLASS)]
    ionq_qpu = [m for m in mro if m.endswith("." + IONQ_QPU_CLASS) or m.split(".")[-1] == IONQ_QPU_CLASS]
    if ionq_qpu or "qpu" in name.lower():
        raise Refused(f"IonQ quantum hardware (QPU) is never used by this app: it consumes credits ({observed}). "
                      "Zero jobs submitted.")
    if not ionq_sim:
        raise Refused(f"Backend not positively identified as BasicSimulator or the free IonQ remote simulator "
                      f"({observed}). Zero jobs submitted.")
    if getattr(backend, "_simulator", None) is not True:
        raise Refused(f"IonQ backend does not report itself as a simulator ({observed}). Zero jobs submitted.")
    if not IONQ_SIM_NAME.match(name):
        raise Refused(f"IonQ simulator name not recognised ({observed}). Zero jobs submitted.")
    options = getattr(backend, "options", None)
    noise = getattr(options, "noise_model", None)
    if not isinstance(noise, str) or not NOISE_MODEL.match(noise):
        raise Refused(f"IonQ simulator noise model missing or ambiguous ({observed}, noise_model={noise!r}). "
                      "Zero jobs submitted.")
    return {"kind": KIND_IONQ_SIM, "free_simulator": True, "noise_model": noise,
            "ideal_reference_applies": noise == "ideal", "mro": mro}
