#!/bin/sh
# 防火墙节点启动入口。
#
# 原因同 images/l2/start.sh：containerlab 的 exec 只在 deploy 时跑一次，
# 容器 restart 后 nftables 规则、接口地址、VRRP 都会丢失。
#
# 防重入：setup.sh 里会拉起 keepalived 守护进程，若此处再执行一次，
# 同一个节点上会出现两套 keepalived 实例，两边都把 VIP 装到内核上，
# 形成 VRRP 双主、ARP 冲突、流量黑洞（ROUTE-07/08 期望 1 个持有者却得到 2 个）。
# 因此启动前先杀掉历史实例，再执行 setup.sh。
set -e

pkill -x keepalived 2>/dev/null || true
sleep 1

if [ -f /setup.sh ]; then
    i=0
    until sh /setup.sh; do
        i=$((i+1))
        if [ "$i" -ge 5 ]; then
            echo "warning: /setup.sh 连续 5 次执行失败，放弃" >&2
            break
        fi
        echo "warning: /setup.sh 执行失败，第 $i 次重试" >&2
        pkill -x keepalived 2>/dev/null || true
        sleep 2
    done
fi

exec sleep infinity
