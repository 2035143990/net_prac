#!/bin/sh
# 链路速率施加脚本（由各镜像 ENTRYPOINT 调用）。
# 台账来源：gen.py 的 LINK_RATES，与设计方案 4.1/4.4/7.2 的速率口径一致。
# 宿主若禁用 tc，脚本不报错退出，仿真功能不受影响。
RATES_FILE="$1"
[ -f "$RATES_FILE" ] || exit 0
command -v tc >/dev/null 2>&1 || exit 0

while read -r IF RATE; do
    [ -n "$IF" ] || continue
    case "$IF" in \#*) continue ;; esac
    [ -e "/sys/class/net/$IF" ] || continue
    BURST=$(awk -v r="$RATE" 'BEGIN{
        n = r; sub(/mbit/, "", n);
        b = int(n / 100); if (b < 32) b = 32;
        printf "%dkbit", b }')
    tc qdisc del dev "$IF" root 2>/dev/null || true
    tc qdisc add dev "$IF" root tbf rate "$RATE" burst "$BURST" latency 50ms 2>/dev/null || true
done < "$RATES_FILE"
exit 0
