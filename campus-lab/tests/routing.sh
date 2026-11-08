#!/bin/sh
# ROUTE: OSPF / VRRP / default route checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin ROUTE
cap=base

case_begin ROUTE-01 "$cap" "core1 OSPF 邻居数 >= 11"
run_cmd core1 "vtysh -c 'show ip ospf neighbor' | grep -c Full"
assert_eq "11" "$OUT"
case_end

case_begin ROUTE-02 "$cap" "core2 OSPF 邻居数 >= 11"
run_cmd core2 "vtysh -c 'show ip ospf neighbor' | grep -c Full"
assert_eq "11" "$OUT"
case_end

case_begin ROUTE-03 "$cap" "core1 存在教学网段 OSPF 路由"
run_cmd core1 "vtysh -c 'show ip route 10.10.0.0/24' | grep 'Known via \"ospf\"'"
assert_contains 'Known via "ospf"' "$OUT"
case_end

case_begin ROUTE-04 "$cap" "core1 存在宿舍网段 OSPF 路由"
run_cmd core1 "vtysh -c 'show ip route 10.32.0.0/24' | grep 'Known via \"ospf\"'"
assert_contains 'Known via "ospf"' "$OUT"
case_end

case_begin ROUTE-05 "$cap" "core1 默认路由指向防火墙 VIP"
run_cmd core1 "ip route | grep '^default .*via 10.0.100.254'"
assert_contains '10.0.100.254' "$OUT"
case_end

case_begin ROUTE-06 "$cap" "fw1 内网路由指向核心 VIP"
run_cmd fw1 "ip route | grep '^10.0.0.0/8 via 10.0.100.253'"
assert_contains '10.0.100.253' "$OUT"
case_end

case_begin ROUTE-07 "$cap" "核心 VRRP VIP 由 core1/core2 之一持有"
run_cmd core1 "ip -4 addr show eth12 | grep -c 10.0.100.253"
c1=$OUT
run_cmd core2 "ip -4 addr show eth12 | grep -c 10.0.100.253"
assert_eq "1" "$((c1 + OUT))"
case_end

case_begin ROUTE-08 "$cap" "宿舍汇聚 VRRP VIP 由 agg-d1/agg-d2 之一持有"
run_cmd agg-d1 "ip -4 addr show eth3.301 | grep -c 10.32.0.1"
d1=$OUT
run_cmd agg-d2 "ip -4 addr show eth3.301 | grep -c 10.32.0.1"
assert_eq "1" "$((d1 + OUT))"
case_end

suite_end
exit $?