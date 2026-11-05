#!/bin/sh
# End-to-end reachability checks. Run from campus-lab/ with the lab deployed.
set -u
P=clab-campus-lab-
FAIL=0

check() {
  src=$1; dst=$2; label=$3
  if docker exec "${P}${src}" ping -c2 -W2 "$dst" >/dev/null 2>&1; then
    printf 'PASS  %-38s %s -> %s\n' "$label" "$src" "$dst"
  else
    printf 'FAIL  %-38s %s -> %s\n' "$label" "$src" "$dst"
    FAIL=$((FAIL + 1))
  fi
}

echo '== Same VLAN / VLAN间 =='
check pc-ta1 10.10.0.12 'VLAN101 same subnet'
check pc-ta1 10.10.1.11 'VLAN101 -> VLAN102'
check pc-ta2 10.10.1.11 'VLAN101 -> VLAN102 (reverse)'

echo '== 跨区域 =='
check pc-ta1 10.20.0.11 '教学区 -> 实验区 VLAN201'
check pc-ta1 10.32.0.11 '教学区 -> 宿舍区 VLAN301'
check pc-ta1 10.55.0.11 '教学区 -> 图书馆 VLAN50'
check pc-ta1 10.64.0.11 '教学区 -> 生活区 VLAN61'
check pc-ta1 10.60.0.10 '教学区 -> 数据中心 VLAN70'
check pc-d1  10.10.0.11 '宿舍区 -> 教学区'
check pc-lib 10.32.0.11 '图书馆 -> 宿舍区'

echo '== 无线业务 VLAN =='
check pc-ta1 10.50.0.11 '有线 -> 无线 VLAN500'
check pc-ta1 10.51.0.11 '有线 -> 无线 VLAN510'

echo '== 内网 -> Internet (NAT) =='
check pc-ta1 203.0.113.100 'NAT 访问 Internet'

echo '== 内网 -> DMZ =='
check pc-ta1 10.80.0.10 '内网访问 DMZ 服务器'

echo
if [ "$FAIL" -eq 0 ]; then
  echo 'RESULT: ALL PASS'
  exit 0
fi
echo "RESULT: $FAIL FAILED"
exit 1
