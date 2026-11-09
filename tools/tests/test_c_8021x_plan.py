#!/usr/bin/env python3
"""tools/c_8021x_plan.py 的单元测试（仅标准库）。

运行：python3 -m unittest discover -s tools/tests -v
"""
import ipaddress
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import c_address_plan as cap   # noqa: E402
import c_8021x_plan as auth   # noqa: E402


def _mk(rules, scenario, **kw):
    base = next(r for r in rules if r.scenario == scenario)
    data = dict(
        scenario=base.scenario, ssid=base.ssid, method=base.method,
        pre_vlan=base.pre_vlan, pre_subnet=base.pre_subnet,
        post_vlan=base.post_vlan, post_subnet=base.post_subnet,
        radius_attrs=base.radius_attrs,
    )
    data.update(kw)
    return auth.AuthRule(**data)


class TestDesign(unittest.TestCase):
    def setUp(self):
        self.rules = auth.build_rules()

    def test_default_passes(self):
        self.assertEqual(auth.check(self.rules), [])

    def test_six_scenarios(self):
        self.assertEqual(len(self.rules), 6)

    def test_isolation_subnet_is_free(self):
        iso = ipaddress.ip_network(auth.ISOLATION_SUBNET)
        for row in cap.all_rows():
            self.assertFalse(row.subnet.overlaps(iso), row.building)

    def test_isolation_vlan_not_in_planning(self):
        self.assertNotIn(auth.ISOLATION_VLAN, {r.vlan for r in cap.all_rows()})

    def test_radius_servers_in_datacenter(self):
        dc = next(r.subnet for r in cap.all_rows() if r.building == "数据中心服务器")
        for name, ip in auth.RADIUS_SERVERS:
            self.assertIn(ipaddress.ip_address(ip), dc, name)

    def test_all_rules_start_in_isolation(self):
        for r in self.rules:
            self.assertEqual(r.pre_vlan, auth.ISOLATION_VLAN, r.scenario)

    def test_wireless_ssid_vlan_matches_design(self):
        by_ssid = {r.ssid: r.post_vlan for r in self.rules if r.ssid != "—"}
        self.assertEqual(by_ssid["ECUST-EDU"], "500")
        self.assertEqual(by_ssid["ECUST-STU"], "510")

    def test_every_rule_sends_vlan_attr(self):
        for r in self.rules:
            self.assertTrue(any("VLAN" in a for a in r.radius_attrs), r.scenario)

    def test_simulation_gap_reported(self):
        gaps = auth.simulation_gaps()
        self.assertTrue(any("未建模" in g for g in gaps), gaps)


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.rules = auth.build_rules()

    def test_missing_vlan_attr_detected(self):
        bad = list(self.rules)
        bad[0] = _mk(bad, bad[0].scenario, radius_attrs=("Filter-Id=teacher",))
        self.assertTrue(any("未下发 VLAN" in e for e in auth.check(bad)))

    def test_wrong_ssid_vlan_detected(self):
        bad = list(self.rules)
        bad[2] = _mk(bad, "无线-教职工", post_vlan="510")
        self.assertTrue(any("ECUST-EDU" in e for e in auth.check(bad)))

    def test_non_isolation_start_detected(self):
        bad = list(self.rules)
        bad[0] = _mk(bad, "有线-教职工", pre_vlan=101)
        self.assertTrue(any("认证前 VLAN" in e for e in auth.check(bad)))

    def test_unknown_post_vlan_detected(self):
        bad = list(self.rules)
        bad[2] = _mk(bad, "无线-教职工", post_vlan="777")
        errors = auth.check(bad)
        self.assertTrue(any("777" in e and "不在地址规划" in e for e in errors), errors)

    def test_non_guest_stuck_in_isolation_detected(self):
        bad = list(self.rules)
        bad[0] = _mk(bad, "有线-教职工", post_vlan="999")
        self.assertTrue(any("不应仍在隔离 VLAN" in e for e in auth.check(bad)))

    def test_radius_overlap_with_planning_detected(self):
        """把隔离网段设成已占用的网段，应报交叠。"""
        old = auth.ISOLATION_SUBNET
        try:
            auth.ISOLATION_SUBNET = "10.10.0.0/24"
            errors = auth.check(self.rules)
            self.assertTrue(any("交叠" in e for e in errors), errors)
        finally:
            auth.ISOLATION_SUBNET = old


class TestOutput(unittest.TestCase):
    def test_markdown_rows(self):
        rules = auth.build_rules()
        md = auth.to_markdown(rules)
        self.assertTrue(md.startswith("| 场景 |"))
        self.assertEqual(md.strip().count("\n") + 1, len(rules) + 2)


if __name__ == "__main__":
    unittest.main()
