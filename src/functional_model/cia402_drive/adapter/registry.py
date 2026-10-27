from device_descriptions.cmmt_as.description import CmmtAsDescription
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from .contract import validate_adapter
from .f_kr_cmmt import FKrCmmtAdapter

# BUS selects the functional profile. The current model retains the CMMT-compatible device description.
FACTORIES = {('cia402-drive', 'f_kr_cmmt'): FKrCmmtAdapter}

def create_adapter(device):
    if device['type'] != 'cia402-drive': raise ValueError('Unsupported functional profile')
    profile = CiA402DriveProfile(CmmtAsDescription(device['model']['mode']))
    key = (profile.name, device['model']['type'])
    if key == ('cia402-drive', 'copley_drive_sim'):
        from .copley import CopleyAdapter
        return validate_adapter(CopleyAdapter.open(profile, device['model']['artifact'], device['id']))
    if key not in FACTORIES: raise ValueError(f'Unsupported profile/model combination: {key}')
    return validate_adapter(FACTORIES[key](profile))
