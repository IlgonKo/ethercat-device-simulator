from copy import deepcopy
from device_descriptions.cpx_ap_i_ec.profile import contract
from device_descriptions.fixture import write_fixture

class Station:
    def __init__(self, device):
        self.device=device
        self.contract=contract(device)
        self.timing=None
    def describe(self):return deepcopy(self.contract)
    def generate_fixture(self, folder):return write_fixture(self.contract,folder)
    def dispatch(self, request):
        raise ValueError('CPX OD is owned by the EtherCAT Slave; use IO snapshot exchange')
    def close(self):pass
