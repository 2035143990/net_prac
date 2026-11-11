#!/bin/sh
# 主机 / 服务器 / 终端节点启动入口。
#
# 原因同 images/l2/start.sh：containerlab 的 exec 只在 deploy 时跑一次，
# 容器 restart 后 IP 地址、默认路由、dnsmasq 等都会丢失。
# 用 ENTRYPOINT 保证容器每次启动都自动恢复到已配置状态。
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

if [ -f /setup.sh ]; then
    i=0
    until sh /setup.sh; do
        i=$((i+1))
        if [ "$i" -ge 5 ]; then
            echo "warning: /setup.sh 连续 5 次执行失败，放弃" >&2
            break
        fi
        echo "warning: /setup.sh 执行失败，第 $i 次重试" >&2
        sleep 2
    done
fi

# 施加链路速率（containerlab 不支持原生带宽参数，用 tc/netem 实际限速）。
if [ -f /configs/apply-rates.sh ] && [ -f "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" ]; then
    sh /configs/apply-rates.sh "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" || true
fi

exec sleep infinity
