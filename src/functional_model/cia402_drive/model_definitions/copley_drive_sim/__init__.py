"""Contract for upstream revision 68978af04ea475cf89e39ae872cdccb5ddc95e4c."""
SIGNATURE = {
    'ControlWord': ('UInt16', 'input'), 'ModesOfOp': ('Int8', 'input'),
    'TargetPosition': ('Int32', 'input'), 'TargetVelocity': ('Int32', 'input'),
    'TargetTorque': ('Int16', 'input'), 'FaultInject': ('Boolean', 'input'),
    'StatusWord': ('UInt16', 'output'), 'ModesDisplay': ('Int8', 'output'),
    'ActualPosition': ('Int32', 'output'), 'ActualVelocity': ('Int32', 'output'),
    'TorqueActual': ('Int16', 'output'), 'AmplifierEvent': ('UInt32', 'output'),
    'ProfileVelocity': ('Float64', 'parameter'),
    'ProfileAcceleration': ('Float64', 'parameter'),
    'TorqueTimeConstant': ('Float64', 'parameter'),
}
STEP_SECONDS = 0.002
