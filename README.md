# EtherCAT Device Simulator

Software-based EtherCAT device simulation, starting with CMMT drives and reusable CiA 402 models.

The intended architecture connects a PySOEM master over EtherCAT to a software ESC and slave communication stack, with device behavior provided by our existing object dictionary and CiA 402 modules.

KickCAT is the initial candidate for the software ESC and slave stack. Integration and PySOEM interoperability are pending validation.
