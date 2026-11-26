"""IO signal adapters. Behaviour physics and delay history remain inside FMUs."""
import math
from pathlib import Path
from functional_model.runtime.fmi.runner import Fmi3Runner

CYLINDER_SIGNATURE = {
    **{name:('Float64','parameter') for name in ('stroke','piston_diameter','rod_diameter','moving_mass','sensor_width','supply_gauge_pressure','opposing_force','initial_position')},
    **{name:('Boolean','input') for name in ('extend_command','retract_command')},
    **{name:('Boolean','output') for name in ('extended_sensor','retracted_sensor')},
}
DELAY_SIGNATURE = {'command':('Int16','input'),'feedback':('Int16','output'),'delay_seconds':('Float64','parameter')}
ARTIFACTS = {'pneumatic_double_acting':'SoftESCDoubleActingCylinder-fmi3-web.fmu',
             'analog_delay':'SoftESCAnalogDelay-linux.fmu'}

class FmiIOAdapter:
    def __init__(self, spec, artifact_directory):
        self.kind=spec['preset']['model']
        artifact=Path(artifact_directory)/ARTIFACTS[self.kind]
        if not artifact.is_file():raise FileNotFoundError(f'IO FMU missing: {artifact}; prepare Docker inputs/build artifacts')
        settings=dict(spec['preset']['config'])
        settings.update(spec['instance_config'])
        if self.kind=='pneumatic_double_acting':
            settings.update(extend_command=False,retract_command=False)
            signature=CYLINDER_SIGNATURE
        else:
            settings.setdefault('delay_seconds',.016);settings['command']=0
            signature=DELAY_SIGNATURE
        self.runner=Fmi3Runner(artifact,signature,instance_name=spec['id'],initial_values=settings)

    def initial_outputs(self):
        if self.kind=='pneumatic_double_acting':
            return dict(extended=self.runner.get('extended_sensor'),retracted=self.runner.get('retracted_sensor'))
        return dict(feedback=self.runner.get('feedback'))

    def step(self, inputs, time, dt):
        if not math.isclose(time,self.runner.time,rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError('IO scheduler and FMU time differ')
        if not math.isclose(dt,.008,rel_tol=0,abs_tol=1e-12):raise ValueError('IO FMU requires an 8 ms scheduler step')
        if self.kind=='pneumatic_double_acting':
            # Pass both commands unchanged, including both ON. Interlocks belong above this adapter.
            self.runner.set('extend_command',inputs['extend'])
            self.runner.set('retract_command',inputs['retract'])
        else:self.runner.set('command',inputs['command'])
        self.runner.step(dt)
        return self.initial_outputs()

    def close(self):self.runner.close()
