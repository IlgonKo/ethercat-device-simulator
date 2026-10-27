"""Minimal in-process model boundary. No network or FMU runtime requirement."""
from typing import Protocol

class DriveAdapter(Protocol):
    profile: object
    od: object
    capabilities: object
    def read_sdo(self, index: int, subindex: int, size: int) -> bytes: ...
    def write_sdo(self, index: int, subindex: int, payload: bytes) -> None: ...
    def apply_outputs(self, payload: bytes) -> None: ...
    def step(self, dt: float) -> None: ...
    def read_inputs(self) -> bytes: ...

def validate_adapter(adapter):
    for name in ('profile', 'od', 'capabilities'):
        if not hasattr(adapter, name): raise TypeError(f'Adapter requires {name}')
    for name in ('read_sdo', 'write_sdo', 'apply_outputs', 'step', 'read_inputs'):
        if not callable(getattr(adapter, name, None)): raise TypeError(f'Adapter requires {name}')
    return adapter
