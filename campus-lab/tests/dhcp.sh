#!/bin/sh
# DHCP: server / relay / client lease checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin DHCP
cap=dhcp
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin DHCP-01 "$cap" "教学区动态终端取得 VLAN101 地址"
run_cmd pc-dyn1 "cat /tmp/dhcp.env"
assert_contains "ip=10.10.0." "$OUT"
case_end

case_begin DHCP-02 "$cap" "宿舍区动态终端取得 VLAN301 地址"
run_cmd pc-dyn2 "cat /tmp/dhcp.env"
assert_contains "ip=10.32.0." "$OUT"
case_end

case_begin DHCP-03 "$cap" "无线动态终端取得 VLAN500 地址"
run_cmd pc-dyn3 "cat /tmp/dhcp.env"
assert_contains "ip=10.50.0." "$OUT"
case_end

case_begin DHCP-04 "$cap" "教学区动态终端网关正确"
run_cmd pc-dyn1 "cat /tmp/dhcp.env"
assert_contains "router=10.10.0.1" "$OUT"
case_end

case_begin DHCP-05 "$cap" "DHCP 下发 DNS 为数据中心服务器"
run_cmd pc-dyn1 "cat /tmp/dhcp.env"
assert_contains "dns=10.60.0.10" "$OUT"
case_end

case_begin DHCP-06 "$cap" "教学区租约为 4 小时量级"
run_cmd pc-dyn1 "cat /tmp/dhcp.env"
assert_contains "lease=14" "$OUT"
case_end

case_begin DHCP-07 "$cap" "宿舍汇聚 DHCP Relay 进程运行"
run_cmd agg-d1 "pgrep -f dnsmasq >/dev/null && echo relay-running"
assert_contains "relay-running" "$OUT"
case_end

case_begin DHCP-08 "$cap" "服务器租约文件记录客户端 MAC"
run_cmd srv-dc1 "grep -q '02:00:00:00:01:01' /var/log/dhcp.leases && echo lease-found"
assert_contains "lease-found" "$OUT"
case_end

suite_end
exit $?