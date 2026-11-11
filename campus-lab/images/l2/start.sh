#!/bin/sh
# 二层交换机（Linux bridge）启动入口。
#
# 为什么需要这个入口：containerlab 的 exec 只在 deploy 时执行一次，
# 容器一旦被 restart（宿主机重启 / docker daemon 重启 / 手工 restart），
# exec 不会重跑，容器会回到"未配置"状态——br0 不存在、VLAN 过滤丢失、
# 二层广播域不成立，进而导致 VRRP 双主、跨 VLAN 不可达。
# 把配置放进 ENTRYPOINT 后，容器每次启动都会自愈。
#
# 挂载点约定：
#   /setup.sh            由 campus-lab.clab.yml 的 binds 提供
#   /configs/rates/*.rates  本节点的链路速率台账（由 gen.py 生成）
#   /configs/apply-rates.sh 链路速率施加脚本
set -e

# 传入命令参数时直接执行该命令，不进入常驻模式。
# build-images.sh 用 `docker run --rm <image> dnsmasq --version` 校验镜像内
# 工具版本，若入口忽略参数会永远 sleep，校验脚本将挂死。
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# setup.sh 依赖 veth 接口已注入 netns，而容器起来的瞬间 containerlab
# 可能还没完成注入，因此 setup.sh 内部带等待逻辑；这里再做一层重试，
# 覆盖「等待超时」等边界情况。
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

# 施加链路速率（容器lab 不支持原生带宽参数，用 tc/netem 实际限速）。
# 限速必须在接口 up 之后进行，因此放在 setup.sh 之后。
if [ -f /configs/apply-rates.sh ] && [ -f "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" ]; then
    sh /configs/apply-rates.sh "/configs/rates/$(cat /etc/hostname 2>/dev/null).rates" || true
fi

exec sleep infinity
