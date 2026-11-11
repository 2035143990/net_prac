#!/usr/bin/env python3
"""tools/c_address_plan.py 的单元测试（仅标准库）。

运行：python3 -m unittest discover -s tools/tests -v
或：  python3 tools/tests/test_c_address_plan.py
"""
import ipaddress
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import c_address_plan as cap  # noqa: E402


class TestPlanGeneration(unittest.TestCase):
    def setUp(self):
        self.rows = cap.all_rows()

    def test_row_and_subnet_counts(self):
        self.assertEqual(len(self.rows), cap.EXPECTED_ROWS)
        self.assertEqual(cap.subnet_count(self.rows), cap.EXPECTED_SUBNETS)

    def test_default_plan_passes(self):
        self.assertEqual(cap.check(self.rows), [])

    def test_vlan_range_matches_design(self):
        vlans = sorted({r.vlan for r in self.rows})
        self.assertEqual(vlans, sorted(
            list(range(101, 106)) + list(range(201, 209)) + list(range(301, 329))
            + [50, 61, 62, 63, 70, 80, 90, 500, 510]))

    def test_gateway_is_network_dot_one(self):
        for r in self.rows:
            self.assertEqual(r.gateway, str(r.subnet[1]), r.building)

    def test_representative_subnets_match_simulation(self):
        """campus-lab/gen.py 已使用的代表楼栋网段不能被改动。"""
        by_building = {r.building: str(r.subnet) for r in self.rows}
        self.assertEqual(by_building["教学楼A"], "10.10.0.0/24")   # VLAN 101
        # 教学区按“一栋楼一个 /24、第三段顺延”：A=10.10 B=10.11 C=10.12 D=10.13 E=10.14
        self.assertEqual(by_building["教学楼B"], "10.11.0.0/24")   # VLAN 102
        self.assertEqual(by_building["实验楼A"], "10.20.0.0/24")   # VLAN 201
        self.assertEqual(by_building["学生公寓 1 号楼"], "10.32.0.0/24")  # VLAN 301

    def test_no_overlap_with_functional_networks(self):
        functional = {ipaddress.ip_network(n) for _, _, _, n in cap.FUNCTIONAL}
        for r in self.rows:
            if (r.building, r.subnet) in {(name, ipaddress.ip_network(n))
                                          for name, _, _, n in cap.FUNCTIONAL}:
                continue
            for net in functional:
                self.assertFalse(r.subnet.overlaps(net) and r.subnet != net,
                                 f"{r.building} {r.subnet} 与功能区 {net} 交叠")


class TestConflictDetection(unittest.TestCase):
    """故意制造冲突，确认检查函数能报出来（避免检查形同虚设）。"""

    def _base(self):
        return cap.all_rows()

    def test_duplicate_vlan_detected(self):
        rows = self._base()
        bad = list(rows)
        bad[0] = cap.Row(bad[0].building, bad[0].region, bad[1].vlan,
                         bad[0].subnet, bad[0].gateway)
        errors = cap.check(bad)
        self.assertTrue(any("重复" in e for e in errors), errors)

    def test_overlapping_subnet_detected(self):
        rows = self._base()
        bad = list(rows)
        bad[0] = cap.Row(bad[0].building, bad[0].region, bad[0].vlan,
                         bad[1].subnet, str(bad[1].subnet[1]))
        errors = cap.check(bad)
        self.assertTrue(any("交叠" in e for e in errors), errors)

    def test_wrong_gateway_detected(self):
        rows = self._base()
        bad = list(rows)
        bad[0] = cap.Row(bad[0].building, bad[0].region, bad[0].vlan,
                         bad[0].subnet, str(bad[0].subnet[2]))
        errors = cap.check(bad)
        self.assertTrue(any("不是子网 .1" in e for e in errors), errors)

    def test_count_mismatch_detected(self):
        errors = cap.check(self._base()[:-1])
        self.assertTrue(any("期望" in e for e in errors), errors)


class TestOutput(unittest.TestCase):
    def test_markdown_has_header_and_all_rows(self):
        rows = cap.all_rows()
        md = cap.to_markdown(rows)
        self.assertTrue(md.startswith("| 楼栋/功能区 |"))
        self.assertEqual(md.strip().count("\n") + 1, len(rows) + 2)

    def test_csv_roundtrip(self):
        import csv
        import io
        rows = cap.all_rows()
        parsed = list(csv.DictReader(io.StringIO(cap.to_csv(rows))))
        self.assertEqual(len(parsed), len(rows))
        self.assertEqual(set(parsed[0]), set(cap.FIELDS))


if __name__ == "__main__":
    unittest.main()
