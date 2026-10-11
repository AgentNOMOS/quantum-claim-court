"""SYNTHETIC test stand-ins for qiskit-ionq backend classes (tests only; never shipped).

They copy the identity surface of qiskit-ionq 1.1.1 (module, class names, MRO, name, `_simulator`,
options.noise_model, a target with the frozen circuit's gates) so the R3b policy can be tested without
qiskit-ionq or a network. scripts/ionq_offline_check.py repeats the key checks against the REAL classes.
`run` never contacts anything: it records the call and returns preset counts (or raises).
"""
import types

from qiskit.providers.basic_provider import BasicSimulator

_TARGET_OPS = BasicSimulator().target.operation_names


class _Res:
    def __init__(self, counts):
        self._c, self.results = counts, [type("R", (), {"shots": sum(counts.values())})()]

    def get_counts(self):
        return self._c


class _Job:
    def __init__(self, r):
        self._r = r

    def result(self):
        return self._r


def _module(cls, module="qiskit_ionq.ionq_backend"):
    cls.__module__ = module
    return cls


class IonQBackend:
    """Stand-in for qiskit_ionq.ionq_backend.IonQBackend."""
    def __init__(self, name, simulator, noise_model="ideal", counts=None, fail=None, ops=None):
        self.name = name
        self._simulator = simulator
        self.options = types.SimpleNamespace(noise_model=noise_model, shots=1024)
        self.target = types.SimpleNamespace(operation_names=list(ops if ops is not None else _TARGET_OPS))
        self.calls = []
        self._counts = counts or {"00": 1250, "01": 360, "10": 350, "11": 40}
        self._fail = fail

    def run(self, circuit, **kw):
        self.calls.append(kw)
        if self._fail:
            raise self._fail
        return _Job(_Res(self._counts))


IonQBackend = _module(IonQBackend)


class IonQSimulatorBackend(IonQBackend):
    def __init__(self, name="ionq_simulator", noise_model="ideal", **kw):
        super().__init__(name, True, noise_model, **kw)


class IonQQPUBackend(IonQBackend):
    def __init__(self, name="ionq_qpu.forte-1", **kw):
        super().__init__(name, False, "ideal", **kw)


IonQSimulatorBackend = _module(IonQSimulatorBackend)
IonQQPUBackend = _module(IonQQPUBackend)
IonQSimulatorBackend.__qualname__ = "IonQSimulatorBackend"
IonQQPUBackend.__qualname__ = "IonQQPUBackend"
IonQBackend.__qualname__ = "IonQBackend"
