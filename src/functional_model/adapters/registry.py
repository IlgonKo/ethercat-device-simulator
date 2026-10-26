from device_descriptions.cmmt_as.description import CmmtAsDescription
from functional_model.profiles.cia402_drive.profile import CiA402DriveProfile
from .contract import validate_adapter
from .f_kr_internal import FKrInternalAdapter

# External BUS identity is deliberately retained while the internal profile is generic.
FACTORIES = {('cia402-drive', 'f_kr_internal'): FKrInternalAdapter}

def create_adapter(device):
    if device['type'] != 'cmmt-as': raise ValueError('Unsupported EtherCAT device description')
    profile = CiA402DriveProfile(CmmtAsDescription(device['model']['mode']))
    key = (profile.name, device['model']['type'])
    if key not in FACTORIES: raise ValueError(f'Unsupported profile/model combination: {key}')
    return validate_adapter(FACTORIES[key](profile))
