#!/bin/sh
# Trust / Untrust / DMZ policy checks. Run from campus-lab/.
set -u
P=clab-campus-lab-
FAIL=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }

body=$(docker exec "${P}internet" sh -c 'wget -T3 -qO- http://10.80.0.10/' 2>/dev/null)
[ "$body" = 'DMZ server OK' ] && pass 'Internet -> DMZ TCP/80 allowed' || fail 'Internet -> DMZ TCP/80 rejected'

if docker exec "${P}internet" sh -c 'wget -T2 -qO- http://10.10.0.11/' >/dev/null 2>&1; then
  fail 'Internet -> Trust should be blocked (unexpected success)'
else
  pass 'Internet -> Trust blocked'
fi

if docker exec "${P}internet" ping -c1 -W1 10.32.0.11 >/dev/null 2>&1; then
  fail 'Internet -> dorm VLAN should be blocked (unexpected success)'
else
  pass 'Internet -> dorm VLAN blocked'
fi

if docker exec "${P}srv-dmz" ping -c1 -W1 10.10.0.11 >/dev/null 2>&1; then
  fail 'DMZ -> Trust should be blocked (unexpected success)'
else
  pass 'DMZ -> Trust blocked'
fi

echo
echo '== fw1 policy counters =='
docker exec "${P}fw1" nft list table inet fw 2>/dev/null

echo
[ "$FAIL" -eq 0 ] && { echo 'RESULT: ALL PASS'; exit 0; }
echo "RESULT: $FAIL FAILED"; exit 1
