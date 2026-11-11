#!/bin/sh
# 主机 / 服务器 / 终端节点启动入口。
#
# 原因同 images/l2/start.sh：containerlab 的 exec 只在 deploy 时跑一次，
# 容器 restart 后 IP 地址、默认路由、dnsmasq 等都会丢失。
# 用 ENTRYPOINT 保证容器每次启动都自动恢复到已配置状态。
#
# 挂载点约定：/setup.sh（由 campus-lab.clab.yml 的 binds 提供）。
set -e

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

exec sleep infinity
