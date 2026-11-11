#!/bin/sh
# 部署 / 销毁校园网实验环境。
#
# 用法：
#   sh deploy-lab.sh deploy    # 销毁旧环境、部署新环境、等待收敛
#   sh deploy-lab.sh destroy   # 销毁环境
#
# 两个关键点：
#
# 1) 必须用 clab destroy 清理，不能用 docker rm。
#    Containerlab 依赖自己的状态文件（clab-campus-lab/.state.clab.yaml）
#    追踪容器与 veth；手工 docker rm 会让状态失步，后续 deploy 可能
#    触发二次清理并重建容器。
#
# 2) 部署后记录 dockerd 的 MainPID。
#    WSL2 发行版在没有活跃前台进程时会被 Windows 回收，systemd 随之执行
#    完整关机序列，dockerd 被重启；dockerd 虽然会恢复容器进程，但
#    Containerlab 注入的 veth 链路不会重新注入，二层广播域与 VRRP 全部失效。
#    tests/preflight.sh 会比对记录下来的 PID，准确识别这种状态。
set -e
cd "$(dirname "$0")"

TOPO=campus-lab.clab.yml
PIDFILE=.deploy-dockerd-pid

# 优先使用本机原生 containerlab（WSL / Linux），
# 否则退回用官方容器运行（macOS，需要 Docker Desktop）。
if command -v clab >/dev/null 2>&1; then
  CLAB="clab"
elif [ -x "$HOME/bin/clab" ]; then
  CLAB="$HOME/bin/clab"
else
  CLAB="./run-clab.sh"
fi

action=${1:-deploy}

case "$action" in
  deploy)
    echo "==> 销毁旧环境"
    $CLAB destroy -t "$TOPO" --cleanup || true
    sleep 3

    echo "==> 部署拓扑"
    $CLAB deploy -t "$TOPO" --timeout 20m

    # 记录 dockerd PID，供 preflight 判断环境是否被重启过
    if command -v systemctl >/dev/null 2>&1; then
      systemctl show docker -p MainPID --value 2>/dev/null | tr -d ' ' > "$PIDFILE"
      echo "==> 已记录 dockerd MainPID: $(cat "$PIDFILE")"
    fi

    echo "==> 等待 120 秒让 OSPF / VRRP 收敛"
    sleep 120

    echo "==> 拓扑就绪预检"
    sh tests/preflight.sh || true
    ;;

  destroy)
    echo "==> 销毁环境"
    $CLAB destroy -t "$TOPO" --cleanup || true
    rm -f "$PIDFILE"
    ;;

  *)
    echo "用法: sh deploy-lab.sh [deploy|destroy]" >&2
    exit 2
    ;;
esac
