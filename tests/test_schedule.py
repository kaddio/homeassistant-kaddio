"""Busy-window tests, incl. back-to-back meetings."""

import importlib.util, pathlib, sys, types, unittest
from datetime import datetime, timedelta, timezone

base = pathlib.Path(__file__).parent.parent / "custom_components" / "kaddio"
pkg = types.ModuleType("kaddio_pkg2"); pkg.__path__ = [str(base)]; sys.modules["kaddio_pkg2"] = pkg
for name in ("models", "schedule"):
    spec = importlib.util.spec_from_file_location(f"kaddio_pkg2.{name}", base / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[f"kaddio_pkg2.{name}"] = mod
    spec.loader.exec_module(mod)
models, sch = sys.modules["kaddio_pkg2.models"], sys.modules["kaddio_pkg2.schedule"]

def t(h, m=0):
    return datetime(2026, 11, 9, h, m, tzinfo=timezone.utc)

def ev(uid, start, end, kind="booking"):
    return models.KaddioEvent(uid, start, end, "x", "", kind)

LEAD = TRAIL = timedelta(minutes=5)
K = sch.DEFAULT_KINDS


class ScheduleTest(unittest.TestCase):
    def test_lead_and_trail(self):
        e = [ev("a", t(10), t(11))]
        self.assertIsNone(sch.is_busy(e, t(9, 54), LEAD, TRAIL, K))
        self.assertIsNotNone(sch.is_busy(e, t(9, 55), LEAD, TRAIL, K))
        self.assertIsNotNone(sch.is_busy(e, t(11, 4), LEAD, TRAIL, K))
        self.assertIsNone(sch.is_busy(e, t(11, 5), LEAD, TRAIL, K))

    def test_back_to_back_has_no_gap(self):
        e = [ev("a", t(10), t(11)), ev("b", t(11, 5), t(12))]
        for minute in range(0, 65):
            now = t(10) + timedelta(minutes=minute)
            self.assertIsNotNone(sch.is_busy(e, now, LEAD, TRAIL, K), minute)

    def test_gap_longer_than_lead_plus_trail_turns_off(self):
        e = [ev("a", t(10), t(11)), ev("b", t(11, 30), t(12))]
        self.assertIsNone(sch.is_busy(e, t(11, 10), LEAD, TRAIL, K))

    def test_lunch_ignored_by_default_but_counted_when_asked(self):
        e = [ev("lunch", t(12), t(13), kind="cal")]
        self.assertIsNone(sch.is_busy(e, t(12, 30), LEAD, TRAIL, K))
        self.assertIsNotNone(sch.is_busy(e, t(12, 30), LEAD, TRAIL, sch.ALL_KINDS))

    def test_next_boundary(self):
        e = [ev("a", t(10), t(11)), ev("lunch", t(9), t(9, 30), kind="cal")]
        self.assertEqual(sch.next_boundary(e, t(8), LEAD, TRAIL, K), t(9, 55))
        self.assertEqual(sch.next_boundary(e, t(10, 1), LEAD, TRAIL, K), t(11, 5))
        self.assertIsNone(sch.next_boundary(e, t(12), LEAD, TRAIL, K))

if __name__ == "__main__":
    unittest.main()
