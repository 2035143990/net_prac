#!/bin/sh
# ISO: dorm isolation and management network protection. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin ISO
cap=acl
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin ISO-01 "$cap" "宿舍 -> 管理网阻断"
assert_unreachable pc-d1 10.70.0.10
case_end

case_begin ISO-02 "$cap" "宿舍 -> 教学区阻断"
assert_unreachable pc-d1 10.10.0.11
case_end

case_begin ISO-03 "$cap" "宿舍 -> 实验区阻断"
assert_unreachable pc-d1 10.20.0.11
case_end

case_begin ISO-04 "$cap" "宿舍 -> 数据中心阻断"
assert_unreachable pc-d1 10.60.0.10
case_end

case_begin ISO-05 "$cap" "宿舍有线/无线之间互通"
assert_reachable pc-d1 10.51.0.11
case_end

case_begin ISO-06 "$cap" "宿舍 -> Internet 放行"
assert_reachable pc-d1 203.0.113.100
case_end

case_begin ISO-07 "$cap" "宿舍 -> DMZ 服务放行"
assert_http_contains pc-d1 "http://10.80.0.10/" "DMZ server OK"
case_end

case_begin ISO-08 "$cap" "教学区 -> 管理网阻断"
assert_unreachable pc-ta1 10.70.0.10
case_end

case_begin ISO-09 "$cap" "管理终端 -> 教学区放行"
assert_reachable mgmt-pc 10.10.0.11
case_end

case_begin ISO-10 "$cap" "宿舍到教学区拦截计数器命中"
assert_counter_positive agg-d1 "inet zone" "iso.dorm2teaching"
case_end

case_begin ISO-11 "$cap" "宿舍源地址校验规则已加载"
run_cmd agg-d1 "nft list table inet zone | grep 'iso.src_guard'"
assert_contains "iso.src_guard" "$OUT"
case_end

case_begin ISO-12 "$cap" "宿舍 -> 图书馆按默认拒绝"
assert_unreachable pc-d1 10.55.0.11
case_end

suite_end
exit $?