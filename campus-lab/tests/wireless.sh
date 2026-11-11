#!/bin/sh
# WIRELESS: 无线子网划分与校区互联检查。
#
# 任务书要求：
#   - 宿舍区、实验区是一个单独的无线子网；
#   - 其他大楼是另一个无线子网；
#   - 网络中心经核心交换连接梅陇校区和 Internet。
#
# 仿真口径：VLAN 510（10.51.0.0/24）服务宿舍区与实验区，
# VLAN 500（10.50.0.0/24）服务教学区等其他大楼。
#
# 用例编号沿用「套件名-序号」约定，与 CONN/ROUTE/DHCP/ISO/NAT/LAG/FAIL
# 保持一致：WIRELESS-01～07 校验无线子网，WIRELESS-08～11 校验校区互联。
set -u
. "$(dirname "$0")/lib.sh"

suite_begin WIRELESS
cap=base

case_begin WIRELESS-01 "$cap" "宿舍区 AP 归属 VLAN 510 无线子网"
assert_reachable ap-d1 10.51.0.1
case_end

case_begin WIRELESS-02 "$cap" "实验区 AP 归属同一个 VLAN 510 无线子网"
assert_reachable ap-la 10.51.0.1
case_end

case_begin WIRELESS-03 "$cap" "宿舍区 AP 与实验区 AP 同网段互通"
assert_reachable ap-d1 10.51.0.21
case_end

case_begin WIRELESS-04 "$cap" "实验区 AP 可访问数据中心 DNS"
# 用真实 DNS 查询而不是 ping：设计方案 6.6 把宿舍/实验无线子网所在区域
# 列为隔离区域，只放行 DNS(53)，ping 数据中心会被 iso.dorm2dc 丢弃。
assert_dns_resolves ap-la www.campus.local 10.60.0.10 10.80.0.10
case_end

case_begin WIRELESS-05 "$cap" "实验区无线可经 NAT 访问 Internet"
assert_reachable ap-la 203.0.113.100
case_end

case_begin WIRELESS-06 "$cap" "教学区等大楼使用另一个无线子网 VLAN 500"
assert_reachable ap-ta 10.50.0.1
case_end

case_begin WIRELESS-07 "$cap" "两个无线子网之间三层可达（同一 SSID 漫游）"
assert_reachable ap-ta 10.50.0.11
assert_reachable ap-d1 10.51.0.11
case_end

case_begin WIRELESS-08 "$cap" "内网经出口可访问梅陇校区业务网段"
assert_reachable pc-ta1 10.91.0.11
case_end

case_begin WIRELESS-09 "$cap" "梅陇校区对端可反向访问校园网内网地址"
assert_reachable pc-ml1 10.60.0.10
case_end

case_begin WIRELESS-10 "$cap" "梅陇校区经 r2 静态路由回程到园区内网"
# 校验的是「r2 去梅陇校区网段走 10.91.1.0/30 互联链路」。
# 注意目的地必须取梅陇侧地址（10.91.0.0/16）；若取园区内网地址，
# 命中的是 r2 的 10.0.0.0/8 回指路由，与梅陇互联无关。
run_cmd r2 "ip route get 10.91.0.11 | head -n1"
assert_contains "10.91.1.2" "$OUT"
case_end

case_begin WIRELESS-11 "$cap" "梅陇校区业务主机可经 r2 访问 Internet"
assert_reachable pc-ml1 203.0.113.100
case_end

suite_end
exit $?
