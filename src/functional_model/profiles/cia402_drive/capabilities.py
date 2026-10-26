from dataclasses import dataclass

@dataclass(frozen=True)
class DriveCapabilities:
    modes: frozenset[int]
    state_machine_owner: str = 'model'
    dynamic_pdo: bool = False
    arbitrary_state_restore: bool = False
