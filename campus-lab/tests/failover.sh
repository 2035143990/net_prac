#!/bin/sh
# VRRP and OSPF failover checks. Run from campus-lab/.
set -u
P=clab-campus-lab-
FAIL=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }
ping_lib() { docker exec "${P}pc-ta1" ping -c3 -W2 10.55.0.11 >/dev/null 2>&1; }

echo '== VRRP: core1 master -> core2 backup =='
docker exec -d "${P}core1" pkill keepalived
i=0; ok=0
while [ "$i" -lt 20 ]; do
  if docker exec "${P}core2" ip -4 addr show eth12 2>/dev/null | grep -q '10.0.100.253'; then ok=1; break; fi
  i=$((i + 1)); sleep 1
done
[ "$ok" -eq 1 ] && pass 'core2 took over VIP 10.0.100.253' || fail 'core2 did not take over VIP (timeout)'
ping_lib && pass 'traffic survives core1 keepalived failure' || fail 'traffic lost during VRRP failover'

docker cp configs/frr/core1/keepalived.conf "${P}core1":/tmp/keepalived.conf
docker exec -d "${P}core1" sh -c 'keepalived -D -f /tmp/keepalived.conf >>/var/log/keepalived.log 2>&1'
i=0; ok=0
while [ "$i" -lt 20 ]; do
  if docker exec "${P}core1" ip -4 addr show eth12 2>/dev/null | grep -q '10.0.100.253'; then ok=1; break; fi
  i=$((i + 1)); sleep 1
done
[ "$ok" -eq 1 ] && pass 'core1 preempted and reclaimed VIP' || fail 'core1 did not reclaim VIP (timeout)'
ping_lib && pass 'traffic OK after failback' || fail 'traffic lost after failback'

echo
echo '== OSPF: agg-t1 uplink eth1 down =='
docker exec "${P}pc-ta1" pkill ping 2>/dev/null || true
docker exec "${P}pc-ta1" ping -c 40 -i 0.2 10.55.0.11 >/tmp/failover-ping.log 2>&1 &
PINGPID=$!
sleep 1
docker exec "${P}agg-t1" ip link set eth1 down
sleep 4
docker exec "${P}agg-t1" ip link set eth1 up
wait "$PINGPID" 2>/dev/null || true
i=0; ok=0
while [ "$i" -lt 30 ]; do
  if docker exec "${P}agg-t1" vtysh -c 'show ip ospf neighbor' 2>/dev/null | grep '10.0.10.1 ' | grep -q Full; then ok=1; break; fi
  i=$((i + 1)); sleep 2
done
[ "$ok" -eq 1 ] || fail 'OSPF neighbor did not recover (timeout)'
lost=$(tail -2 /tmp/failover-ping.log | grep -o '[0-9]*% packet loss' | head -1)
[ -n "$lost" ] || lost=unknown
pass "agg-t1 uplink recovered; ping loss during failure: $lost"
ping_lib && pass 'traffic OK after OSPF reconvergence' || fail 'traffic lost after OSPF reconvergence'

echo
[ "$FAIL" -eq 0 ] && { echo 'RESULT: ALL PASS'; exit 0; }
echo "RESULT: $FAIL FAILED"; exit 1
