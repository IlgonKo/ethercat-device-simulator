"""CiA402 fixture entry point; shared XML writer lives in device_descriptions."""
from device_descriptions.fixture import write_fixture

def generate_fixture(model, destination):
    return write_fixture(model.describe(), destination)
