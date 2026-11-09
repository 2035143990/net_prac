#!/usr/bin/env python3
"""tools/c_dhcp_plan.py 的单元测试（仅标准库）。

运行：python3 -m unittest discover -s tools/tests -v
"""
import ipaddress
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import c_address_plan as cap      # noqa: E402
import c_dhcp_plan as dhcp        # noqa: E402


class TestPools(unittest.TestCase):
    def setUp(self):
        self.pools = dhcp.build_pools()
        self.rows = cap.all_rows()

    def test_pool_count(self):
        self.assertEqual(len(self.pools), dhcp.EXPECTED_POOLS)

    def test_ranges_inside_subnet_and_avoid_reserved(self):
        for p in self.pools:
            self.assertIn(p.start, p.subnet, p.name)
            self.assertIn(p.end, p.subnet, p.name)
            self.assertGreater(int(p.start), int(p.subnet[dhcp.RESERVED_TOP]), p.name)
            self.assertLess(int(p.end), int(p.subnet.broadcast_address), p.name)

    def test_gateway_matches_planning(self):
        plan = {r.vlan: r.gateway for r in self.rows}
        for p in self.pools:
            self.assertEqual(p.gateway, plan[p.vlan], p.name)

    def test_lease_by_region(self):
        expected = {"教学区": 14400, "实验区": 28800,
                    "宿舍区": 43200, "图书馆": 28800, "生活区": 28800}
        for p in self.pools:
            if p.region == "无线":
                self.assertEqual(p.lease, dhcp.LEASE_BY_REGION[
                    dhcp.WIRELESS_LEASE_REGION[p.vlan]], p.name)
            else:
                self.assertEqual(p.lease, expected[p.region], p.name)

    def test_living_area_has_single_pool(self):
        living = [p for p in self.pools if p.region == "生活区"]
        self.assertEqual(len(living), 1)
        self.assertEqual(living[0].vlan, 61)
        self.assertEqual(living[0].subnet, cap.LIVING_AREA_BASE)

    def test_static_networks_excluded(self):
        vlans = {p.vlan for p in self.pools}
        for v in (70, 80, 90):          # 数据中心 / DMZ / 管理网
            self.assertNotIn(v, vlans)

    def test_no_overlapping_pools(self):
        for i, a in enumerate(self.pools):
            for b in self.pools[i + 1:]:
                self.assertFalse(a.subnet.overlaps(b.subnet),
                                 f"{a.name} 与 {b.name} 重叠")

    def test_representative_pools_match_simulation(self):
        """campus-lab/gen.py 已生成的配置，除 v102 外必须完全一致。"""
        sim = {
            "v50": ("10.55.0.100", "10.55.0.200", 28800),
            "v61": ("10.64.0.100", "10.64.0.200", 28800),
            "v101": ("10.10.0.100", "10.10.0.200", 14400),
            "v201": ("10.20.0.100", "10.20.0.200", 28800),
            "v301": ("10.32.0.100", "10.32.0.200", 43200),
            "v500": ("10.50.0.100", "10.50.0.200", 14400),
            "v510": ("10.51.0.100", "10.51.0.200", 43200),
        }
        by_name = {p.name: p for p in self.pools}
        for name, (start, end, lease) in sim.items():
            p = by_name[name]
            self.assertEqual((str(p.start), str(p.end), p.lease),
                             (start, end, lease), name)


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.pools = dhcp.build_pools()
        self.rows = cap.all_rows()

    def test_reserved_overlap_detected(self):
        bad = list(self.pools)
        p = bad[0]
        bad[0] = dhcp.Pool(p.name, p.vlan, p.region, p.subnet, p.gateway,
                           p.subnet[1], p.end, p.lease, p.scope)
        errors = dhcp.check(bad, self.rows)
        self.assertTrue(any("保留段" in e for e in errors), errors)

    def test_gateway_mismatch_detected(self):
        bad = list(self.pools)
        p = bad[0]
        bad[0] = dhcp.Pool(p.name, p.vlan, p.region, p.subnet,
                           str(p.subnet[2]), p.start, p.end, p.lease, p.scope)
        errors = dhcp.check(bad, self.rows)
        self.assertTrue(any("网关" in e for e in errors), errors)

    def test_duplicate_pool_detected(self):
        bad = self.pools + [self.pools[0]]
        errors = dhcp.check(bad, self.rows)
        self.assertTrue(any("池名重复" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
