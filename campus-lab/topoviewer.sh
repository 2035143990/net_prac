#!/bin/sh
# 启动 Containerlab TopoViewer（交互式拓扑查看器）。
#
# 用法：
#   sh topoviewer.sh          # 启动 Web 服务，默认 0.0.0.0:50080
#   sh topoviewer.sh 0.0.0.0:8080
#
# 启动后用浏览器访问：
#   Windows： http://localhost:50080
#   Linux  ： http://<WSL_IP>:50080
#
# 重要：TopoViewer 必须在 WSL 终端里"前台"或带 keeper 进程运行。
# WSL2 实例在没有活跃进程时会被 Windows 回收，届时 veth 链路丢失，
# 拓扑图会显示为断链。本脚本会顺带启动一个 keeper 进程保活。
set -e
cd "$(dirname "$0")"

ADDR=${1:-0.0.0.0:50080}
LOG=.topoviewer.log
PIDFILE=.topoviewer.pid
KEEPER_PIDFILE=.wsl-keeper.pid

if command -v clab >/dev/null 2>&1; then
  CLAB=clab
elif [ -x "$HOME/bin/clab" ]; then
  CLAB="$HOME/bin/clab"
else
  CLAB="./run-clab.sh"
fi

# 清理上一轮残留
if [ -f "$PIDFILE" ]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
if [ -f "$KEEPER_PIDFILE" ]; then
  kill "$(cat "$KEEPER_PIDFILE")" 2>/dev/null || true
  rm -f "$KEEPER_PIDFILE"
fi

# 保活进程：防止 WSL 实例被回收导致 veth 丢失 / TopoViewer 中断
nohup sh -c 'while true; do sleep 60; done' >/dev/null 2>&1 &
echo $! > "$KEEPER_PIDFILE"

echo "==> 启动 TopoViewer: $CLAB graph --srv $ADDR"
nohup "$CLAB" graph --srv "$ADDR" -t campus-lab.clab.yml > "$LOG" 2>&1 &
echo $! > "$PIDFILE"

sleep 8

if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "!! TopoViewer 启动失败，日志：" >&2
  cat "$LOG" >&2
  exit 1
fi

cat "$LOG"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "==> 浏览器访问地址："
echo "    http://localhost:${ADDR##*:}          (Windows 侧)"
[ -n "$IP" ] && echo "    http://$IP:${ADDR##*:}          (同网段其他机器)"
echo
echo "==> 停止：kill \$(cat $PIDFILE) \$(cat $KEEPER_PIDFILE)"
