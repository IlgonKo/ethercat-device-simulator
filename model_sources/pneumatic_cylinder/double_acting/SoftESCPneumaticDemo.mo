within ;
model SoftESCPneumaticDemo
  "Self-running two-roundtrip scenario for Modelica tools"
  SoftESCDoubleActingCylinder cylinder;
  output Real position(unit="m") = cylinder.position;
  output Real pressure_cap(unit="Pa") = cylinder.pressure_cap;
  output Real pressure_rod(unit="Pa") = cylinder.pressure_rod;
  output Boolean retracted_sensor = cylinder.retracted_sensor;
  output Boolean extended_sensor = cylinder.extended_sensor;
equation
  cylinder.extend_command = (time >= 0.4 and time < 0.52)
                         or (time >= 2.0 and time < 2.12);
  cylinder.retract_command = (time >= 1.2 and time < 1.32)
                          or (time >= 2.8 and time < 2.92);
  annotation(experiment(StartTime=0, StopTime=4, Tolerance=1e-6, Interval=0.001));
end SoftESCPneumaticDemo;
