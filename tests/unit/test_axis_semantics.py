"""RF-015 contracts exercised without a NIC, wall-clock sleeps or stored state."""
import unittest

from tests.reference.factory import reference_model as Model
from functional_model.ipc.server import dispatch_request


class Drive:
    def __init__(self, mode=1, referenced=True):
        self.runtime = Model()
        self.adapter = self.runtime.adapter
        self.model = self.adapter.model
        self.od = self.adapter.od
        self.od.write(0x6060, mode)
        self.od.write(0x6081, 100)
        self.od.write(0x6083, 1000)
        self.od.write(0x6084, 1000)
        for cw in (6, 7, 15):
            self.tick(cw)
        self.model.homing_referenced = referenced

    def tick(self, cw=None, count=1, dt=.008):
        if cw is not None:
            self.od.write(0x6040, cw)
        for _ in range(count):
            self.adapter.step(dt)

    def start(self, target=500000):
        self.od.write(0x607A, target)
        self.tick(15)
        self.tick(0x3f)
        self.tick(15)

    def until_stopped(self, limit=5000):
        for _ in range(limit):
            if not self.od.read(0x6041) & 0x100:
                return
            self.tick()
        raise AssertionError("Drive did not reach standstill")

    def write(self, index, value, sub=0, size=4, signed=False):
        return dispatch_request(self.runtime, dict(op="write", index=index,
            subindex=sub, data=value.to_bytes(size, "little", signed=signed).hex()))


class AxisSemanticsTests(unittest.TestCase):
    def drive(self, *args, **kwargs):
        d = Drive(*args, **kwargs)
        self.addCleanup(d.runtime.close)
        return d

    def test_pp_profile_and_target_are_latched(self):
        baseline, changed = self.drive(), self.drive()
        for d in (baseline, changed):
            d.start()
            d.tick(count=20)
        for index, value in ((0x6081, 50), (0x6083, 200), (0x6084, 300),
                             (0x607A, 600000)):
            changed.od.write(index, value)
        for _ in range(30):
            baseline.tick(); changed.tick()
            self.assertEqual(changed.model.actual_position, baseline.model.actual_position)
            self.assertEqual(changed.model.actual_velocity, baseline.model.actual_velocity)
        self.assertEqual(changed.od.read(0x607A), 600000)
        self.assertEqual(changed.model.pp_target_position, .5)

    def test_busy_pp_edge_is_ignored_and_not_queued(self):
        d = self.drive(); d.start(5000)
        d.od.write(0x607A, 8000)
        d.tick(0x3f)
        self.assertEqual(d.model.pp_target_position, .005)
        self.assertFalse(d.od.read(0x6041) & 0x1000)
        d.until_stopped()
        d.tick(count=10)
        self.assertEqual(d.model.actual_position, .005)
        self.assertTrue(d.model.target_reached)
        d.tick(15); d.tick(0x3f)
        self.assertEqual(d.model.pp_target_position, .008)

    def test_out_of_range_next_target_does_not_stop_active_pp(self):
        a,b = self.drive(), self.drive()
        for d in (a,b): d.start()
        b.od.write(0x607A, 2000000)
        for _ in range(10):
            a.tick(); b.tick()
            self.assertEqual(a.model.actual_position, b.model.actual_position)
        self.assertTrue(b.model.pp_active)
        self.assertEqual(b.od.read(0x607A), 2000000)

    def test_new_out_of_range_pp_warns_without_fault_or_motion(self):
        d = self.drive(); d.start(2000000)
        self.assertEqual(d.model.actual_position, 0)
        self.assertFalse(d.model.pp_active)
        self.assertEqual(d.od.read(0x6041) & 0x880, 0x880)
        self.assertFalse(d.od.read(0x6041) & 8)

    def test_pp_next_run_uses_new_profile(self):
        d = self.drive(); d.start(5000)
        d.od.write(0x6081, 50)
        d.until_stopped()
        d.start(30000); d.tick(count=25)
        self.assertLessEqual(d.model.actual_velocity, .05)

    def test_pp_limit_changes_wait_for_next_run(self):
        d = self.drive(); d.start(5000)
        d.od.write(0x607D, 1000, 2)
        d.until_stopped()
        self.assertEqual(d.model.actual_position, .005)
        d.start(6000)
        self.assertFalse(d.model.pp_active)
        d.start(0); d.until_stopped()
        self.assertEqual(d.model.actual_position, 0)

    def test_pp_boundaries_inclusive(self):
        d = self.drive()
        d.od.write(0x607D, 1000, 2)
        d.start(1000); d.until_stopped()
        self.assertEqual(d.model.actual_position, .001)

    def test_pv_limit_stop_requires_neutral_then_inward_request(self):
        d = self.drive(3)
        d.od.write(0x607D, 1000, 2)
        d.od.write(0x60FF, 100); d.tick()
        d.until_stopped()
        position = d.model.actual_position
        self.assertGreaterEqual(position, .001)
        d.tick(count=10)
        self.assertEqual(d.model.actual_position, position)
        d.od.write(0x60FF, -100); d.tick(count=3)
        self.assertEqual(d.model.actual_position, position)
        d.od.write(0x60FF, 0); d.tick()
        d.od.write(0x60FF, -100); d.tick(count=30)
        self.assertLess(d.model.actual_position, .001)
        self.assertFalse(d.od.read(0x6041) & 0x880)

    def test_pv_limit_changes_do_not_change_current_run(self):
        d = self.drive(3)
        d.od.write(0x60FF, 100); d.tick(count=20)
        d.od.write(0x607D, 1000, 2); d.tick(count=20)
        self.assertGreater(d.model.actual_velocity, 0)
        d.od.write(0x60FF, 0); d.tick(); d.until_stopped()
        position=d.model.actual_position
        d.od.write(0x60FF,100);d.tick(count=10)
        self.assertEqual(d.model.actual_position,position)

    def test_velocity_reversal_uses_deceleration_and_zero(self):
        for mode in (3,-3):
            with self.subTest(mode=mode):
                d=self.drive(mode)
                d.od.write(0x6083,2000);d.od.write(0x6084,100)
                if mode==3: d.od.write(0x60FF,100);d.tick(count=20)
                else:d.tick(0x101f,count=20)
                before=d.model.actual_velocity
                if mode==3:d.od.write(0x60FF,-100);d.tick()
                else:d.tick(0x102f)
                self.assertAlmostEqual(d.model.actual_velocity,before-.0008)
                seen_zero=False
                for _ in range(300):
                    d.tick()
                    v=d.model.actual_velocity
                    if v==0:seen_zero=True
                    if v<0:break
                self.assertTrue(seen_zero)
                self.assertLess(d.model.actual_velocity,0)

    def test_jog_both_directions_stop(self):
        d=self.drive(-3);d.tick(0x101f,count=20)
        d.tick(0x103f);d.until_stopped()
        self.assertEqual(d.model.actual_velocity,0)

    def test_mode_request_waits_for_standstill(self):
        d=self.drive(3)
        d.od.write(0x60FF,100);d.tick(count=20)
        d.od.write(0x6060,1);d.tick()
        self.assertEqual(d.od.read(0x6061),3)
        self.assertGreater(d.model.actual_velocity,0)
        d.od.write(0x60FF,0);d.tick();d.until_stopped();d.tick()
        self.assertEqual(d.od.read(0x6061),1)
        self.assertEqual(d.od.read(0x6060),1)

    def test_pp_halt_uses_start_deceleration_and_cancels(self):
        d=self.drive();d.start();d.tick(count=20)
        d.od.write(0x6084,100)
        before=d.model.actual_velocity
        d.tick(0x10f)
        self.assertAlmostEqual(d.model.actual_velocity,before-.008)
        d.od.write(0x6084,200)
        d.until_stopped();position=d.model.actual_position
        self.assertFalse(d.model.target_reached)
        d.tick(15,count=10)
        self.assertEqual(d.model.actual_position,position)
        self.assertFalse(d.od.read(0x6041)&8)

    def test_pv_stop_latches_request_deceleration(self):
        d=self.drive(3);d.od.write(0x60FF,100);d.tick(count=20)
        d.od.write(0x6084,100);d.od.write(0x60FF,0);d.tick()
        before=d.model.actual_velocity
        d.od.write(0x6084,1000);d.tick()
        self.assertAlmostEqual(d.model.actual_velocity,before-.0008)

    def test_halt_clear_does_not_resume_velocity(self):
        d=self.drive(3);d.od.write(0x60FF,100);d.tick(count=20)
        d.tick(0x10f);d.until_stopped()
        position=d.model.actual_position
        d.tick(15,count=10)
        self.assertEqual(d.model.actual_position,position)
        d.od.write(0x60FF,0);d.tick()
        d.od.write(0x60FF,100);d.tick()
        self.assertGreater(d.model.actual_position,position)

    def test_disable_does_not_replay_pp_or_pv(self):
        for mode in (1,3):
            with self.subTest(mode=mode):
                d=self.drive(mode)
                if mode==1:d.start()
                else:d.od.write(0x60FF,100);d.tick()
                d.tick(7)
                position=d.model.actual_position
                d.tick(15,count=10)
                self.assertEqual(d.model.actual_position,position)
                self.assertEqual(d.od.read(0x6041)&0x6f,0x27)

    def test_quick_stop_ramp_state_and_no_auto_enable(self):
        d=self.drive(3);d.od.write(0x60FF,100);d.tick(count=20)
        self.assertEqual(d.write(0x6085,500),{})
        before=d.model.actual_velocity
        d.tick(0xb)
        self.assertEqual(d.od.read(0x6041)&0x6f,0x7)
        self.assertAlmostEqual(d.model.actual_velocity,before-.004)
        d.write(0x6085,1000)
        before=d.model.actual_velocity;d.tick(15)
        self.assertAlmostEqual(d.model.actual_velocity,before-.004)
        d.until_stopped()
        self.assertEqual(d.od.read(0x6041)&0x6f,0x40)
        d.tick(15,count=10)
        self.assertEqual(d.od.read(0x6041)&0x6f,0x40)

    def test_quick_stop_overrides_halt_and_disable_overrides_quick(self):
        d=self.drive();d.start();d.tick(count=20)
        d.tick(0x10f);before=d.model.actual_velocity
        d.write(0x6085,2000);d.tick(0xb)
        self.assertAlmostEqual(d.model.actual_velocity,max(0,before-.016))
        d.tick(7)
        self.assertEqual(d.model.actual_velocity,0)
        self.assertEqual(d.od.read(0x6041)&0x6f,0x23)

    def test_invalid_sdo_settings_abort_without_partial_write(self):
        d=self.drive()
        for index,sub,value,size,signed in ((0x607D,1,2000000,4,True),
                    (0x605A,0,6,2,True),(0x6085,0,0,4,False)):
            with self.subTest(index=hex(index)):
                old=d.od.read(index,sub)
                result=d.write(index,value,sub,size,signed)
                self.assertEqual(result["error"]["kind"],"sdo_abort")
                self.assertEqual(d.od.read(index,sub),old)
                self.assertFalse(d.od.read(0x6041)&8)

    def test_homing_elapsed_time_and_reference_lifetime(self):
        d=self.drive(6,referenced=False)
        d.model.actual_position=.03
        d.tick(0x1f,dt=.03,count=3)
        self.assertFalse(d.model.homing_referenced)
        self.assertEqual(d.model.actual_position,.03)
        d.tick(dt=.01)
        self.assertTrue(d.model.homing_referenced)
        self.assertEqual(d.model.actual_position,0)
        d.tick(7);d.tick(15)
        self.assertTrue(d.model.homing_referenced)

    def test_homing_cancel_on_start_clear_halt_disable(self):
        for cw in (15,0x11f,7):
            with self.subTest(cw=cw):
                d=self.drive(6,referenced=False)
                d.model.actual_position=.03
                d.tick(0x1f)
                d.tick(cw,count=20)
                self.assertFalse(d.model.homing_active)
                self.assertFalse(d.model.homing_referenced)
                self.assertEqual(d.model.actual_position,.03)

    def test_pp_requires_reference_but_pv_does_not(self):
        d=self.drive(referenced=False);d.start()
        self.assertFalse(d.model.pp_active)
        d.od.write(0x6060,3);d.od.write(0x60FF,100);d.tick()
        self.assertGreater(d.model.actual_velocity,0)

    def test_three_axes_do_not_share_execution_state(self):
        a,b,c=[self.drive() for _ in range(3)]
        a.start(3000);b.start(-5000)
        for _ in range(10):a.tick();b.tick();c.tick()
        a.tick(0x10f)
        self.assertGreater(a.model.actual_position,0)
        self.assertLess(b.model.actual_position,0)
        self.assertEqual(c.model.actual_position,0)
        self.assertTrue(b.model.pp_active)

    def test_quick_stop_objects_are_exposed_and_persisted(self):
        d=self.drive()
        entries={(e["index"],e["subindex"]):e for e in d.runtime.describe()["entries"]}
        self.assertEqual(entries[0x605A,0]["initial"],"0200")
        self.assertEqual(entries[0x6085,0]["initial"],"e8030000")
        self.assertFalse(entries[0x6085,0]["rx"])
        self.assertIn("6085:00",d.runtime.parameter_values())
        self.assertIn("605a:00",d.runtime.parameter_values())

    def test_reset_preserves_completed_reference_and_cancels_old_motion(self):
        from tests.reference.state_machine import CiA402State
        d=self.drive();d.start();d.tick(count=5)
        d.model.sm.state=CiA402State.FAULT
        d.tick();position=d.model.actual_position
        d.tick(0x80);d.tick(6);d.tick(7);d.tick(15,count=5)
        self.assertTrue(d.model.homing_referenced)
        self.assertEqual(d.model.actual_position,position)
        self.assertFalse(d.model.pp_active)

    def test_fault_cancels_homing_without_late_completion(self):
        from tests.reference.state_machine import CiA402State
        d=self.drive(6,referenced=False);d.tick(0x1f)
        d.model.sm.state=CiA402State.FAULT;d.tick(count=20)
        self.assertFalse(d.model.homing_referenced)
        self.assertFalse(d.model.homing_active)

    def test_start_held_through_disable_enable_cannot_launch_pp(self):
        d=self.drive();d.start()
        d.tick(0x17);position=d.model.actual_position
        d.tick(0x1f,count=10)
        self.assertEqual(d.model.actual_position,position)
        d.tick(15);d.tick(0x3f)
        self.assertTrue(d.model.pp_active)

    def test_ignored_pp_during_halt_deceleration_is_not_queued(self):
        d=self.drive();d.start();d.tick(count=20)
        d.tick(0x10f);d.od.write(0x607A,700000);d.tick(0x3f)
        d.until_stopped();position=d.model.actual_position
        d.tick(count=10)
        self.assertEqual(d.model.actual_position,position)
        self.assertFalse(d.model.pp_active)

    def test_new_pv_request_immediately_after_stop_is_accepted(self):
        d=self.drive(3);d.od.write(0x60FF,100);d.tick(count=20)
        d.od.write(0x60FF,0);d.tick();d.until_stopped()
        d.od.write(0x60FF,-100);d.tick()
        self.assertLess(d.model.actual_velocity,0)

    def test_pp_completion_zero_window_time_cannot_complete_in_flight(self):
        d=self.drive();d.od.write(0x6068,0);d.start()
        self.assertTrue(d.model.pp_active)
        self.assertFalse(d.model.target_reached)

    def test_velocity_uses_live_acceleration_outside_stop(self):
        d=self.drive(3);d.od.write(0x6083,100)
        d.od.write(0x60FF,100);d.tick()
        before=d.model.actual_velocity
        d.od.write(0x6083,1000);d.tick()
        self.assertAlmostEqual(d.model.actual_velocity,before+.008)

    def test_csp_still_tracks_targets_and_rejects_out_of_range(self):
        d=self.drive(8)
        d.od.write(0x607A,10000);d.tick(count=10)
        self.assertGreater(d.model.actual_position,0)
        d.od.write(0x607A,2000000);position=d.model.actual_position;d.tick()
        self.assertEqual(d.model.actual_position,position)
        self.assertEqual(d.model.actual_velocity,0)

    def test_constant_mode_requests_do_not_restart_pp(self):
        d=self.drive();d.start();d.tick(count=10)
        target=d.model.pp_target_position
        for _ in range(10):
            d.od.write(0x6060,1);d.tick()
            self.assertEqual(d.model.pp_target_position,target)
        self.assertTrue(d.model.pp_active)

    def test_negative_limit_stop_and_recovery(self):
        d=self.drive(-3);d.od.write(0x607D,-1000,1)
        d.tick(0x102f);d.until_stopped();position=d.model.actual_position
        self.assertLessEqual(position,-.001)
        d.tick(0x101f,count=5)
        self.assertEqual(d.model.actual_position,position)
        d.tick(15);d.tick(0x101f,count=30)
        self.assertGreater(d.model.actual_position,-.001)
        self.assertFalse(d.od.read(0x6041)&0x880)


if __name__=="__main__":
    unittest.main()
