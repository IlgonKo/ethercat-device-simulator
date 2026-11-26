"""F-KR OD conversion boundary. No second OD or cached parameter values."""
import math


class FKrUnits:
    def __init__(self, od):
        self.od = od
        scale = lambda sub: 10.0 ** -abs(int(od.read(0x2194, sub)))
        position, velocity, acceleration = scale(1), scale(2), scale(3)
        # Linear profiles use m/m/s/m/s²; rotary profiles retain degrees.
        self.scales = {(i, 0): position for i in (0x607A, 0x6064, 0x6067)}
        self.scales.update({(0x607D, 1): position, (0x607D, 2): position})
        self.scales.update({(i, 0): velocity for i in (0x6081, 0x607F, 0x60FF, 0x606C)})
        self.scales.update({(i, 0): acceleration for i in (0x6083, 0x6084, 0x6085)})
        self.scales[0x2183, 12] = velocity * 1000.0

    def read(self, index, subindex=0):
        return self.od.read(index, subindex) * self.scales.get((index, subindex), 1)

    def write(self, index, value, subindex=0):
        raw = value / self.scales.get((index, subindex), 1)
        if not math.isfinite(raw):
            raise ValueError("Nonfinite model output")
        # Remove floating-point noise at exact integer OD boundaries.
        nearest = round(raw)
        if abs(raw-nearest) <= max(1e-9, abs(raw)*1e-14):
            raw = nearest
        self.od.write(index, raw, subindex)
