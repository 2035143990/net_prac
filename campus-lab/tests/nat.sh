#!/bin/sh
# NAT: DMZ destination NAT and source NAT isolation. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin NAT
cap=dnat
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin NAT-01 "$cap" "Internet 访问公网地址 TCP/80"
assert_http_contains internet "http://198.51.100.80/" "DMZ server OK"
case_end

case_begin NAT-02 "$cap" "Internet 访问公网地址 TCP/443"
assert_http_contains internet "http://198.51.100.80:443/" "DMZ server OK"
case_end

case_begin NAT-03 "$cap" "未发布端口 TCP/22 不返回 DMZ 服务"
run_cmd internet "wget -T2 -qO- http://198.51.100.80:22/ || true"
assert_not_contains "DMZ server OK" "$OUT"
case_end

case_begin NAT-04 "$cap" "Internet 直达 DMZ 私网地址失败"
run_cmd internet "wget -T3 -qO- http://10.80.0.10/ || true"
assert_not_contains "DMZ server OK" "$OUT"
case_end

case_begin NAT-05 "$cap" "DNAT 计数器命中 TCP/80"
assert_counter_positive fw1 "inet fw" "nat.dnat80"
case_end

case_begin NAT-06 "$cap" "私网直达丢包计数器命中"
assert_counter_positive fw1 "inet fw" "nat.private_direct_drop"
case_end

case_begin NAT-07 "$cap" "Trust -> Internet 源 NAT 计数器命中"
assert_counter_positive fw1 "inet fw" "nat.snat"
case_end

suite_end
exit $?