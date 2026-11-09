#!/usr/bin/env python3
"""tools/c_dns_plan.py 的单元测试（仅标准库）。

运行：python3 -m unittest discover -s tools/tests -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import c_dns_plan as dns  # noqa: E402


def _mk(servers, name, **kw):
    """按名字复制一台服务器并覆盖字段，便于构造异常场景。"""
    base = next(s for s in servers if s.name == name)
    data = dict(
        name=base.name, role=base.role, zone=base.zone, ip=base.ip,
        subnet=base.subnet, forwards_to=base.forwards_to,
        authoritative_for=base.authoritative_for,
    )
    data.update(kw)
    return dns.DnsServer(**data)


class TestDesign(unittest.TestCase):
    def setUp(self):
        self.servers = dns.build_servers()

    def test_four_servers(self):
        self.assertEqual(len(self.servers), 4)

    def test_default_design_passes(self):
        self.assertEqual(dns.check(self.servers), [])

    def test_internal_primary_matches_dhcp_dns(self):
        primary = [s for s in self.servers if s.role == "内部主"][0]
        self.assertEqual(primary.ip, dns.DHCP_DNS)

    def test_placement(self):
        for s in self.servers:
            if s.zone == "内部":
                self.assertEqual(s.subnet, dns.DC_SUBNET, s.name)
            else:
                self.assertEqual(s.subnet, dns.DMZ_SUBNET, s.name)

    def test_no_address_collision_with_existing_devices(self):
        ips = {s.ip for s in self.servers}
        self.assertFalse(ips & dns.RESERVED_IN_DMZ, ips & dns.RESERVED_IN_DMZ)
        self.assertFalse(ips & dns.RESERVED_IN_DC, ips & dns.RESERVED_IN_DC)

    def test_no_address_in_dhcp_range(self):
        for s in self.servers:
            self.assertFalse(100 <= int(s.ip.split(".")[-1]) <= 200, s.name)

    def test_simulation_gap_reported(self):
        gaps = dns.simulation_gaps(self.servers)
        self.assertTrue(any("3 台" in g for g in gaps), gaps)


class TestChecks(unittest.TestCase):
    """构造异常配置，确认每条检查都能报错。"""

    def setUp(self):
        self.servers = dns.build_servers()

    def test_duplicate_ip(self):
        bad = list(self.servers)
        bad[1] = _mk(bad, "srv-dc2", ip=bad[0].ip)
        self.assertTrue(any("重复" in e for e in dns.check(bad)))

    def test_occupied_ip(self):
        bad = list(self.servers)
        bad[2] = _mk(bad, "srv-dmz1", ip="10.80.0.10")
        errors = dns.check(bad)
        self.assertTrue(any("已被现有设备占用" in e for e in errors), errors)

    def test_dhcp_range_ip(self):
        bad = list(self.servers)
        bad[2] = _mk(bad, "srv-dmz1", ip="10.80.0.150")
        errors = dns.check(bad)
        self.assertTrue(any("DHCP 动态范围" in e for e in errors), errors)

    def test_wrong_placement(self):
        bad = list(self.servers)
        bad[0] = _mk(bad, "srv-dc1", subnet=dns.DMZ_SUBNET)
        errors = dns.check(bad)
        self.assertTrue(any("应部署在数据中心" in e for e in errors), errors)

    def test_missing_backup(self):
        bad = self.servers[:1] + self.servers[2:]
        errors = dns.check(bad)
        self.assertTrue(any("4 台" in e for e in errors), errors)

    def test_primary_mismatch_with_dhcp(self):
        bad = list(self.servers)
        bad[0] = _mk(bad, "srv-dc1", ip="10.60.0.30")
        errors = dns.check(bad)
        self.assertTrue(any("不一致" in e for e in errors), errors)

    def test_external_dns_uses_public_recursive(self):
        bad = list(self.servers)
        bad[2] = _mk(bad, "srv-dmz1", forwards_to=("8.8.8.8",))
        errors = dns.check(bad)
        self.assertTrue(any("不应直接使用公网上游" in e for e in errors), errors)


class TestOutput(unittest.TestCase):
    def test_markdown_rows(self):
        servers = dns.build_servers()
        md = dns.to_markdown(servers)
        self.assertTrue(md.startswith("| 服务器 |"))
        self.assertEqual(md.strip().count("\n") + 1, len(servers) + 2)

    def test_csv_fields(self):
        import csv
        import io
        rows = list(csv.DictReader(io.StringIO(dns.to_csv(dns.build_servers()))))
        self.assertEqual(len(rows), 4)
        self.assertEqual(set(rows[0]), set(dns.FIELDS))


if __name__ == "__main__":
    unittest.main()
