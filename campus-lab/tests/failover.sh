#!/bin/sh
# FAIL: VRRP / OSPF / firewall failover checks. Run from campus-lab/.
set -u
. "$(dirname "$0")/lib.sh"

suite_begin FAIL
cap=base

case_begin FAIL-01 "$cap" "core1 keepalived 故障后 core2 接管 VIP"
docker exec -d "${P}core1" pkill keepalived 2>/dev/null || true
wait_for core2 20 "ip -4 addr show eth12 | grep -q 10.0.100.253"
assert_eq "0" "$?"
case_end

case_begin FAIL-02 "$cap" "核心 VRRP 切换期间业务不中断"
assert_reachable pc-ta1 10.55.0.11
case_end

case_begin FAIL-03 "$cap" "core1 恢复后重新抢占 VIP"
docker cp configs/frr/core1/keepalived.conf "${P}core1":/tmp/keepalived.conf 2>/dev/null || true
docker exec -d "${P}core1" sh -c 'keepalived -D -f /tmp/keepalived.conf >>/var/log/keepalived.log 2>&1' 2>/dev/null || true
wait_for core1 20 "ip -4 addr show eth12 | grep -q 10.0.100.253"
assert_eq "0" "$?"
case_end

case_begin FAIL-04 "$cap" "汇聚上联故障后可恢复 OSPF 邻居"
docker exec "${P}agg-t1" ip link set eth1 down 2>/dev/null || true
sleep 3
docker exec "${P}agg-t1" ip link set eth1 up 2>/dev/null || true
wait_for agg-t1 90 "vtysh -c 'show ip ospf neighbor' | grep '10.0.10.1 ' | grep -q Full"
assert_eq "0" "$?"
case_end

case_begin FAIL-05 "$cap" "fw1 keepalived 故障后 fw2 接管 Trust VIP"
docker exec -d "${P}fw1" pkill keepalived 2>/dev/null || true
wait_for fw2 20 "ip -4 addr show eth1 | grep -q 10.0.100.254"
assert_eq "0" "$?"
docker cp configs/fw/fw1/keepalived.conf "${P}fw1":/tmp/keepalived.conf 2>/dev/null || true
docker exec -d "${P}fw1" sh -c 'keepalived -D -f /tmp/keepalived.conf >>/var/log/keepalived.log 2>&1' 2>/dev/null || true
case_end

case_begin FAIL-06 "$cap" "故障实验后核心 OSPF 邻居恢复为 11"
run_cmd core1 "vtysh -c 'show ip ospf neighbor' | grep -c Full"
assert_eq "11" "$OUT"
case_end

suite_end
exit $?