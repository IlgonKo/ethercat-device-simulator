from functional_model.cia402_drive.profile.configured_od import ConfiguredObjectDictionary
from .state_machine import CiA402StateMachine, CiA402State
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PPExecution:
    target: float
    velocity: float
    acceleration: float
    deceleration: float
    limits: tuple[float, float]


@dataclass(frozen=True)
class StopExecution:
    reason: str
    deceleration: float


class VirtualCiA402Servo:
    def __init__(self, cycle_time=0.001, device_profile=None, od=None, units=None):
        self.cycle_time = cycle_time
        if device_profile is None:
            raise ValueError("VirtualCiA402Servo requires an explicit device_profile")
        self.device_profile = device_profile

        self.od = od if od is not None else ConfiguredObjectDictionary(device_profile)
        if units is None:
            raise ValueError("F-KR requires adapter-owned unit conversion")
        self._read = units.read
        self._write = units.write
        self.sm = CiA402StateMachine()

        self.actual_position = 0.0
        self.actual_velocity = 0.0

        self.kp = 5.0
        self.target_reached = False
        self.window_counter = 0
        self.previous_controlword = 0
        self.pp_active = False
        self.pp_target_position = self.actual_position
        self.pp_setpoint_ack = False
        self.halt_active = False
        self.homing_active = False
        self.homing_counter = 0
        self.homing_referenced = False
        self.homing_error = False
        self.software_limit_warning = False
        self.position_target_rejected = False

        self._last_mode_command = int(self.od.read_role("mode_of_operation"))
        self._last_target_position_command = self.od.read_role("target_position")
        self._last_device_reset_command = int(
            self.od.read_role("device_reset_command")
        )
        self._last_parameter_save_command = int(
            self.od.read_role("parameter_save_command")
        )

        self.applied_mode = int(self._read(0x6060))
        self.od.write_internal(0x6061, self.applied_mode)
        self.pp_execution = None
        self.stop_execution = None
        self.active_limits = None
        self.velocity_active = False
        self.velocity_rearm = False
        self.pp_armed = False
        self.homing_elapsed = 0.0
        self.position_window_elapsed = 0.0
        self._last_csp_target_command = self._read(0x607A)

    def _apply_od_commands(self):
        device_reset_command = int(self.od.read_role("device_reset_command"))
        if device_reset_command != self._last_device_reset_command and device_reset_command == 1:
            self._apply_device_reset_response()
        self._last_device_reset_command = device_reset_command
        parameter_save_command = int(self.od.read_role("parameter_save_command"))
        if parameter_save_command != self._last_parameter_save_command and parameter_save_command == 1:
            self.od.write_role("parameter_save_status", 0)
            self.od.write_role("parameter_save_return_code", 0)
            self.od.write_role("parameter_save_return_value", 1)
        self._last_parameter_save_command = parameter_save_command
        # OD command writes never mutate an accepted PP execution.
        self._last_target_position_command = self._read(0x607A)

    def _apply_device_reset_response(self):
        current_position = self.od.read_role("actual_position")
        self.od.reset_non_pdo_configuration()
        self.od.reset_pdo_values()
        self.od.write_role("target_position", current_position)
        self.od.write_role("actual_position", current_position)
        self.od.write_role("statusword", 0x0027)
        self.od.write_role(
            "mode_of_operation_display",
            self.od.read_role("mode_of_operation"),
        )
        self._last_mode_command = int(self.od.read_role("mode_of_operation"))
        self._last_target_position_command = self.od.read_role("target_position")

    def get_statusword(self):
        return self._read(0x6041)

    def model_update(self):
        if not math.isfinite(self.cycle_time) or not 0 < self.cycle_time <= .1:
            raise ValueError("Cycle time must be finite and in (0, 0.1]")
        self._apply_od_commands()
        self.process_cycle()

    def set_mode(self, mode, previous_mode=None):
        # Request only; the cycle applies it at standstill.
        self._write(0x6060, int(mode))

    def set_target_position(self, position, previous_target=None):
        self._write(0x607A, position)
        self._last_target_position_command = position

    def set_software_position_limits(self, negative_limit, positive_limit):
        if negative_limit > positive_limit:
            raise ValueError("Minimum position limit exceeds maximum")
        self._write(0x607D, negative_limit, 1)
        self._write(0x607D, positive_limit, 2)

    def get_software_position_limits(self):
        return {
            "negative_limit": self._read(0x607D, 1),
            "positive_limit": self._read(0x607D, 2),
        }

    def set_position_loop_gain(self, kp):
        self.kp = float(kp)

    def get_position_loop_gain(self):
        return self.kp

    def get_position(self):
        return self._read(0x6064)

    def get_target_position(self):
        return self._read(0x607A)

    def get_velocity(self):
        return self._read(0x606C)

    def is_target_reached(self):
        return self.target_reached

    def stop_at_current_position(self):
        # Cancel execution, not the user's OD settings.
        self.actual_velocity = 0.0
        self.pp_active = False
        self.pp_setpoint_ack = False
        self.pp_execution = None
        self.stop_execution = None
        self.velocity_active = False
        self.velocity_rearm = True
        self.pp_armed = False
        if self.homing_active:
            self.homing_referenced = False
        self.homing_active = False
        self.homing_elapsed = 0.0
        self.window_counter = 0
        self.position_window_elapsed = 0.0
        self.target_reached = False
        self._write_actual_feedback()

    # ---------------------------------
    # CiA402
    # ---------------------------------

    def is_in_position(self):
        target = self.pp_target_position if self.applied_mode == 1 else self._read(0x607A)
        return abs(target - self._read(0x6064)) <= abs(self._read(0x6067))

    def update_target_reached(self):
        if self.is_in_position():
            self.window_counter += 1
        else:
            self.window_counter = 0
            self.target_reached = False

        window_time_ms = self._read(0x6068)

        required_count = max(1,int(window_time_ms /(self.cycle_time *1000)))

        if self.window_counter >= required_count:
            self.target_reached = True

    def _position_command_requires_reference(self):
        return self.applied_mode in {1, 8}

    # ---------------------------------
    # Main Cycle
    # ---------------------------------

    def process_cycle(self):
        cw = int(self._read(0x6040))
        self.halt_active = bool(cw & 0x100)
        old_state = self.sm.state
        self.sm.process(cw)
        if self.sm.state == CiA402State.QUICK_STOP_ACTIVE:
            if old_state != CiA402State.QUICK_STOP_ACTIVE:
                self._begin_stop("quick_stop", self._read(0x6085))
            self._step_stop()
        elif self.sm.state != CiA402State.OPERATION_ENABLED:
            self.stop_at_current_position()
            self._apply_pending_mode()
        else:
            self._apply_pending_mode()
            if self.stop_execution is None and not self.halt_active and self._velocity_input_is_neutral():
                self.velocity_rearm = False
            if not cw & 0x10:
                self.pp_armed = True
                self.pp_setpoint_ack = False
            if self.halt_active and self.applied_mode != 8:
                self.velocity_rearm = True
                if self._is_moving() and self.stop_execution is None:
                    decel = self.pp_execution.deceleration if self.pp_execution else self._read(0x6084)
                    self._begin_stop("halt", decel)
                if self.applied_mode == 1:
                    self.target_reached = False
            if self.stop_execution is not None:
                self._step_stop()
            elif not self.halt_active or self.applied_mode == 8:
                handler = {1: self.process_pp, 3: self.process_pv, -3: self.process_jog,
                           6: self.process_homing, 8: self.process_csp}.get(self.applied_mode)
                if handler:
                    handler()
        self._write_actual_feedback()
        # Clear a limit warning only after a valid recovery has entered the range.
        if (self.pp_active or self.velocity_active) and self.active_limits is not None:
            lo, hi = self.active_limits
            if lo <= self.actual_position <= hi:
                self.software_limit_warning = False
        statusword = self.sm.get_statusword()
        if self.target_reached: statusword |= 1 << 10
        if self.pp_setpoint_ack and self.applied_mode == 1: statusword |= 1 << 12
        if self._is_moving(): statusword |= 1 << 8
        if self._software_limit_is_active(): statusword |= (1 << 7) | (1 << 11)
        if self.homing_referenced: statusword |= 1 << 15
        if self.applied_mode == 6 and self.homing_error: statusword |= 1 << 3
        self.od.write_internal(0x6041, statusword)
        self.od.write_internal(0x6061, self.applied_mode)
        self.previous_controlword = cw

    # ---------------------------------
    # Homing
    # ---------------------------------

    def process_homing(self):
        cw = int(self._read(0x6040))
        if self.homing_active and not cw & 0x10:
            self.homing_active = False
            self.homing_referenced = False
            self.homing_elapsed = 0.0
            self.target_reached = False
            return
        edge = bool(cw & 0x10) and not self.previous_controlword & 0x10
        if edge and not self._is_moving():
            self.homing_active = True
            self.homing_elapsed = 0.0
            self.homing_referenced = False
            self.homing_error = False
            self.target_reached = False
        if not self.homing_active:
            return
        self.homing_elapsed += self.cycle_time
        if self.homing_elapsed + 1e-12 < .1:
            return
        # Coordinate reset, not a simulated travel to zero.
        self.actual_position = 0.0
        self.actual_velocity = 0.0
        self._write(0x607A, 0)
        self.pp_target_position = 0.0
        self.pp_execution = None
        self.active_limits = None
        self._last_target_position_command = 0
        self.homing_active = False
        self.homing_referenced = True
        self.target_reached = True

    # ---------------------------------
    # PP
    # ---------------------------------

    def process_pp(self):
        cw = int(self._read(0x6040))
        edge = bool(cw & 0x10) and not self.previous_controlword & 0x10
        if edge and self.pp_armed and not self._is_moving():
            self.pp_armed = False
            self.target_reached = False
            if not self.homing_referenced:
                return
            target = float(self._read(0x607A))
            limits = self._software_position_limits()
            self.active_limits = limits
            if not limits[0] <= target <= limits[1]:
                self.position_target_rejected = True
                self.software_limit_warning = True
                return
            velocity = abs(float(self._read(0x6081)))
            cap = abs(float(self._read(0x607F))) if target >= self.actual_position else abs(float(self._read(0x2183, 12)))
            if cap > 0:
                velocity = min(velocity, cap)
            self.pp_execution = PPExecution(target, velocity, abs(float(self._read(0x6083))),
                                             abs(float(self._read(0x6084))), limits)
            self.pp_target_position = target
            self.position_target_rejected = False
            self.pp_active = True
            self.pp_setpoint_ack = True
            self.position_window_elapsed = 0.0
        if not self.pp_active:
            return
        profile = self.pp_execution
        target, max_vel = profile.target, profile.velocity
        accel, decel = profile.acceleration, profile.deceleration
        window = abs(float(self._read(0x6067)))
        dt = self.cycle_time

        error = target - self.actual_position
        distance = abs(error)
        if distance <= window and abs(self.actual_velocity) <= max(
            self._acceleration_to_velocity_delta(decel, dt),
            1e-9,
        ):
            self.actual_position = target
            self.actual_velocity = 0.0
            self._write_actual_feedback()
            self._update_pp_completion()
            return

        direction = 1.0 if error >= 0.0 else -1.0
        velocity_toward_target = self.actual_velocity * direction
        position_velocity_toward_target = (
            self.actual_velocity * direction
        )
        decel_position_rate = decel
        stopping_distance = (
            max(position_velocity_toward_target, 0.0) ** 2
            / (2.0 * decel_position_rate)
            if decel_position_rate > 0.0
            else 0.0
        )

        if velocity_toward_target < 0.0:
            desired_velocity = 0.0
            velocity_limit = decel
        elif distance <= stopping_distance:
            desired_velocity = 0.0
            velocity_limit = decel
        else:
            desired_velocity = direction * max_vel
            velocity_limit = accel

        self.actual_velocity = self._move_towards(
            self.actual_velocity,
            desired_velocity,
            self._acceleration_to_velocity_delta(velocity_limit, dt),
        )
        next_position = (
            self.actual_position
            + self.actual_velocity * dt
        )

        if (
            (target - self.actual_position) == 0.0 or
            (target - self.actual_position) * (target - next_position) <= 0.0
        ):
            self.actual_position = target
            self.actual_velocity = 0.0
        else:
            self.actual_position = next_position

        self._write_actual_feedback()
        self._update_pp_completion()

    def _decelerate_to_stop(self):
        decel = abs(float(self._read(0x6084)))
        self.actual_velocity = self._move_towards(
            self.actual_velocity,
            0.0,
            self._acceleration_to_velocity_delta(decel, self.cycle_time),
        )
        self.actual_position += (
            self.actual_velocity
            * self.cycle_time
        )

    def _move_towards(self, current, target, max_delta):
        if max_delta <= 0.0:
            return current

        delta = target - current
        if abs(delta) <= max_delta:
            return target

        return current + max_delta * (1.0 if delta > 0.0 else -1.0)

    def _write_actual_feedback(self):
        self._write(0x6064, self.actual_position)
        self._write(0x606C, self.actual_velocity)


    @staticmethod
    def _acceleration_to_velocity_delta(acceleration, dt):
        return float(acceleration) * float(dt)

    # ---------------------------------
    # PV
    # ---------------------------------

    def process_pv(self):
        target = float(self._read(0x60FF))
        cap = abs(float(self._read(0x607F))) if target >= 0 else abs(float(self._read(0x2183, 12)))
        if cap > 0:
            target = max(-cap, min(cap, target))
        self._process_velocity(target)

    # ---------------------------------
    # Jog
    # ---------------------------------

    def process_jog(self):
        cw = int(self._read(0x6040))
        positive, negative = bool(cw & 0x10), bool(cw & 0x20)
        target = 0.0 if positive == negative else (1 if positive else -1) * self._jog_velocity_limit(cw)
        self._process_velocity(target)

    def _jog_velocity_limit(self, controlword):
        profile_velocity = abs(float(self._read(0x6081)))
        positive_limit = abs(float(self._read(0x607F)))
        negative_limit = abs(float(self._read(0x2183, 0x0C)))
        configured_limits = [
            value for value in (profile_velocity, positive_limit, negative_limit)
            if value > 0.0
        ]
        max_velocity = min(configured_limits) if configured_limits else 0.0

        if controlword & (1 << 12):
            speed_factor = 1.0
        elif controlword & (1 << 11):
            speed_factor = 0.25
        else:
            speed_factor = 0.5

        return max_velocity * speed_factor

    def _limit_jog_velocity_at_software_limit(self, target_velocity):
        target_velocity = float(target_velocity)
        if abs(target_velocity) <= 1e-12:
            return 0.0

        negative_limit, positive_limit = self._software_position_limits()
        if target_velocity > 0.0 and self.actual_position >= positive_limit:
            return 0.0
        if target_velocity < 0.0 and self.actual_position <= negative_limit:
            return 0.0
        return target_velocity

    def _software_position_limits(self):
        limits = float(self._read(0x607D, 1)), float(self._read(0x607D, 2))
        if limits[0] > limits[1]:
            raise ValueError("Minimum position limit exceeds maximum")
        return limits

    def _position_target_is_within_software_limits(self, position):
        negative_limit, positive_limit = self._software_position_limits()
        position = float(position)
        return negative_limit <= position <= positive_limit

    def _actual_position_exceeds_software_limits(self):
        negative_limit, positive_limit = self._software_position_limits()
        return (
            self.actual_position < negative_limit or
            self.actual_position > positive_limit
        )

    def _software_limit_is_active(self):
        return self.software_limit_warning

    def _is_moving(self):
        return (abs(float(self.actual_velocity)) > 1e-9 or self.pp_active
                or self.homing_active or self.velocity_active or self.stop_execution is not None)

    # ---------------------------------
    # CSP
    # ---------------------------------

    def process_csp(self):

        if self.sm.get_statusword() != 0x0027:
            return

        target = self._read(0x607A)
        if target != self._last_csp_target_command:
            if not self.homing_referenced:
                self._write(0x607A, self._last_csp_target_command)
            elif not self._position_target_is_within_software_limits(target):
                self.software_limit_warning = True
                self.stop_at_current_position()
                self._write(0x607A, self.actual_position)
            self._last_csp_target_command = self._read(0x607A)

        if self.halt_active:
            self._decelerate_to_stop()
            self._write_actual_feedback()
            self.target_reached = abs(self.actual_velocity) <= 1e-9
            return

        if not self.homing_referenced:
            self.target_reached = False
            self._decelerate_to_stop()
            self._write_actual_feedback()
            return

        target = self._read(0x607A)
        profile_vel = abs(float(self._read(0x6081)))
        positive_limit = abs(float(self._read(0x607F)))
        negative_limit = abs(float(self._read(0x2183, 0x0C)))
        max_profile_vel = positive_limit
        if target < self.actual_position and negative_limit > 0:
            max_profile_vel = negative_limit
        max_vel = min(profile_vel, max_profile_vel) if max_profile_vel > 0 else profile_vel
        accel = self._read(0x6083)
        decel = self._read(0x6084)

        error = target - self.actual_position

        desired_velocity = self.kp * error
        desired_velocity = max(
            min(desired_velocity, max_vel),
            -max_vel,
        )

        delta_v = (desired_velocity - self.actual_velocity)

        if abs(desired_velocity) > abs(self.actual_velocity):
            limit = accel
        else:
            limit = decel

        max_delta_v = self._acceleration_to_velocity_delta(
            limit,
            self.cycle_time,
        )

        delta_v = max(min(delta_v, max_delta_v), -max_delta_v)

        self.actual_velocity += delta_v

        self.actual_position += (
            self.actual_velocity
            * self.cycle_time
        )

        self._write(0x6064, self.actual_position)

        self._write(0x606C, self.actual_velocity)

        self.update_target_reached()

    def _apply_pending_mode(self):
        requested = int(self._read(0x6060))
        if requested == self.applied_mode or self._is_moving():
            return
        self.applied_mode = requested
        self._last_mode_command = requested
        self.pp_execution = None
        self.pp_setpoint_ack = False
        self.target_reached = False
        self.active_limits = None
        self.homing_error = False

    def _begin_stop(self, reason, deceleration):
        if self.stop_execution is not None and reason != "quick_stop":
            return
        deceleration = abs(float(deceleration))
        if not math.isfinite(deceleration) or deceleration <= 0:
            raise ValueError("A stop requires positive finite deceleration")
        self.stop_execution = StopExecution(reason, deceleration)
        self.pp_active = False
        self.pp_setpoint_ack = False
        self.pp_armed = False
        self.velocity_active = False
        self.velocity_rearm = True
        if self.homing_active:
            self.homing_referenced = False
        self.homing_active = False
        self.homing_elapsed = 0.0
        self.target_reached = False

    def _step_stop(self):
        stop = self.stop_execution
        if stop is None:
            return
        self.actual_velocity = self._move_towards(self.actual_velocity, 0,
            self._acceleration_to_velocity_delta(stop.deceleration, self.cycle_time))
        self.actual_position += self.actual_velocity * self.cycle_time
        if abs(self.actual_velocity) <= 1e-9:
            self.actual_velocity = 0.0
            self.stop_execution = None
            self.pp_execution = None
            if stop.reason == "quick_stop":
                self.sm.finish_quick_stop()
            elif not self.halt_active and self._velocity_input_is_neutral():
                self.velocity_rearm = False

    def _update_pp_completion(self):
        if abs(self.actual_position - self.pp_target_position) <= abs(self._read(0x6067)) and abs(self.actual_velocity) <= 1e-9:
            self.position_window_elapsed += self.cycle_time
        else:
            self.position_window_elapsed = 0.0
            return
        if self.position_window_elapsed + 1e-12 >= max(0, self._read(0x6068)) / 1000:
            self.target_reached = True
            self.pp_active = False

    def _process_velocity(self, target):
        if self.velocity_rearm:
            if abs(target) <= 1e-12:
                self.velocity_rearm = False
            return
        if target == 0:
            if self.velocity_active or abs(self.actual_velocity) > 1e-9:
                self._begin_stop("stop", self._read(0x6084))
                self._step_stop()
            return
        if not self.velocity_active:
            self.active_limits = self._software_position_limits()
            self.velocity_active = True
        lo, hi = self.active_limits
        outside_direction = ((target > 0 and self.actual_position >= hi)
                             or (target < 0 and self.actual_position <= lo))
        if outside_direction:
            self.software_limit_warning = True
            self._begin_stop("limit", self._read(0x6084))
            self._step_stop()
            return
        # Reverse using the deceleration ramp, explicitly reaching zero first.
        reversing = target * self.actual_velocity < 0
        desired = 0.0 if reversing else target
        accel, decel = float(self._read(0x6083)), float(self._read(0x6084))
        ramp = decel if reversing or abs(desired) < abs(self.actual_velocity) else accel
        self.actual_velocity = self._move_towards(self.actual_velocity, desired,
            self._acceleration_to_velocity_delta(ramp, self.cycle_time))
        self.actual_position += self.actual_velocity * self.cycle_time
        self.target_reached = abs(self.actual_velocity - target) <= 1e-9

    def _velocity_input_is_neutral(self):
        cw = int(self._read(0x6040))
        if self.applied_mode == 3:
            return self._read(0x60FF) == 0
        if self.applied_mode == -3:
            return bool(cw & 0x10) == bool(cw & 0x20)
        return self._read(0x60FF) == 0 and not cw & 0x30
