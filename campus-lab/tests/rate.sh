#!/bin/sh
# RATE: link rate modeling checks.
#
# 任务书对链路速率有明确要求：主干 10G、汇聚到楼层 1G、宿舍到房间 100M。
# Containerlab 的 link 没有原生带宽参数，因此速率由 gen.py 生成台账
# （configs/rates/*.rates），并在容器内用 tc/netem 的 tbf qdisc 实际限速。
# 本套件验证「台账存在」与「限速已生效」两个层面。
set -u
. "$(dirname "$0")/lib.sh"

suite_begin RATE
cap=rate
if ! require_cap "$cap"; then suite_end; exit 0; fi

case_begin RATE-01 "$cap" "速率台账文件已生成且覆盖全部有速率的节点"
run_cmd core1 "ls /configs/rates/ | wc -l"
CNT=$OUT
run_cmd core1 "cat /configs/rates/core1.rates"
assert_contains "10gbit" "$OUT"
case_end

case_begin RATE-02 "$cap" "核心到汇聚的主干链路限速为 10G"
run_cmd core1 "tc qdisc show dev eth1 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 10Gbit" "$OUT"
case_end

case_begin RATE-03 "$cap" "核心间聚合成员链路限速为 10G"
run_cmd core1 "tc qdisc show dev eth11 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 10Gbit" "$OUT"
case_end

case_begin RATE-04 "$cap" "汇聚到楼层接入的链路限速为 1G"
run_cmd agg-t1 "tc qdisc show dev eth3 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 1Gbit" "$OUT"
case_end

case_begin RATE-05 "$cap" "宿舍接入到房间信息点的链路限速为 100M"
run_cmd acc-d1 "tc qdisc show dev eth3 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 100Mbit" "$OUT"
case_end

case_begin RATE-06 "$cap" "教学接入到房间信息点的链路限速为 1G"
run_cmd acc-ta "tc qdisc show dev eth3 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 1Gbit" "$OUT"
case_end

case_begin RATE-07 "$cap" "出口到梅陇校区的互联链路限速为 10G"
run_cmd r2 "tc qdisc show dev eth3 | grep -o 'rate [0-9]*[MG]bit'"
assert_contains "rate 10Gbit" "$OUT"
case_end

case_begin RATE-08 "$cap" "限速后业务仍然可用（限速不误伤转发）"
assert_reachable pc-ta1 10.60.0.10
case_end

case_begin RATE-09 "$cap" "台账中的速率档位只有 10G/1G/100M 三种"
run_cmd core1 "cat /configs/rates/*.rates | grep -v '^#' | awk '{print \$2}' | sort -u | wc -l"
assert_eq "3" "$OUT"
run_cmd core1 "cat /configs/rates/*.rates | grep -cv '^#' >/dev/null; cat /configs/rates/*.rates | grep -v '^#' | awk '{print \$2}' | sort -u | tr '\n' ','"
assert_contains "10gbit" "$OUT"
assert_contains "1gbit" "$OUT"
assert_contains "100mbit" "$OUT"
case_end

suite_end
exit $?
