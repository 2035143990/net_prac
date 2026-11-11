#!/bin/sh
# 拓扑健康预检：在跑用例前确认实验环境处于"已就绪"状态。
#
# 背景：Containerlab 的 exec 只在 deploy 时执行一次，容器一旦被 restart
# （宿主机重启 / dockerd 重启 / 手工 restart），setup.sh 不会重跑；
# 而容器 netns 重建后，Containerlab 注入的 veth 也不会自动回来。
# 此时容器数量依然齐全，但二层广播域、VRRP、OSPF 全部失效，
# 表现为大批用例无意义地失败（曾经出现过 37/65 的情形）。
# 因此这里做前置检查，把问题拦在测试之前。
#
# 特别地：WSL2 发行版在没有活跃前台进程时会被 Windows 回收，systemd 随之
# 执行完整关机序列，dockerd 被重启。这同样会导致 veth 丢失。部署时会把
# dockerd 的 MainPID 记录到 .deploy-dockerd-pid，本脚本据此判断环境是否
# 在部署之后被重启过，从而给出准确的修复提示。
#
# 退出码：0 健康；1 不健康（诊断信息打印到 stdout）。
set -u
P=clab-campus-lab-

fail=0
note() { echo "  - $1"; }
bad() { echo "  ! $1"; fail=1; }

echo "== 拓扑健康预检 =="

# 0) dockerd 是否在部署之后被重启过（WSL 实例被回收的典型症状）
PIDFILE=.deploy-dockerd-pid
if [ -f "$PIDFILE" ]; then
  depid=$(cat "$PIDFILE" 2>/dev/null | tr -d ' ')
  curpid=$(systemctl show docker -p MainPID --value 2>/dev/null | tr -d ' ')
  if [ -n "$depid" ] && [ -n "$curpid" ] && [ "$depid" != "$curpid" ]; then
    bad "dockerd 在部署后被重启过（部署时 PID=$depid，现在 PID=$curpid）"
    note "WSL 实例被回收或 docker 服务重启，Containerlab 的 veth 链路已丢失"
  fi
fi

# 1) 二层交换机：br0 必须存在且已接入端口
for n in acc-ta acc-tb acc-d1 acc-la acc-lib acc-life dc-sw trust-sw untrust-sw dmz-sw inet-sw ml-sw ml-lan-sw; do
  if ! docker exec "$P$n" true 2>/dev/null; then
    bad "$n 容器不存在或未运行"
    continue
  fi
  brs=$(docker exec "$P$n" sh -c 'ip -o link show type bridge 2>/dev/null | wc -l' 2>/dev/null | tr -d ' ')
  ports=$(docker exec "$P$n" sh -c 'bridge link show 2>/dev/null | wc -l' 2>/dev/null | tr -d ' ')
  if [ "${brs:-0}" -lt 1 ]; then
    bad "$n 没有 bridge（配置未执行或容器重启后未恢复）"
  elif [ "${ports:-0}" -lt 1 ]; then
    bad "$n 的 bridge 没有接入任何端口（二层广播域未建立）"
  fi
done

# 2) 核心层：FRR 进程与 OSPF 邻居
if docker exec "$P"core1 true 2>/dev/null; then
  ospf=$(docker exec "$P"core1 vtysh -c 'show ip ospf neighbor' 2>/dev/null | grep -c Full)
  if [ "${ospf:-0}" -lt 11 ]; then
    bad "core1 OSPF 邻居仅 ${ospf:-0}/11 Full（期望 11）"
  fi
fi

# 3) VRRP：每个 VIP 必须且只能有一个持有者
check_vip() {
  a=$1; b=$2; vip=$3
  ca=$(docker exec "$P$a" sh -c "ip -4 addr show 2>/dev/null | grep -c '$vip'" 2>/dev/null | tr -d ' ')
  cb=$(docker exec "$P$b" sh -c "ip -4 addr show 2>/dev/null | grep -c '$vip'" 2>/dev/null | tr -d ' ')
  total=$(( ${ca:-0} + ${cb:-0} ))
  if [ "$total" -ne 1 ]; then
    bad "VRRP VIP $vip 持有者数量为 $total（$a=${ca:-0} $b=${cb:-0}，期望恰好 1）"
  fi
}
check_vip core1 core2 10.0.100.253
check_vip agg-t1 agg-t2 10.10.0.1
check_vip agg-d1 agg-d2 10.32.0.1
check_vip fw1 fw2 10.0.100.254

if [ "$fail" -ne 0 ]; then
  echo
  echo "预检未通过：实验环境未处于就绪状态，直接跑用例会得到大量无意义失败。" >&2
  echo "请先重新部署实验环境：" >&2
  echo "    cd campus-lab && clab destroy -t campus-lab.clab.yml --cleanup && \\" >&2
  echo "        clab deploy -t campus-lab.clab.yml --timeout 20m" >&2
  echo "部署后需等待约 90 秒让 OSPF / VRRP 收敛，再运行本测试套件。" >&2
  exit 1
fi

echo "预检通过：二层广播域、OSPF 邻居、VRRP 唯一性均正常。"
exit 0
