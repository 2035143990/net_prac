#!/bin/sh
# OSPF / VRRP / route sanity checks. Run from campus-lab/.
set -u
P=clab-campus-lab-
FAIL=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }

for r in core1 core2; do
  n=$(docker exec "${P}${r}" vtysh -c 'show ip ospf neighbor' 2>/dev/null | grep -c Full)
  [ "${n:-0}" -ge 12 ] && pass "$r OSPF Full neighbors: $n" || fail "$r OSPF Full neighbors: ${n:-0} (<12)"
done

for net in 10.10.0.0/24 10.20.0.0/24 10.32.0.0/24 10.50.0.0/24 10.55.0.0/24 10.60.0.0/24 10.64.0.0/24; do
  if docker exec "${P}core1" vtysh -c "show ip route $net" 2>/dev/null | grep -q 'Known via "ospf"'; then
    pass "core1 has OSPF route $net"
  else
    fail "core1 missing OSPF route $net"
  fi
done

pair_vip() {
  a=$1; b=$2; iface=$3; vip=$4
  if docker exec "${P}${a}" ip -4 addr show "$iface" 2>/dev/null | grep -q "$vip" ||
     docker exec "${P}${b}" ip -4 addr show "$iface" 2>/dev/null | grep -q "$vip"; then
    pass "VRRP pair $a/$b owns VIP $vip"
  else
    fail "VRRP pair $a/$b has no VIP $vip"
  fi
}
pair_vip core1 core2 eth12 10.0.100.253
pair_vip agg-t1 agg-t2 eth3.101 10.10.0.1
pair_vip agg-d1 agg-d2 eth3.301 10.32.0.1
pair_vip fw1 fw2 eth1 10.0.100.254
pair_vip r1 r2 eth1 10.90.1.254

if docker exec "${P}core1" ip route 2>/dev/null | grep -q '^default .*via 10.0.100.254'; then
  pass 'core1 default route via firewall VIP'
else
  fail 'core1 default route via firewall VIP'
fi
if docker exec "${P}fw1" ip route 2>/dev/null | grep -q '^10.0.0.0/8 via 10.0.100.253'; then
  pass 'fw1 internal route via core VIP'
else
  fail 'fw1 internal route via core VIP'
fi

echo
[ "$FAIL" -eq 0 ] && { echo 'RESULT: ALL PASS'; exit 0; }
echo "RESULT: $FAIL FAILED"; exit 1
