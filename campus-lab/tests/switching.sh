#!/bin/sh
# SWITCH: VLAN, Trunk, access-port and STP checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin SWITCH
cap=switching
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin SWITCH-01 "$cap" "acc-ta 已启用 STP"
run_cmd acc-ta "cat /sys/class/net/br0/bridge/stp_state"
assert_eq "1" "$OUT"
case_end

case_begin SWITCH-02 "$cap" "acc-ta 上联 Trunk 承载 VLAN101/500"
run_cmd acc-ta "bridge vlan show dev eth1"
assert_contains "101" "$OUT"
assert_contains "500" "$OUT"
case_end

case_begin SWITCH-03 "$cap" "acc-ta eth3 为 VLAN101 Access 端口"
run_cmd acc-ta "bridge vlan show dev eth3 | tr -s '[:space:]' ' '"
assert_contains "101 PVID Egress Untagged" "$OUT"
case_end

case_begin SWITCH-04 "$cap" "acc-ta 双上联在路由接入设计中保持转发"
run_cmd acc-ta "bridge link show dev eth1; bridge link show dev eth2"
count=$(printf '%s\n' "$OUT" | grep -c "state forwarding" || true)
assert_eq "2" "$count"
case_end

case_begin SWITCH-05 "$cap" "宿舍无线 VLAN510 通过 Trunk"
run_cmd acc-d1 "bridge vlan show dev eth1"
assert_contains "510" "$OUT"
case_end

case_begin SWITCH-06 "$cap" "AP 接口接入无线 VLAN510"
run_cmd acc-d1 "bridge vlan show dev eth4 | tr -s '[:space:]' ' '"
assert_contains "510 PVID Egress Untagged" "$OUT"
case_end

case_begin SWITCH-07 "$cap" "图书馆上联 Trunk 承载 VLAN50"
run_cmd acc-lib "bridge vlan show dev eth1"
assert_contains "50" "$OUT"
case_end

case_begin SWITCH-08 "$cap" "图书馆终端接口接入 VLAN50"
run_cmd acc-lib "bridge vlan show dev eth3 | tr -s '[:space:]' ' '"
assert_contains "50 PVID Egress Untagged" "$OUT"
case_end

suite_end
exit $?
