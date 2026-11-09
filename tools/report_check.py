#!/usr/bin/env python3
"""Check course report facts block and section coverage against facts.json."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "campus-lab" / "configs" / "facts.json"
REPORT_PATH = ROOT / "docs" / "course-report-draft.md"
REQUIRED_SECTIONS = [str(i) for i in range(1, 9)]
REQUIRED_CASES = ["DHCP", "ISO", "NAT", "LAG", "FAIL"]
REQUIRED_LABELS = ["摘要", "关键词", "参考文献"]


def expected_block(facts: dict) -> dict[str, str]:
    return {
        "nodes": str(facts["nodes"]["total"]),
        "links": str(facts["links"]),
        "vlans": ",".join(str(v) for v in sorted(facts["vlans"])),
        "mgmt_vlan": str(facts["mgmt_vlan"]),
        "dhcp_pools": str(len(facts["dhcp"]["pools"])),
        "nat_publish": ",".join(item["public"] for item in facts["nat"]["publish"]),
        "lags": ",".join(item["name"] for item in facts["lags"]),
    }


def main() -> int:
    if not FACTS_PATH.exists():
        print(f"missing facts: {FACTS_PATH}")
        return 2
    if not REPORT_PATH.exists():
        print(f"missing report: {REPORT_PATH}")
        return 2
    facts = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    text = REPORT_PATH.read_text(encoding="utf-8")

    block = re.search(r"<!-- facts:begin -->(.*?)<!-- facts:end -->", text, re.DOTALL)
    if not block:
        print("missing facts block")
        return 1
    actual: dict[str, str] = {}
    for line in block.group(1).strip().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            actual[key.strip()] = value.strip()
    expected = expected_block(facts)

    errors = []
    for key, value in expected.items():
        if key not in actual:
            errors.append(f"facts missing key: {key}")
        elif actual[key] != value:
            errors.append(f"facts mismatch {key}: report={actual[key]} facts={value}")
    for key in actual:
        if key not in expected:
            errors.append(f"facts unknown key: {key}")

    headings = set(re.findall(r"^## (\d+) ", text, re.MULTILINE))
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"missing section: {section}")

    for label in REQUIRED_LABELS:
        if label not in text:
            errors.append(f"missing required label: {label}")

    for prefix in REQUIRED_CASES:
        if not re.search(rf"\b{prefix}-\d{{2}}\b", text):
            errors.append(f"missing test case reference: {prefix}-xx")

    for ref in re.findall(r"!\[[^\]]*\]\((figures/[^)]+)\)", text):
        if not (REPORT_PATH.parent / ref).exists():
            errors.append(f"missing figure: {ref}")

    if errors:
        for error in errors:
            print("FAIL", error)
        return 1
    print("report check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())