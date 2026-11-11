# 校园网仿真验证记录

> 关联报告：`docs/course-report-draft.md`
> 验证日期：2026-11-08 ~ 2026-11-11
> 环境：macOS / Docker Desktop / Containerlab（容器方式运行）
> 拓扑：44 个容器、66 条链路

## 1. 验证范围

本轮验证覆盖：

1. 配置生成：`gen.py` 语法、生成数量、脚本语法、幂等性、facts 一致性；
2. 部署运行：44 个容器全部启动；
3. 功能测试：CONN、ROUTE、SEC、DHCP、ISO、NAT、LAG、FAIL 共 64 条用例；
4. 缺陷修复后的 64 条全量回归。

**未完成**：性能、压力、池耗尽、长时间稳定性未测试。

## 2. 配置生成级验证

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 拓扑生成 | `python3 gen.py` | 44 节点 / 66 链路 |
| Python 语法 | `python3 -m py_compile gen.py drawio-postprocess.py tools/report_check.py` | 通过 |
| Shell 语法 | `find configs tests -name '*.sh' -exec sh -n {} \;` | 通过 |
| 幂等性 | 两次生成后排除 `facts.json` 比对 SHA-256 | 完全一致 |
| 报告一致性 | `python3 tools/report_check.py` | `report check OK` |
| 镜像组件 | `dnsmasq --version` | 2.92rel2，满足 `dhcp-relay` 要求 |

## 3. 首次全量测试

- run-id：`20261108T115247Z`
- 开始：2026-11-08T11:52:47Z
- 结束：2026-11-08T11:54:32Z
- 环境：44 个容器全部 running
- 结果：**61 / 64 通过，3 失败，0 跳过**

| 套件 | 通过/总数 | 失败用例 |
| --- | --- | --- |
| CONN | 10/10 | — |
| ROUTE | 8/8 | — |
| SEC | 6/6 | — |
| DHCP | 8/8 | — |
| ISO | 11/12 | ISO-09 |
| NAT | 7/7 | — |
| LAG | 7/7 | — |
| FAIL | 4/6 | FAIL-04、FAIL-06 |

原始结果位于 `campus-lab/tests/results/20261108T115247Z/`，包含 `results.jsonl`、`summary.txt` 与 `raw/<case>.log`。

### 3.1 最终全量回归（2026-11-11）

- run-id：`20261111T062929Z`
- 环境：44 个容器全部 running
- 结果：**64 / 64 通过，0 失败，0 跳过**

| 套件 | 通过/总数 |
| --- | --- |
| CONN | 10/10 |
| ROUTE | 8/8 |
| SEC | 6/6 |
| DHCP | 8/8 |
| ISO | 12/12 |
| NAT | 7/7 |
| LAG | 7/7 |
| FAIL | 6/6 |
| **合计** | **64/64** |

原始结果位于 `campus-lab/tests/results/20261111T062929Z/`。

本轮新增修复：

1. `tests/run-all.sh` 在套件执行前等待 `core1/core2` 的 OSPF Full 邻居数达到 11，避免部署后抢跑造成 CONN/ROUTE/DHCP 假失败；
2. 按设计方案 5.1 补全教学区（10.10–10.14）、实验区（10.20–10.27）、宿舍区（10.32–10.49、10.96–10.106）的 ACL 地址集合；
3. 按设计方案 6.6 增加生活区 → 教学/实验/宿舍/图书馆/数据中心/管理网阻断，以及数据中心 → Untrust/Internet 阻断。抽查结果：生活区 → 教学区阻断、生活区 → Internet 放行、数据中心 → Internet 阻断。

## 4. 关键实测证据

### 4.1 DHCP

三台动态终端均通过 Relay 从 `srv-dc1` 取得地址：

| 终端 | VLAN | 地址 | 网关 | DNS | 租期 |
| --- | --- | --- | --- | --- | --- |
| `pc-dyn1` | 101 | 10.10.0.133 | 10.10.0.1 | 10.60.0.10 | 14400 |
| `pc-dyn2` | 301 | 10.32.0.134 | 10.32.0.1 | 10.60.0.10 | 43200 |
| `pc-dyn3` | 500 | 10.50.0.135 | 10.50.0.1 | 10.60.0.10 | 14400 |

服务器租约文件同时记录三台客户端 MAC，DHCP-01~DHCP-08 全部通过。

### 4.2 OSPF / LAG

- `core1` OSPF Full 邻居：11；
- `core1 bond0`：`Bonding Mode: IEEE 802.3ad Dynamic link aggregation`，`Transmit Hash Policy: layer3+4`；
- `srv-dc1 bond0`：active-backup；
- 成员故障实验 LAG-07 通过，业务未中断。

### 4.3 安全与 NAT

- Internet → `198.51.100.80:80/443` 可访问 DMZ；
- Internet → DMZ 私网地址 `10.80.0.10` 失败；
- Internet → Trust、Internet → 宿舍区、DMZ → Trust 均失败；
- DNAT / 私网直达丢弃 / SNAT 计数器均命中；
- NAT-01~NAT-07、SEC-01~SEC-06 全部通过。

### 4.4 故障切换

- FAIL-01~FAIL-03 通过：core1 keepalived 停止后 core2 接管 Trust VIP，业务不中断，core1 恢复后重新抢占；
- FAIL-05 通过：fw1 keepalived 停止后 fw2 接管 Trust VIP；
- FAIL-04 首次失败：上联恢复后 30 秒内未观察到 OSPF 邻居恢复；
- FAIL-06 首次失败：核心邻居数为 10，是 FAIL-04 的连带结果。

## 5. 缺陷与修复

### 5.1 DHCP 客户端未配置地址

**现象**：服务器租约文件已有记录，但客户端 `/tmp/dhcp.env` 与 `eth1` 地址为空。

**根因**：`udhcpc.sh` 由 `gen.py` 生成后权限为 644，busybox `udhcpc` 直接执行脚本失败，未报错。

**修复**：动态终端启动前执行 `chmod +x /configs/udhcpc.sh`。

### 5.2 DHCP Relay `Network unreachable`

**现象**：Relay 日志持续输出 `failed to send packet: Network unreachable`，但汇聚已能 ping 通 DHCP 服务器。

**根因**：Relay 在 OSPF 路由收敛前启动，失败后不再重试。

**修复**：`start-services.sh` 最多等待 120 秒路由；未就绪时转入后台延迟启动循环。

### 5.3 核心 ACL 只加载前两条规则

**现象**：`core1` 的 `table inet zone` 只有 `zone.established` 与 `iso.dhcp`，缺少管理网规则，导致管理终端访问业务区失败。

**根因**：prestart 阶段 ACL 加载不完整，且核心没有 `start-services.sh` 做二次加载。

**修复**：`images/frr/start.sh` 在 `frrinit` 后删除并重载 `acl.nft`，核心与汇聚统一生效。

### 5.4 管理流量回程不对称

**现象**：`mgmt-pc → pc-ta1` 去程经 `agg-t2`，回程经 `agg-t1`；汇聚的无状态管理目的拦截把回程当作新会话丢弃。

**修复**：

1. 管理目的拦截从全部汇聚上移至 `core1/core2`；
2. 每台汇聚增加 `10.70.0.0/24` 静态回程路由：core1 下一跳 distance 1，core2 下一跳 distance 2；
3. 管理源放行保留在汇聚与核心。

复核：`mgmt-pc ping 10.10.0.11` 两次请求两次响应，丢包率 0%。

### 5.5 FAIL-04 等待窗口不足

**修复**：OSPF 邻居恢复等待窗口从 30 秒提高到 90 秒。复核邻居可恢复为 Full。

## 6. 修复后复核

| 项目 | 命令/对象 | 结果 |
| --- | --- | --- |
| 核心 OSPF | `core1 show ip ospf neighbor` | 11 条 Full |
| 核心 ACL | `core1 nft list table inet zone` | 管理三条规则完整 |
| 管理可达 | `mgmt-pc ping 10.10.0.11` | 0% 丢包 |
| DHCP | 三台动态终端 | 地址/网关/DNS/租期正确 |
| 核心聚合 | `core1 /proc/net/bonding/bond0` | 802.3ad，两成员 up |
| 服务器聚合 | `srv-dc1 bond0` | active-backup |
| 生活区隔离 | `pc-life ping 10.10.0.11` | 阻断 |
| 生活区出网 | `pc-life ping 203.0.113.100` | 放行 |
| 数据中心出校 | `srv-dc1 ping 203.0.113.100` | 阻断 |
| 最终全量回归 | `sh tests/run-all.sh` | 64/64 通过（run-id `20261111T062929Z`） |

最终全量回归已执行：**64/64 全部通过，0 失败，0 跳过**。首次运行中的 3 项失败均已定位并修复；测试抢跑问题也已通过收敛预检消除。

## 7. 复现命令

```sh
cd net_prac/campus-lab
sh build-images.sh
python3 gen.py
sh run-clab.sh deploy -t campus-lab.clab.yml
sh tests/run-all.sh
```

如需重新验证或更新拓扑图：

```sh
sh tests/run-all.sh
sh gen-drawio.sh
```

并将新的 `run-id`、`summary.txt`、关键 `raw/*.log` 与拓扑图归档。

## 8. 现场演示流程

本节给出答辩现场的可执行演示流程：先按 8.1 准备环境，再按 8.2 的顺序串讲。总时长约 7 分钟。口径稿见 `demo-qa-checklist.md`，本节只列命令与口播要点。

### 8.1 环境准备

前置：Docker Desktop 已安装并分配至少 4 GB 内存 / 4 CPU。首次构建过四个本地镜像（`sh build-images.sh`）且 `gen.py` 已生成拓扑与配置。

一键准备脚本（在 `campus-lab/` 目录下执行）：

```sh
open -a Docker                                       # 1. 启动 Docker Desktop，等菜单栏图标变绿
cd net_prac/campus-lab

sh run-clab.sh destroy -t campus-lab.clab.yml --cleanup 2>/dev/null  # 2. 清理上次残留（首次可跳过）
sh run-clab.sh deploy  -t campus-lab.clab.yml        # 3. 部署 44 节点（约 1–2 分钟）

docker rm -f clab-graph 2>/dev/null                  # 4. 起拓扑可视化（端口映射版，宿主机可访问）
docker run -d --name clab-graph -p 50080:50080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD":"$PWD" -w "$PWD" \
  ghcr.io/srl-labs/clab \
  containerlab graph -t campus-lab.clab.yml

sleep 25                                             # 5. 等 OSPF/VRRP/DHCP 收敛
```

收敛确认（应分别得到 44、11、业务 IP）：

```sh
docker ps --filter name=clab-campus-lab- --format '{{.Names}}' | wc -l          # 应为 44
docker exec clab-campus-lab-core1 vtysh -c 'show ip ospf neighbor' | grep -c Full # 应为 11
docker exec clab-campus-lab-pc-dyn1 ip -br addr show eth1                        # 应有 10.10.0.x
```

浏览器打开 `http://localhost:50080` 确认拓扑图可访问。

> 注意：必须用 `run-clab.sh` 部署（带 `--pid=host`），否则 veth 链路无法挂进容器命名空间，业务接口不会出现。`/etc/hosts` 写入失败的报错是非阻塞的，可忽略。

### 8.2 演示顺序

按以下 7 步串讲，分三档节奏：重点展开（现场跑命令）、一句话带过（报数字）、主动声明边界（防追问）。

| 步 | 对应 Q | 节奏 | 时长 |
| --- | --- | --- | --- |
| ① 开场锁口径 | — | 口播 | 30s |
| ② 拓扑图 | Q1/Q5 | 一句话 | 30s |
| ③ 连通性 + 流向 | Q4 | 现场演示 | 1.5min |
| ④ 防火墙 NAT | Q9 | 现场演示 | 1min |
| ⑤ 双机切换 | Q10 | 现场演示 | 1.5min |
| ⑥ 自动化校验 | Q13 | 现场演示 | 1min |
| ⑦ 边界声明 | Q2/Q7/Q11 | 主动声明 | 1min |

**① 开场锁口径（30s）**

> 「奉贤校区校园网仿真。先统一两个称谓：任务书原文的**梅陇校区**即评委说的**徐汇校区**，统一叫**梅陇（即徐汇）校区**。跨校区链路是**设计覆盖、仿真未建模**——R2 备连梅陇，仿真只建了 internet 节点，这是有意的仿真边界。」

**② 拓扑图（30s，一句话带过 Q1/Q5/Q6/Q8）**

浏览器展示 `http://localhost:50080`：

> 「44 个容器、66 条链路，双核心 + 分区域双汇聚 + 出口双路由 + 双防火墙 + DMZ。**6 大功能区**加出口 DMZ 安全区，**11 个 VLAN**，一栋楼一个子网，预算约 **687 万元**。数字都以 `configs/facts.json` 为单一事实源。」

**③ 连通性 + 流量流向（1.5min，现场演示 Q4）**

```sh
docker exec clab-campus-lab-pc-dyn1 traceroute -n -w 1 -q 1 -m 8 203.0.113.100
```

> 「CONN-09，教学区动态终端访问 Internet。traceroute 5 跳：**接入 → 汇聚 VRRP 网关 → 核心 → 防火墙 → 出口路由 → Internet**。该通的 100% 通，该断的必须断——宿舍到管理网、教学区是阻断的，不通才是正确结果。首次全量 61/64，3 条已修复并复核关键路径，全量回归答辩前补跑。」

**④ 防火墙 NAT（1min，现场演示 Q9）**

```sh
docker exec clab-campus-lab-fw1 conntrack -L | grep 203.0.113.100 | head -3
```

> 「fw1/fw2 双机，nftables 三区策略。conntrack 看到 SNAT 把源地址从 `10.10.0.133` 改写成 `10.90.1.11`，对应 eth1→eth2 的 masquerade。DMZ 这边 DNAT `198.51.100.80:80/443 → 10.80.0.10` 对外发布 Web。」

**⑤ 双机切换（1.5min，现场演示 Q10）**

```sh
docker exec clab-campus-lab-pc-dyn1 ping -c 30 -i 0.5 203.0.113.100 &  # 持续 ping，后台
docker stop clab-campus-lab-core1                                       # 停主核心，观察 ping 不中断
docker start clab-campus-lab-core1                                     # 恢复，core1 重新抢占
```

> 「停 core1，业务不中断——core2 通过 VRRP 接管 VIP。恢复后 core1 重新抢占。防火墙、出口、核心 bond0 都是双机/双链路。**如实交代**：DHCP/DNS 所在 srv-dc1 是单实例，srv-dc2 已建模未承载，这是设计与仿真的已知差距。」

**⑥ 自动化校验（1min，现场演示 Q13）**

```sh
cd net_prac && python3 tools/report_check.py
```

> 「`facts.json` 是单一事实源，`report_check.py` 逐键比对报告数字，输出 `report check OK`。8 个套件 64 条用例，退出码 0/1/2 区分通过/失败/环境不可用。」

**⑦ 边界主动声明（1min，不要等被问 Q2/Q7/Q11）**

> 「三个边界主动交代：**跨校区**仿真只覆盖奉贤校内，梅陇侧由 R2 承载，设计文档有完整出口方案；**FTP** 本期未部署，DMZ 已具备承载能力，属预留项；**无线**仿真验证 VLAN、地址池、认证策略，射频覆盖需真实环境勘测。」

### 8.3 演示后清理

```sh
docker stop clab-graph && docker rm clab-graph
sh run-clab.sh destroy -t campus-lab.clab.yml --cleanup
```