"""Model access failures; protocol-level Abort translation belongs to the Slave."""
class DeviceRejectedException(ValueError):
    pass

class SdoObjectNotFoundException(KeyError):
    def __init__(self, index, subindex=0):
        self.index, self.subindex = index, subindex
        super().__init__(f'{index:04x}:{subindex:02x}')
