#!/bin/sh
# 二层交换机（Linux bridge）启动入口。
#
# 为什么需要这个入口：containerlab 的 exec 只在 deploy 时执行一次，
# 容器一旦被 restart（宿主机重启 / docker daemon 重启 / 手工 restart），
# exec 不会重跑，容器会回到"未配置"状态——br0 不存在、VLAN 过滤丢失、
# 二层广播域不成立，进而导致 VRRP 双主、跨 VLAN 不可达。
# 把配置放进 ENTRYPOINT 后，容器每次启动都会自愈。
#
# 挂载点约定：/setup.sh（由 campus-lab.clab.yml 的 binds 提供）。
set -e

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

exec sleep infinity
