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
#
# 挂载点约定：
#   /setup.sh               由 campus-lab.clab.yml 的 binds 提供
#   /configs/rates/*.rates  本节点的链路速率台账（由 gen.py 生成）
#   /configs/apply-rates.sh 链路速率施加脚本
set -e

# 传入命令参数时直接执行该命令，不进入常驻模式。
# build-images.sh 用 `docker run --rm <image> dnsmasq --version` 校验镜像内
# 工具版本，若入口忽略参数会永远 sleep，校验脚本将挂死。
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

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

# 施加链路速率（containerlab 不支持原生带宽参数，用 tc/netem 实际限速）。
if [ -f /configs/apply-rates.sh ] && [ -f "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" ]; then
    sh /configs/apply-rates.sh "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" || true
fi

exec sleep infinity
