#!/bin/sh
# SEC: Trust / Untrust / DMZ boundary checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin SEC
cap=base

case_begin SEC-01 "$cap" "Internet -> DMZ 发布地址 TCP/80 放行"
assert_http_contains internet "http://198.51.100.80/" "DMZ server OK"
case_end

case_begin SEC-02 "$cap" "Internet -> Trust 阻断"
assert_unreachable internet 10.10.0.11
case_end

case_begin SEC-03 "$cap" "Internet -> 宿舍区阻断"
assert_unreachable internet 10.32.0.11
case_end

case_begin SEC-04 "$cap" "DMZ -> Trust 阻断"
assert_unreachable srv-dmz 10.10.0.11
case_end

case_begin SEC-05 "$cap" "Internet 直达 DMZ 私网地址阻断"
run_cmd internet "wget -T3 -qO- http://10.80.0.10/ || true"
assert_not_contains "DMZ server OK" "$OUT"
case_end

case_begin SEC-06 "$cap" "防火墙放行计数器有效命中"
assert_counter_positive fw1 "inet fw" "nat.allow"
case_end

suite_end
exit $?