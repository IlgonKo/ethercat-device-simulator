within ;
model SoftESCDoubleActingCylinder
  "Offline prototype: pneumatic 5/2 memory valve and double-acting cylinder"
  parameter Real stroke(unit="m", min=0.001) = 0.100;
  parameter Real piston_diameter(unit="m", min=0.001) = 0.020;
  parameter Real rod_diameter(unit="m", min=0) = 0.008;
  parameter Real moving_mass(unit="kg", min=0.001) = 0.15;
  parameter Real supply_gauge_pressure(unit="Pa", min=0) = 600000;
  parameter Real opposing_force(unit="N") = 0
    "Constant force against extension; not a dynamic external load input";
  parameter Real initial_position(unit="m", min=0) = 0;
  parameter Real sensor_width(unit="m", min=0.00001) = 0.001;

  input Boolean extend_command(start=false)
    "Energize the extension pilot (prototype Boolean actuation)";
  input Boolean retract_command(start=false)
    "Energize the retraction pilot (prototype Boolean actuation)";
  output Real position(unit="m");
  output Real velocity(unit="m/s");
  output Real pressure_cap(unit="Pa") "Absolute chamber pressure";
  output Real pressure_rod(unit="Pa") "Absolute chamber pressure";
  output Real pneumatic_force(unit="N") "Pressure force before friction/load/contact";
  output Boolean retracted_sensor;
  output Boolean extended_sensor;
  output Boolean valve_extended "Latched valve direction, not cylinder position";

protected
  PneumaticCircuits.Sources.PressureSupply supply(p_gauge=supply_gauge_pressure);
  PneumaticCircuits.Sources.Tube supply_tube(L=1.0);
  PneumaticCircuits.Valves.PushButtonValve32 extend_pilot;
  PneumaticCircuits.Valves.PushButtonValve32 retract_pilot;
  PneumaticCircuits.Sources.Tube extend_pilot_tube(L=0.3);
  PneumaticCircuits.Sources.Tube retract_pilot_tube(L=0.3);
  PneumaticCircuits.Valves.DoublePilotValve52 valve(switched_start=false);
  PneumaticCircuits.Sources.Tube cap_tube(L=0.5);
  PneumaticCircuits.Sources.Tube rod_tube(L=0.5);
  PneumaticCircuits.Actuators.DoubleActingCylinder cylinder(
    L=stroke, D=piston_diameter, d=rod_diameter,
    m=moving_mass, F_load=opposing_force, x_start=initial_position);

initial equation
  assert(stroke > 0 and piston_diameter > rod_diameter and rod_diameter >= 0,
    "Invalid cylinder geometry");
  assert(initial_position >= 0 and initial_position <= stroke,
    "Initial position must be inside the stroke");
  assert(sensor_width > 0 and 2*sensor_width < stroke,
    "End sensor windows must not overlap");
  assert(moving_mass > 0 and supply_gauge_pressure >= 0,
    "Invalid moving mass or supply pressure");

equation
  extend_pilot.pressed = extend_command;
  retract_pilot.pressed = retract_command;
  connect(supply.port, supply_tube.port);
  connect(extend_pilot.p1, supply_tube.port);
  connect(retract_pilot.p1, supply_tube.port);
  connect(valve.p1, supply_tube.port);
  connect(extend_pilot.p2, extend_pilot_tube.port);
  connect(valve.p14, extend_pilot_tube.port);
  connect(retract_pilot.p2, retract_pilot_tube.port);
  connect(valve.p12, retract_pilot_tube.port);
  connect(valve.p4, cap_tube.port);
  connect(cylinder.A, cap_tube.port);
  connect(valve.p2, rod_tube.port);
  connect(cylinder.B, rod_tube.port);

  position = cylinder.x;
  velocity = cylinder.v;
  pressure_cap = cylinder.pA;
  pressure_rod = cylinder.pB;
  pneumatic_force = cylinder.F_p;
  retracted_sensor = position <= sensor_width;
  extended_sensor = position >= stroke - sensor_width;
  valve_extended = valve.switched;

  annotation(experiment(StartTime=0, StopTime=4, Tolerance=1e-6, Interval=0.008),
    Documentation(info="<html><p>Prototype composed from the MIT-licensed
    PneumaticCircuits library. Boolean inputs drive its 3/2 pilot valves;
    electrical coil dynamics are not modeled. Both commands OFF preserves the
    5/2 valve direction and does not stop the piston. End stops are compliant,
    so position can slightly exceed the nominal stroke. This is not a validated
    manufacturer model.</p></html>"));
end SoftESCDoubleActingCylinder;
