#!/usr/bin/env python3
"""tools/report_check.py 的单元测试（仅标准库）。

运行：python3 -m unittest discover -s tools/tests -v

这些测试验证"报告与设计一致"的校验确实能检出错误，
避免校验函数形同虚设。
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import report_check as rc  # noqa: E402

REPORT = ROOT / "docs" / "course-report-draft.md"
FACTS = ROOT / "campus-lab" / "configs" / "facts.json"


class TestReportChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = REPORT.read_text(encoding="utf-8")
        cls.facts = json.loads(FACTS.read_text(encoding="utf-8"))

    def test_current_report_is_consistent(self):
        self.assertEqual(rc.check_vlan_table(self.text), [])
        self.assertEqual(rc.check_dhcp_count(self.text, self.facts), [])
        self.assertEqual(rc.check_dhcp_example(self.text, self.facts), [])
        self.assertEqual(rc.check_relay_example(self.text, self.facts), [])
        self.assertEqual(rc.check_pool_table(self.text, self.facts), [])
        self.assertEqual(rc.check_dns_section(self.text), [])
        self.assertEqual(rc.check_auth_section(self.text), [])

    def test_vlan_gateway_mismatch_detected(self):
        bad = self.text.replace(
            "| 101 | 教学楼 A | 10.10.0.0/24 | 10.10.0.1 |",
            "| 101 | 教学楼 A | 10.10.0.0/24 | 10.10.0.99 |")
        self.assertTrue(any("VLAN 101" in e for e in rc.check_vlan_table(bad)))

    def test_vlan_subnet_mismatch_detected(self):
        bad = self.text.replace(
            "| 201 | 实验楼 A | 10.20.0.0/24 |", "| 201 | 实验楼 A | 10.21.0.0/24 |")
        self.assertTrue(any("VLAN 201" in e for e in rc.check_vlan_table(bad)))

    def test_pool_lease_mismatch_detected(self):
        bad = self.text.replace(
            "| v301 | 301 | 10.32.0.100–10.32.0.200 | 43200 |",
            "| v301 | 301 | 10.32.0.100–10.32.0.200 | 14400 |")
        self.assertTrue(any("v301" in e for e in rc.check_pool_table(bad, self.facts)))

    def test_missing_pool_detected(self):
        bad = re.sub(r"^\| v510 .*$\n", "", self.text, flags=re.M)
        self.assertTrue(any("行" in e for e in rc.check_pool_table(bad, self.facts)))

    def test_dns_ip_mismatch_detected(self):
        bad = self.text.replace("| srv-dmz1 | 外部主 | 10.80.0.21 |",
                                "| srv-dmz1 | 外部主 | 10.80.0.29 |")
        self.assertTrue(any("srv-dmz1" in e for e in rc.check_dns_section(bad)))

    def test_missing_auth_scenario_detected(self):
        bad = self.text.replace("| 无线-访客 | ECUST-GUEST |", "| 访客无线 | ECUST-GUEST |")
        self.assertTrue(any("无线-访客" in e for e in rc.check_auth_section(bad)))

    def test_wrong_relay_target_detected(self):
        bad = self.text.replace("dhcp-relay=10.32.0.252,10.60.0.10",
                                "dhcp-relay=10.32.0.252,10.60.0.99")
        self.assertTrue(any("目标" in e for e in rc.check_relay_example(bad, self.facts)))


if __name__ == "__main__":
    unittest.main()
