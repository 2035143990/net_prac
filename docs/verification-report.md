# 校园网仿真验证记录

> 关联报告：`docs/course-report-draft.md`
> 验证日期：2026-11-08 ~ 2026-11-11
> 环境：
> - macOS / Docker Desktop / Containerlab（容器方式运行）
> - Windows / WSL2 Ubuntu-24.04 / Docker Engine 29.1.3 / Containerlab 0.83.0（原生 Linux 内核内运行）
>
> 拓扑：49 个容器、72 条链路

## 1. 验证范围

本轮验证覆盖：

1. 配置生成：`gen.py` 语法、生成数量、脚本语法、幂等性、facts 一致性；
2. 部署运行：49 个容器全部启动，72 条 veth 链路全部建立；
3. 功能测试：CONN、ROUTE、SEC、DHCP、ISO、NAT、LAG、FAIL、WIRELESS、RATE 共 **85 条用例，全部通过**；
4. 缺陷修复后全量回归复跑。

**已完成**：补齐三项缺口后的 85 条全量回归已重跑并全部通过（run-id `20261111T135749Z`，前一轮 `20261111T135011Z` 结果一致）。

**未完成**：性能、压力、地址池耗尽、长时间稳定性未测试。

## 2. 配置生成级验证

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 拓扑生成 | `python3 gen.py` | 49 节点 / 72 链路 |
| Python 语法 | `python3 -m py_compile gen.py drawio-postprocess.py tools/report_check.py` | 通过 |
| Shell 语法 | `find configs tests -name '*.sh' -exec sh -n {} \;` | 通过 |
| 幂等性 | 两次生成后排除 `facts.json` 比对 SHA-256 | 完全一致 |
| 报告一致性 | `python3 tools/report_check.py` | `report check OK` |
| 镜像组件 | `dnsmasq --version` | 2.92，满足 `dhcp-relay` 要求 |

## 3. 全量测试

- run-id：`20261109T150150Z`（复现 run-id：`20261109T153144Z`，结果一致）
- 开始：2026-11-09T15:01:51Z
- 结束：2026-11-09T15:04:24Z
- 环境：44 个容器全部 running，OSPF Full 邻居 11
- 结果：**65 / 65 通过，0 失败，0 跳过**

| 套件 | 通过/总数 | 失败用例 |
| --- | --- | --- |
| CONN | 10/10 | — |
| ROUTE | 8/8 | — |
| SEC | 6/6 | — |
| DHCP | 8/8 | — |
| ISO | 13/13 | — |
| NAT | 7/7 | — |
| LAG | 7/7 | — |
| FAIL | 6/6 | — |

原始结果位于 `campus-lab/tests/results/20261111T122017Z/`，包含 `results.jsonl`、`summary.txt` 与 `raw/<case>.log`。

## 3.1 历史测试轮次

| run-id | 环境 | 结果 | 说明 |
| --- | --- | --- | --- |
| `20261108T115247Z` | macOS / Docker Desktop | 61/64 | 首轮，3 项失败（ISO-09、FAIL-04、FAIL-06），均已定位修复 |
| `20261109T135137Z` | Windows / WSL2 | 29/64 | 迁移到 WSL 后首轮，keepalived 未启动导致大面积失败 |
| `20261109T141507Z` | Windows / WSL2 | 62/64 | keepalived 修复后，仅余 CONN-04 与 FAIL-03 |
| `20261109T150150Z` | Windows / WSL2 | **65/65** | 全部修复后全量回归通过 |
| `20261109T153144Z` | Windows / WSL2 | **65/65** | 复现轮次，结果一致 |
| `20261109T155017Z` | Windows / WSL2 | **65/65** | `gen.py` 行尾修复后重建部署再跑，结果一致 |
| `20261110T031032Z` | Windows / WSL2 | 37/65 | 宿主机重启后 containerlab `exec` 未重跑，二层广播域与 VRRP 双主（详见 5.11） |
| `20261110T064550Z` | Windows / WSL2 | **65/65** | ENTRYPOINT 自愈 + ACL 方向修复 + 预检机制后，干净部署全量回归通过 |
| `20261110T065801Z` | Windows / WSL2 | **65/65** | 上述修复的复现轮次，结果一致 |
| `20261111T062929Z` | Windows / WSL2 | 64/64 | 远程侧回归（区域地址规划 + 新增 ACL 当时 ISO 为 12 条） |
| `20261111T122017Z` | Windows / WSL2 | **65/65** | 合并 WSL 侧修复与远程 ACL 后，ISO 恢复 13 条，全量回归通过 |
| `20261111T133133Z` | Windows / WSL2 | 83/85 | 补齐链路速率、实验区无线、梅陇校区三缺口后首轮；WIRELESS-04、WIRELESS-10 失败 |
| `20261111T135011Z` | Windows / WSL2 | **85/85** | 修正 DNS 断言与校区回程断言后全量通过 |
| `20261111T135749Z` | Windows / WSL2 | **85/85** | 用例编号统一为 WIRELESS-xx 后的复现轮次，结果一致 |
| `20261111T140838Z` | Windows / WSL2 | **85/85** | 干净重建部署（destroy + deploy）后的终验轮次，结果一致 |
| `20261111T143222Z` | Windows / WSL2 | **85/85** | 修正 `facts.json` 跨平台编码后，重建镜像并重新部署的终验轮次 |
| `20261111T145644Z` | Windows / WSL2 | **85/85** | 完整复现链（regen → rebuild → destroy+deploy → test），结果一致 |

### 3.1 最终全量回归（2026-11-11）

- run-id：`20261111T145644Z`（复现 run-id：`20261111T135011Z`、`20261111T135749Z`、`20261111T140838Z`、`20261111T143222Z`，结果一致）
- 环境：49 个容器全部 running，72 条 veth 链路全部建立
- 结果：**85 / 85 通过，0 失败，0 跳过**

| 套件 | 通过/总数 |
| --- | --- |
| CONN | 10/10 |
| ROUTE | 8/8 |
| SEC | 6/6 |
| DHCP | 8/8 |
| ISO | 13/13 |
| NAT | 7/7 |
| LAG | 7/7 |
| FAIL | 6/6 |
| WIRELESS | 11/11 |
| RATE | 9/9 |
| **合计** | **85/85** |

原始结果位于 `campus-lab/tests/results/20261111T145644Z/`。

本轮新增修复：

1. `tests/run-all.sh` 在套件执行前等待 `core1/core2` 的 OSPF Full 邻居数达到 11，避免部署后抢跑造成 CONN/ROUTE/DHCP 假失败；收敛等待之后再执行拓扑预检；
2. 按设计方案 5.1 补全教学区（10.10–10.14）、实验区（10.20–10.27）、宿舍区（10.32–10.49、10.96–10.106）的 ACL 地址集合；
3. 按设计方案 6.6 增加生活区 → 教学/实验/宿舍/图书馆/数据中心/管理网阻断，以及数据中心 → Untrust/Internet 阻断。抽查结果：生活区 → 教学区阻断、生活区 → Internet 放行、数据中心 → Internet 阻断；
4. 「教学区 → 宿舍区」阻断规则原先只挂在 `dorm_filter` 链（仅 `saddr ∈ @dorm_nets` 时才跳转），教学区出向流量根本进不去，现已在 forward 基础链增加 `ip saddr @teaching_nets ip daddr @dorm_nets counter drop`；
5. WSL2 实例被 Windows 回收导致 dockerd 重启、veth 链路丢失，预检现会比对部署时记录的 dockerd MainPID 并给出准确提示。

补齐三项缺口时新增的修复见 5.14 ~ 5.18。

## 4. 关键实测证据

### 4.1 拓扑与链路

- 容器：49 个全部 running；
- 二层：宿主机侧生成 73 对 veth，容器内 `eth1`~`eth13`、`bond0` 及 VLAN 子接口（如 `eth13.70`、`eth3.510`、`eth3.301`）全部就位；
- 三层：`core1` OSPF Full 邻居 11。

### 4.2 DHCP

三台动态终端均通过 Relay 从 `srv-dc1` 取得地址：

| 终端 | VLAN | 地址 | 网关 | DNS | 租期 |
| --- | --- | --- | --- | --- | --- |
| `pc-dyn1` | 101 | 10.10.0.133 | 10.10.0.1 | 10.60.0.10 | 14400 |
| `pc-dyn2` | 301 | 10.32.0.134 | 10.32.0.1 | 10.60.0.10 | 43200 |
| `pc-dyn3` | 500 | 10.50.0.135 | 10.50.0.1 | 10.60.0.10 | 14400 |

服务器租约文件同时记录三台客户端 MAC，DHCP-01~DHCP-08 全部通过。

### 4.3 OSPF / LAG

- `core1` OSPF Full 邻居：11；
- `core1 bond0`：`Bonding Mode: IEEE 802.3ad Dynamic link aggregation`，`Transmit Hash Policy: layer3+4`；
- `srv-dc1 bond0`：active-backup；
- 成员故障实验 LAG-07 通过，业务未中断。

### 4.4 安全与 NAT

- Internet → `198.51.100.80:80/443` 可访问 DMZ；
- Internet → DMZ 私网地址 `10.80.0.10` 失败；
- Internet → Trust、Internet → 宿舍区、DMZ → Trust 均失败；
- DNAT / 私网直达丢弃 / SNAT 计数器均命中；
- NAT-01~NAT-07、SEC-01~SEC-06 全部通过。

### 4.5 故障切换

- FAIL-01~FAIL-03 通过：core1 keepalived 停止后 core2 接管 Trust VIP，业务不中断，core1 恢复后重新抢占；
- FAIL-05 通过：fw1 keepalived 停止后 fw2 接管 Trust VIP；
- FAIL-04 通过：上联恢复后 OSPF 邻居可恢复为 Full（等待窗口 90 秒）；
- FAIL-06 通过：故障实验后核心 OSPF 邻居恢复为 11。

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

### 5.6 FRR 节点从未启动 keepalived，VRRP VIP 全网缺失

**现象**：迁移到 WSL 后首轮测试 29/64 通过。core1 的 `show vrrp` 无输出，容器内没有 keepalived 进程，VIP（`10.0.100.253`、`10.60.0.1`、`10.70.0.1`）全部未被占用。跨网段流量因缺少默认网关而失败。

**根因**：`gen.py` 的 `gen_prestart()` 负责生成 FRR 节点的启动脚本，但只生成接口、bond、VLAN 与 ACL 配置，从未启动 keepalived；`gen_keepalived()` 仅生成配置文件。防火墙节点的 `gen_fw()` 里有启动命令，FRR 节点侧却缺失。

**修复**：`gen_prestart()` 在节点存在 VRRP 实例时追加 keepalived 启动命令（14 个 FRR 节点受影响）。

### 5.7 keepalived 拒绝加载可执行权限的配置文件

**现象**：加上启动命令后 keepalived 进程仍然秒退，日志为
`Configuration file '/configs/keepalived.conf' is not a regular non-executable file - skipping`。

**根因**：配置文件通过 bind mount 从 `/mnt/d`（Windows NTFS）挂载进来，权限为 `0777`（带可执行位）。keepalived 出于安全考虑拒绝加载带可执行位的文件。

**修复**：启动前先把配置复制到容器本地文件系统并去掉可执行位：

```sh
cp /configs/keepalived.conf /etc/keepalived.conf
chmod 0644 /etc/keepalived.conf
keepalived -D -f /etc/keepalived.conf >/var/log/keepalived.log 2>&1 &
```

`gen_fw()` 同步采用相同做法。

### 5.8 FAIL-03 恢复 keepalived 时同样踩到权限问题

**现象**：FAIL-03「core1 恢复后重新抢占 VIP」失败。

**根因**：测试用 `docker cp` 把配置复制进容器，复制过来的文件同样是 `0777`，keepalived 拒绝加载。

**修复**：复制后执行 `chmod 0644` 再启动。FAIL-05 中 fw1 的重启逻辑同步修正。

### 5.9 CONN-04 断言与访问控制矩阵矛盾

**现象**：「教学区 → 宿舍区 VLAN301」不可达，CONN-04 失败。

**根因**：断言本身与设计意图冲突。设计方案的访问控制矩阵中「教学区 → 宿舍区」为 ✗（宿舍区为隔离区域，仅放行宿舍互访、DNS、Internet 与 DMZ 发布服务）；`agg-d1` 的 `dorm_filter` 正是按此矩阵实现，ISO-02、ISO-10、ISO-12 等用例也验证了该行为。

**修复**：CONN-04 改为断言不可达，并新增 ISO-13「教学区 → 宿舍区阻断」显式覆盖该验证点，用例总数由 64 增至 65。

### 5.10 仓库内 shell 脚本行尾为 CRLF

**现象**：在 WSL 下执行 `sh build-images.sh` 报 `set: Illegal option -`、`cd: $'.\r': No such file or directory`。

**根因**：Windows 全局 `core.autocrlf=true` 且仓库缺少 `.gitattributes`，检出后全部 82 个 `.sh` 脚本被转成 CRLF，Linux 下无法解析。

**修复**：

1. 新增 `.gitattributes`，对 `*.sh` 等文本文件强制 `eol=lf`；
2. 新增 `tools/fix-eol.py`，一次性把仓库内 157 个文本文件转换为 LF，且幂等；
3. **根因修复**：`gen.py` 的 `w()` 原本用 `open(path, "w")`，在 Windows 上会按平台默认做换行转换，生成的脚本仍是 CRLF。改为 `open(path, "w", newline="")` 关闭转换，使生成物在任何平台都是 LF（`configs/` 下 CRLF 文件数实测为 0）。

### 5.11 容器重启后配置不恢复，导致大面积用例失败

**现象**：run-id `20261110T031032Z` 得分 37/65，CONN 9 条失败、ISO 5 条失败、NAT 5 条失败。典型症状是连同网段互访（`pc-ta1` → `pc-ta2`）都不通，`ROUTE-07`/`ROUTE-08` 期望「VIP 持有者恰好 1 个」却得到 2 个。

**排查过程**：

1. Docker Desktop 未运行，WSL 内 `dockerd` 为 `active`，44 个容器全部 running，容器数量检查无异常；
2. `core1` OSPF Full 邻居为 11、`10.0.100.253` 已在 `core1` 的 `eth12` 上——三层正常；
3. 但 `core1` 上同时存在两套 keepalived（`/etc/keepalived.conf` 与 `/tmp/keepalived.conf` 各一套），`agg-t1`/`agg-t2` 同时持有 `10.10.0.1`，`agg-d1`/`agg-d2` 同时持有 `10.32.0.1`——**VRRP 双主**；
4. 抓包显示 `agg-t1` 只看得到自己的 VRRP 通告，看不到 `agg-t2` 的，反之亦然；
5. 检查二层设备，发现 **7 个接入交换机的 `br0` 全部不存在**（`bridge link show` 输出为空），`trust-sw` 的 `br0` 存在但无任何端口接入——二层广播域根本没有建立；
6. `docker inspect` 显示所有容器 `Created` 为 2026-11-09T15:46Z，而 `Started` 统一变为 2026-11-10T03:08:35Z，即**宿主机重启后 Docker 恢复容器，但 containerlab 的 `exec` 不会重跑**。

**根因**：拓扑配置依赖 containerlab 的 `exec:` 字段执行 `setup.sh`，而 **`exec` 只在 `clab deploy` 时执行一次**。容器被 restart（宿主机重启、`dockerd` 重启、手工 `docker restart`）后，`setup.sh` 不会重跑：二层交换机失去 `br0` 与 VLAN 过滤，主机失去 IP 与默认路由，防火墙失去 nftables 规则与 VRRP。FRR 节点因镜像自带 ENTRYPOINT 而能自愈，这掩盖了问题的范围。

**修复**：

1. 为 `campus-l2`、`campus-host`、`campus-fw` 三个镜像新增 ENTRYPOINT 启动脚本（`images/{l2,host,fw}/start.sh`），在容器每次启动时执行挂载的 `/setup.sh`；
2. 拓扑文件中移除全部 `exec:` 字段，配置统一由 ENTRYPOINT 驱动；
3. `gen.py` 为二层、主机、防火墙的 `setup.sh` 统一注入 veth 接口就绪等待（`wait_for_ifaces`），避免容器启动瞬间接口尚未注入导致 `set -e` 中止；
4. `gen.py` 与 `images/frr/start.sh` 在启动 keepalived 前先 `pkill -x keepalived`，避免容器重启后旧实例与新实例并存形成 VRRP 双主；
5. keepalived 配置的加载统一收敛到镜像 ENTRYPOINT 一处（`prestart.sh` 只负责复制配置与去可执行位），消除双实例来源。

**验证**：干净部署后 65/65 通过（run-id `20261110T064550Z`、`20261110T065801Z`）。

### 5.12 访问控制矩阵中「教学区 → 宿舍区」的规则方向错误

**现象**：修复 5.11 后 CONN-04、ISO-13（均为「教学区 → 宿舍区应阻断」）失败，`pc-ta1` 反而能 ping 通 `10.32.0.11`。

**根因**：`agg-d1` 的 nftables 规则把「教学区 → 宿舍区阻断」写在了 `dorm_filter` 链内：

```
ip saddr @dorm_nets jump dorm_filter      # 只有源属于宿舍网段的流量才进入该链
...
chain dorm_filter {
  ip daddr @teaching_nets counter drop comment "iso.dorm2teaching"
}
```

教学区发往宿舍区的流量源地址不属于 `@dorm_nets`，**根本不会跳进 `dorm_filter`**，链内的 drop 规则永远不会命中，等同虚设。ISO-02、ISO-10、ISO-12 等用例验证的是「宿舍区 → 教学区」方向，恰好绕开了这个缺口，因此长期未被发现。

**修复**：在 `forward` 主链中补充源、宿双向匹配的规则，位置放在 `jump dorm_filter` 之前：

```
ip saddr @teaching_nets ip daddr @dorm_nets counter drop comment "iso.teaching2dorm"
```

**验证**：热加载后 `iso.teaching2dorm` 计数器命中 2 包，`pc-ta1 → 10.32.0.11` 100% 丢包，而宿舍区互访、宿舍区 → Internet、教学区 → 图书馆均不受影响；随后干净部署复跑 65/65 通过。

### 5.13 缺少实验环境就绪状态的预检

**现象**：环境损坏时（5.11 场景）`run-all.sh` 只检查容器数量，44 个容器齐全便继续执行，最终输出一份 37/65 的"测试报告"，极易被误判为功能缺陷。

**修复**：新增 `tests/preflight.sh` 并接入 `run-all.sh`，在执行用例前校验：

- 13 台二层设备的 `br0` 存在且已接入端口（补入梅陇互联的 `ml-sw` 与 `ml-lan-sw`）；
- `core1` 的 OSPF Full 邻居为 11；
- 四组 VRRP VIP（核心、两个汇聚、防火墙）各自恰好有 1 个持有者。

任一项不满足即以退出码 2 终止，并输出 `result=ENV_UNAVAILABLE` 及重新部署命令，不再产出无意义的用例级失败。

### 5.14 VLAN 510 在汇聚层跨楼栋桥接导致二层环路

**现象**：为让宿舍区与实验区共用无线子网，最初在 `agg-d1:eth4 ↔ agg-l1:eth4`（备用 `agg-d2:eth4 ↔ agg-l2:eth4`）桥接 VLAN 510。结果广播帧在环中无限循环、ARP 应答成倍回流、VRRP 出现双主，表现为大量 ping 超时。

**根因**：广播域跨过 `agg-d1 → acc-d1 → agg-d2 → agg-l2 → acc-la → agg-l1 → agg-d1` 整圈。接入交换机虽各自启用了 STP，但 Linux 桥的 BPDU 默认不带 VLAN 标记，PVST 无法在跨桥链路上正确识别该环。

**修复**：把二层延伸从汇聚层下移到接入层，改为单条 Trunk `acc-d1:eth6 ↔ acc-la:eth5`（VLAN 510），路径上不再有环。汇聚层 `agg-l1`/`agg-l2` 侧**不再配置 VLAN 510 子接口**，网关 `10.51.0.1` 仍只由 `agg-d1`/`agg-d2` 的 VRRP 虚路由 5 持有。

**验证**：`ap-d1 ↔ ap-la`（10.51.0.21）互通；VRRP VIP `10.51.0.1` 持有者数量为 1；`WIRELESS-01`～`WIRELESS-03` 通过。

### 5.15 梅陇网段被防火墙聚合路由吞掉形成转发环路

**现象**：`pc-ta1 → 10.91.0.11`（梅陇业务网段）不通，而梅陇侧反向访问园区却正常。

**根因**：出口防火墙的路由表为 `default via 10.90.1.254` 与 `10.0.0.0/8 via 10.0.100.253`（核心）。`10.91.0.0/16` 落在 `10.0.0.0/8` 内，园区去梅陇的流量被送回核心，核心再送回防火墙，形成环路。

**修复**：在 `fw1`/`fw2` 上补充明细路由 `10.91.0.0/16 via 10.90.1.254`（出口路由器 VRRP 网关），并放行 `iifname eth2 ip saddr @meilong_nets` 的转发。

**验证**：`r2 ip route get 10.91.0.11` 为 `via 10.91.1.2 dev eth3`；`WIRELESS-08`～`WIRELESS-11` 通过。

### 5.16 WIRELESS-04 用 ping 校验 DNS，与访问控制矩阵矛盾

**现象**：实验区 AP `ap-la` 无法 ping 通数据中心 DNS 服务器 `10.60.0.10`，用例失败。

**根因**：**这不是实现缺陷，而是断言方式与设计意图冲突**。设计方案 6.6 的访问控制矩阵把宿舍区列为隔离区域，仅放行「宿舍互访、DNS(53)、Internet、DMZ 发布服务」，`dorm_filter` 链中 `ip daddr @dc_nets counter drop` 会丢弃 ping；`ISO-04` 正是断言这一隔离行为。

**修复**：改为执行真实 DNS 解析（`nslookup www.campus.local 10.60.0.10`），并在 `tests/lib.sh` 中新增 `assert_dns_resolves`。

**验证**：`WIRELESS-04` 通过，且 `ISO-04`（宿舍 → 数据中心阻断）仍为 PASS，二者不再冲突。

### 5.17 WIRELESS-10 断言目的地取错

**现象**：`r2 ip route get 10.60.0.10` 的结果不含 `10.91.1.2`，用例失败。

**根因**：该查询命中的是 `r2` 的 `10.0.0.0/8 via 10.90.1.253` 回指路由（园区内网地址），与梅陇互联无关；而 `r2` 的梅陇静态路由 `10.91.0.0/16 via 10.91.1.2` 本身是正确生效的。

**修复**：把断言目的地改为梅陇侧地址 `10.91.0.11`，此时命中 `via 10.91.1.2 dev eth3`。

**验证**：`WIRELESS-10` 通过。

### 5.18 数据中心 DNS 依赖不可达上游

**现象**：从教学区 `pc-ta1` 查询 `www.campus.local`，dnsmasq 已给出 A 记录 `10.80.0.10`，但 busybox `nslookup` 仍返回非零并提示 "No answer"；从宿舍区查询则整体超时。

**根因**：dnsmasq 配置里只有占位上游 `server=223.5.5.5`，仿真环境没有真实互联网出口，转发出去的查询石沉大海。更关键的是 busybox `nslookup` 会同时发出 A 与 AAAA 两种查询，A 由 `host-record` 命中本地记录得以应答，AAAA 却被送往不可达上游，命令因此一直等到超时。

**修复**：

1. 为 dnsmasq 补上园区内 `host-record`（`srv-dc1`、`srv-dc2`、`dns.campus.local`、`srv-dmz`、`dmz.campus.local`、`www.campus.local`、`internet.campus.local`、`gw.campus.local`）；
2. 增加 `local=/campus.local/` 与 `local=/local/`，声明这些域由 dnsmasq 本地负责、**绝不转发**——缺了这一行，AAAA 查询仍会被送到上游；
3. 同步把 `WIRELESS-04` 的断言改为真实 DNS 解析。

**验证**：`pc-d1`、`ap-la`、`pc-ta1` 三处 `nslookup www.campus.local 10.60.0.10` 均返回 `rc=0` 且解析结果为 `10.80.0.10`。

### 5.19 `gen.py` 写出文件未指定编码，Windows 下 `facts.json` 成为非法 UTF-8

**现象**：终验轮次 `20261111T143222Z` 启动 `tests/run-all.sh` 立即退出，输出 `ENV: expected  containers, found 49` —— 期望值一栏为空。

**根因**：`tests/run-all.sh` 用 `python3 -c 'import json;print(json.load(open("configs/facts.json"))["nodes"]["total"])'` 读取节点总数。`gen.py` 的文件写出辅助函数 `w()` 原本只指定了 `newline=""` 而未指定 `encoding`，在 Windows 上按系统默认编码（GBK）落盘，`facts.json` 中的中文因此写成非法 UTF-8 字节。WSL 内的 Python 默认按 UTF-8 读取该文件，直接抛出 `UnicodeDecodeError`，`EXPECTED` 取值为空，触发"环境不可用"分支。

**修复**：在 `w()` 中显式指定 `encoding="utf-8"`，并保留 `newline=""` 以确保生成的 shell 脚本始终为 LF（否则在 WSL 下会因 CRLF 报 `set: Illegal option -`）。

**验证**：Windows 侧 `python gen.py` 重新生成后，WSL 侧 `python3 -c 'import json;...'` 正常输出 `49`，全量测试 85/85 通过。

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
| keepalived | `core1`/`agg-t1`/`agg-d1`/`fw1` | 进程在运行，VIP 已分配 |
| 主干限速 | `core1 tc qdisc show dev eth1` | `tbf rate 10Gbit` |
| 宿舍接入限速 | `acc-d1 tc qdisc show dev eth3` | `tbf rate 100Mbit` |
| 无线子网互通 | `ap-d1 ping 10.51.0.21` | 0% 丢包 |
| VLAN 510 网关唯一 | `agg-d1`/`agg-d2` 持有 `10.51.0.1` | 合计 1 个 |
| 梅陇回程路由 | `r2 ip route get 10.91.0.11` | `via 10.91.1.2 dev eth3` |
| 梅陇互访 | `pc-ta1 ping 10.91.0.11` / `pc-ml1 ping 10.60.0.10` | 双向 0% 丢包 |
| DNS 解析 | `pc-d1`/`ap-la`/`pc-ta1` 解析 `www.campus.local` | 均为 `10.80.0.10`，rc=0 |
| 最终全量回归 | `sh tests/run-all.sh` | 85/85 通过（run-id `20261111T145644Z`） |

最终全量回归已执行：**85/85 全部通过，0 失败，0 跳过**。首次运行中的 3 项失败均已定位并修复；测试抢跑问题也已通过收敛等待 + 拓扑预检消除。

**补充（2026-11-10）**：针对 5.11~5.13 的三项修复后，从干净部署重新执行全量回归，run-id `20261110T064550Z` 与 `20261110T065801Z` 连续两轮均为 65/65 通过。

**补充（2026-11-11）**：合并远程新增的区域地址规划与 ACL 后，用例数增至 65 条，run-id `20261111T122017Z` 为 65/65 通过。

**补充（2026-11-11，三缺口补齐）**：新增 `WIRELESS`（11 条）与 `RATE`（9 条）两个套件，用例总数增至 85 条。首轮 `20261111T133133Z` 为 83/85（WIRELESS-04、WIRELESS-10 失败）；修复 5.16 ~ 5.18 后，`20261111T135011Z`、`20261111T135749Z` 与干净重建部署的 `20261111T140838Z` 连续三轮均为 **85/85 通过**，原有 65 条用例无回归。

**补充（2026-11-11，跨平台编码修复）**：终验轮次 `20261111T143222Z` 与完整复现链轮次 `20261111T145644Z`（regen → rebuild → destroy+deploy → test）同样为 **85/85 通过**。后者同时修复了 `gen.py` 文件写出未指定 `encoding` 导致的跨平台缺陷，详见 5.19。

## 7. 复现命令

### 7.1 macOS / Linux

```sh
cd net_prac/campus-lab
sh build-images.sh
python3 gen.py
sh run-clab.sh deploy -t campus-lab.clab.yml
sh tests/run-all.sh
```

### 7.1 macOS / Linux

```sh
cd net_prac/campus-lab
sh build-images.sh
python3 gen.py
sh deploy-lab.sh deploy
sh tests/run-all.sh
```

### 7.2 Windows / WSL2

见 `README.md` 的「Windows + WSL2 部署」章节。关键点：容器必须与 clab 运行在**同一个 Linux 内核**内，因此使用 WSL 内自带的 Docker Engine，而不是 Docker Desktop 的 Linux VM。

```sh
cd /mnt/d/code/net_prac/campus-lab
bash build-images.sh
python3 gen.py
sh deploy-lab.sh deploy
bash tests/run-all.sh
```

> **必须全程保持同一个 WSL 终端窗口不关闭**：WSL2 实例在没有活跃前台进程时会被 Windows 回收，
> systemd 随之执行完整关机序列，dockerd 被重启。dockerd 虽然会恢复容器进程，但 Containerlab
> 注入的 veth 链路不会重新注入，二层广播域与 VRRP 全部失效。
> `deploy-lab.sh` 会记录部署时的 dockerd MainPID，`tests/preflight.sh` 会比对并给出准确提示。

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
sh run-clab.sh deploy  -t campus-lab.clab.yml        # 3. 部署 49 节点（约 1–2 分钟）

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

> 「奉贤校区校园网仿真。先统一两个称谓：任务书原文的**梅陇校区**即评委说的**徐汇校区**，统一叫**梅陇（即徐汇）校区**。跨校区链路**已经建模**：核心经 `r2` 的第三条上行、`10.91.1.0/30` 互联到梅陇侧对端 `meilong`，梅陇业务网段 `10.91.0.0/16` 双向可达，可现场演示。」

**② 拓扑图（30s，一句话带过 Q1/Q5/Q6/Q8）**

浏览器展示 `http://localhost:50080`：

> 「49 个容器、72 条链路，双核心 + 分区域双汇聚 + 出口双路由 + 双防火墙 + DMZ，外加梅陇校区互联。**6 大功能区**加出口 DMZ 安全区，**11 个 VLAN**，一栋楼一个子网，预算约 **687 万元**。数字都以 `configs/facts.json` 为单一事实源。」

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

> 「`facts.json` 是单一事实源，`report_check.py` 逐键比对报告数字，输出 `report check OK`。8 个套件 65 条用例，退出码 0/1/2 区分通过/失败/环境不可用。」

**⑦ 边界主动声明（1min，不要等被问 Q2/Q7/Q11）**

> 「三个边界主动交代：**跨校区**仿真只覆盖奉贤校内，梅陇侧由 R2 承载，设计文档有完整出口方案；**FTP** 本期未部署，DMZ 已具备承载能力，属预留项；**无线**仿真验证 VLAN、地址池、认证策略，射频覆盖需真实环境勘测。」

### 8.3 演示后清理

```sh
docker stop clab-graph && docker rm clab-graph
sh run-clab.sh destroy -t campus-lab.clab.yml --cleanup
```