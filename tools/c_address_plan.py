#!/usr/bin/env python3
"""C 组：楼宇 ↔ VLAN ↔ 子网 ↔ 网关明细表生成与冲突检查。

依据《奉贤校区校园网设计方案》5.1（地址空间总规划）与 5.2（VLAN 规划）：

- 一栋楼一个 VLAN、一个 /24 子网，网关为子网 .1；
- VLAN 编号沿用设计方案的编码（101-105 / 201-208 / 301-328 / 50 / 61-63 / 70 / 80 / 90 / 500 / 510）；
- 子网统一使用 10.x.0.0/24，功能区（无线、图书馆、数据中心、DMZ、管理网）优先占位；
- 宿舍区 28 栋楼按序号顺延分配 10.32-10.49（1-18 号楼）与 10.96-10.106（19-28 号楼），
  跳过 10.50/10.51（无线）与 10.55（图书馆）；
- 所有子网、VLAN 之间不得重复或交叠。

本脚本只依赖标准库，便于组内任何人复现：

    python3 tools/c_address_plan.py            # 检查并打印汇总
    python3 tools/c_address_plan.py --md       # 输出 Markdown 明细表
    python3 tools/c_address_plan.py --csv      # 输出 CSV（可用 Excel 打开）

退出码：0 全部检查通过，1 存在冲突。
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import sys
from collections import Counter
from dataclasses import dataclass

# ---------------------------------------------------------------- 功能区（优先占位）
# 这些是 C 组之外已经确定、且被仿真工程（campus-lab/gen.py）引用的网段，不能变动。
FUNCTIONAL = [
    # (名称, 区域, VLAN, 子网)
    ("图书馆", "图书馆", 50, "10.55.0.0/24"),
    ("数据中心服务器", "数据中心", 70, "10.60.0.0/24"),
    ("DMZ", "出口", 80, "10.80.0.0/24"),
    ("网络管理", "网络中心", 90, "10.70.0.0/24"),
    ("无线-教学/图书馆/信息楼", "无线", 500, "10.50.0.0/24"),
    ("无线-宿舍/实验区", "无线", 510, "10.51.0.0/24"),
]

# 生活区：食堂 1、食堂 2、体育馆三栋楼共用 10.64.0.0/24。
# 每栋楼独立 VLAN，同一子网由生活区汇聚的 VLAN 间路由承载。
LIVING_AREA = [
    ("食堂1", 61),
    ("食堂2", 62),
    ("体育馆", 63),
]
LIVING_AREA_BASE = ipaddress.ip_network("10.64.0.0/24")

# 楼栋（严格按设计方案 5.1 的“10.A.B.0/24，B 为楼栋序号”）
# (标签, 区域, VLAN 起点, 子网第三段起点, 楼栋数)
BUILDING_GROUPS = [
    ("教学楼", "教学区", 101, 10, 5),     # 101-105 -> 10.10.0.0/24 ~ 10.14.0.0/24
    ("实验楼", "实验区", 201, 20, 8),     # 201-208 -> 10.20.0.0/24 ~ 10.27.0.0/24
    ("学生公寓", "宿舍区", 301, 32, 28),  # 301-328 -> 10.32.0.0/24 起，跳过无线/图书馆占用的段
]

# 宿舍 19-28 号楼顺延到 10.60~10.69，避开无线 10.50/10.51 与图书馆 10.55。
# 之所以命名为 DORM_TAIL，是为了让冲突检查能逐条报告，而不是静默避让。
DORM_OCTET_OVERRIDES = {19: 96, 20: 97, 21: 98, 22: 99, 23: 101,
                        24: 102, 25: 103, 26: 104, 27: 105, 28: 106}

EXPECTED_ROWS = 5 + 8 + 28 + 3 + 6              # 楼栋 41 + 生活区 3 + 功能区 6 = 50
EXPECTED_SUBNETS = 5 + 8 + 28 + 1 + 1 + 5       # 生活区 3 栋楼共用 1 个子网 = 48


@dataclass(frozen=True)
class Row:
    building: str
    region: str
    vlan: int
    subnet: ipaddress.IPv4Network
    gateway: str

    def as_dict(self) -> dict:
        return {
            "楼栋/功能区": self.building,
            "区域": self.region,
            "VLAN": self.vlan,
            "子网": str(self.subnet),
            "可用主机数": self.subnet.num_addresses - 2,
            "网关": self.gateway,
            "DHCP 动态范围": self.dhcp_range(),
        }

    def dhcp_range(self) -> str:
        """与 campus-lab 的约定一致：.100-.200 为动态池，.1-.11 保留。"""
        if self.subnet.prefixlen != 24:
            return "—"
        return f"{self.subnet[100]} - {self.subnet[200]}"


# ---------------------------------------------------------------- 分配
def building_rows() -> list[Row]:
    rows: list[Row] = []
    for label, region, vlan_base, octet_base, count in BUILDING_GROUPS:
        for i in range(count):
            if label == "学生公寓":
                name = f"{label} {i + 1} 号楼"
                octet = DORM_OCTET_OVERRIDES.get(i + 1, octet_base + i)
            else:
                name = f"{label}{chr(ord('A') + i)}"
                octet = octet_base + i
            subnet = ipaddress.ip_network(f"10.{octet}.0.0/24")
            rows.append(Row(name, region, vlan_base + i, subnet, str(subnet[1])))
    return rows


def living_rows() -> list[Row]:
    return [Row(name, "生活区", vlan, LIVING_AREA_BASE, str(LIVING_AREA_BASE[1]))
            for name, vlan in LIVING_AREA]


def functional_rows() -> list[Row]:
    return [Row(name, region, vlan, ipaddress.ip_network(subnet),
                str(ipaddress.ip_network(subnet)[1]))
            for name, region, vlan, subnet in FUNCTIONAL]


def all_rows() -> list[Row]:
    return building_rows() + living_rows() + functional_rows()


def subnet_count(rows: list[Row]) -> int:
    return len({r.subnet for r in rows})


# ---------------------------------------------------------------- 冲突检查
def check(rows: list[Row]) -> list[str]:
    errors: list[str] = []

    if len(rows) != EXPECTED_ROWS:
        errors.append(f"明细 {len(rows)} 行，期望 {EXPECTED_ROWS}")
    if subnet_count(rows) != EXPECTED_SUBNETS:
        errors.append(f"子网 {subnet_count(rows)} 个，期望 {EXPECTED_SUBNETS}")

    # 1. VLAN 编号唯一
    for vlan, n in sorted(Counter(r.vlan for r in rows).items()):
        if n > 1:
            names = [r.building for r in rows if r.vlan == vlan]
            errors.append(f"VLAN {vlan} 重复：{', '.join(names)}")

    # 2. 子网互不交叠；生活区同组共用子网属有意设计，放行
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if not a.subnet.overlaps(b.subnet):
                continue
            same_living = (a.region == b.region == "生活区"
                           and a.subnet == b.subnet == LIVING_AREA_BASE)
            if not same_living:
                errors.append(f"子网交叠：{a.building} {a.subnet} 与 {b.building} {b.subnet}")

    # 3. 网关在子网内，且为 .1
    for r in rows:
        gw = ipaddress.ip_address(r.gateway)
        if gw not in r.subnet:
            errors.append(f"{r.building} 网关 {r.gateway} 不在 {r.subnet}")
        elif gw != r.subnet[1]:
            errors.append(f"{r.building} 网关 {r.gateway} 不是子网 .1（{r.subnet[1]}）")

    # 4. 楼栋与 VLAN 绑定关系符合设计方案 5.2
    expected = {
        **{f"教学楼{chr(65 + i)}": 101 + i for i in range(5)},
        **{f"实验楼{chr(65 + i)}": 201 + i for i in range(8)},
        **{f"学生公寓 {i + 1} 号楼": 301 + i for i in range(28)},
        **{name: vlan for name, vlan in LIVING_AREA},
    }
    actual = {r.building: r.vlan for r in rows}
    for name, vlan in expected.items():
        if actual.get(name) != vlan:
            errors.append(f"{name} 应为 VLAN {vlan}，实际 {actual.get(name)}")

    # 5. 区域汇总路由互不交叠（教学区 / 实验区 / 宿舍区各自的 /24 聚合后不得重叠）
    regions = {"教学区": [], "实验区": [], "宿舍区": []}
    for r in rows:
        if r.region in regions:
            regions[r.region].append(r.subnet)
    collapsed: list[tuple[str, ipaddress.IPv4Network]] = []
    for name, nets in regions.items():
        for net in ipaddress.collapse_addresses(nets):
            collapsed.append((name, net))
    for i, (na, ba) in enumerate(collapsed):
        for nb, bb in collapsed[i + 1:]:
            if na != nb and ba.overlaps(bb):
                errors.append(f"区域汇总交叠：{na} {ba} 与 {nb} {bb}")

    return errors


def summarise(rows: list[Row]) -> str:
    by_region = Counter(r.region for r in rows)
    regions: dict[str, list[ipaddress.IPv4Network]] = {}
    for r in rows:
        regions.setdefault(r.region, []).append(r.subnet)
    lines = [f"明细 {len(rows)} 行（期望 {EXPECTED_ROWS}），子网 {subnet_count(rows)} 个（期望 {EXPECTED_SUBNETS}）"]
    for region, n in by_region.most_common():
        agg = ", ".join(str(net) for net in ipaddress.collapse_addresses(regions[region]))
        lines.append(f"  {region}: {n} 行，汇总 {agg}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 输出
FIELDS = ["楼栋/功能区", "区域", "VLAN", "子网", "可用主机数", "网关", "DHCP 动态范围"]


def to_markdown(rows: list[Row]) -> str:
    out = ["| " + " | ".join(FIELDS) + " |",
           "| " + " | ".join(["---"] * len(FIELDS)) + " |"]
    for r in rows:
        d = r.as_dict()
        out.append("| " + " | ".join(str(d[f]) for f in FIELDS) + " |")
    return "\n".join(out) + "\n"


def to_csv(rows: list[Row]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(r.as_dict() for r in rows)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成楼宇/VLAN/子网明细并检查冲突")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--md", action="store_true", help="输出 Markdown 明细表")
    group.add_argument("--csv", action="store_true", help="输出 CSV 明细表")
    args = parser.parse_args(argv)

    rows = all_rows()
    errors = check(rows)

    if args.md:
        sys.stdout.write(to_markdown(rows))
    elif args.csv:
        sys.stdout.write(to_csv(rows))
    else:
        print(summarise(rows))

    if errors:
        print("\n检查失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if not (args.md or args.csv):
        print("检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
