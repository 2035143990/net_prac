#!/bin/sh
# CONN: end-to-end reachability checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin CONN
cap=base

case_begin CONN-01 "$cap" "VLAN101 同网段互通"
assert_reachable pc-ta1 10.10.0.12
case_end

case_begin CONN-02 "$cap" "VLAN101 -> VLAN102 三层互通"
assert_reachable pc-ta1 10.10.1.11
case_end

case_begin CONN-03 "$cap" "教学区 -> 实验区 VLAN201"
assert_reachable pc-ta1 10.20.0.11
case_end

case_begin CONN-04 "$cap" "教学/实验区 -> 宿舍区 ACL 阻断"
# 设计方案 6.6 访问控制矩阵：教学区、实验区 -> 宿舍区 = ✗
assert_unreachable pc-ta1 10.32.0.11
assert_unreachable pc-la1 10.32.0.11
case_end

case_begin CONN-05 "$cap" "教学区 -> 图书馆 VLAN50"
assert_reachable pc-ta1 10.55.0.11
case_end

case_begin CONN-06 "$cap" "教学区 -> 生活区 VLAN61"
assert_reachable pc-ta1 10.64.0.11
case_end

case_begin CONN-07 "$cap" "教学区 -> 数据中心 VLAN70"
assert_reachable pc-ta1 10.60.0.10
case_end

case_begin CONN-08 "$cap" "有线 -> 无线 VLAN500"
assert_reachable pc-ta1 10.50.0.11
case_end

case_begin CONN-09 "$cap" "内网经 NAT 访问 Internet"
assert_reachable pc-ta1 203.0.113.100
case_end

case_begin CONN-10 "$cap" "内网访问 DMZ 服务器"
assert_reachable pc-ta1 10.80.0.10
case_end

suite_end
exit $?