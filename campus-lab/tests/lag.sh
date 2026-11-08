#!/bin/sh
# LAG: core/server link aggregation checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin LAG
cap=lag
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin LAG-01 "$cap" "core1 bond0 使用 802.3ad 模式"
run_cmd core1 "ip -d link show bond0"
assert_contains "802.3ad" "$OUT"
case_end

case_begin LAG-02 "$cap" "core1 bond0 两个成员均在线"
run_cmd core1 "cat /proc/net/bonding/bond0"
assert_contains "Slave Interface: eth11" "$OUT"
assert_contains "Slave Interface: eth14" "$OUT"
case_end

case_begin LAG-03 "$cap" "core1 逻辑地址仅在 bond0 上"
run_cmd core1 "ip -4 addr show bond0 | grep -c 10.0.0.1/30"
assert_eq "1" "$OUT"
case_end

case_begin LAG-04 "$cap" "核心间聚合后只有一条 OSPF 邻居"
run_cmd core1 "vtysh -c 'show ip ospf neighbor' | grep -c Full"
assert_eq "11" "$OUT"
case_end

case_begin LAG-05 "$cap" "core2 bond0 使用 802.3ad 模式"
run_cmd core2 "ip -d link show bond0"
assert_contains "802.3ad" "$OUT"
case_end

case_begin LAG-06 "$cap" "服务器双网卡 active-backup 聚合"
run_cmd srv-dc1 "ip -d link show bond0"
assert_contains "active-backup" "$OUT"
case_end

case_begin LAG-07 "$cap" "核心聚合成员故障时业务不中断"
run_cmd core1 "ip link set eth11 down"
sleep 3
assert_reachable pc-ta1 10.60.0.10
run_cmd core1 "ip link set eth11 up"
case_end

suite_end
exit $?