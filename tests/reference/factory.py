from unittest.mock import patch
from functional_model.runtime.axis import Model
from functional_model.cia402_drive.profile.profile import CiA402DriveProfile
from device_descriptions.cmmt_as.description import CmmtAsDescription
from .f_kr_cmmt import FKrCmmtAdapter

def reference_model(device=None):
    def factory(d):
        return FKrCmmtAdapter(CiA402DriveProfile(CmmtAsDescription(d["model"]["mode"])))
    with patch("functional_model.runtime.axis.create_adapter", side_effect=factory):
        return Model(device)
