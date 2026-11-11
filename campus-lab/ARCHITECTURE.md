# 校园网仿真项目架构说明

本文解释 `campus-lab/` 的**代码组织方式**与**网络拓扑分层**。想直接看拓扑，用 TopoViewer（见第 5 节）。

---

## 1. 一句话概括

`gen.py` 是**单一事实源**：它把"设计"（谁连谁、用什么 IP、跑什么协议）编译成两类产物——

1. **运行时产物**：Containerlab 拓扑 YAML + 每个节点挂载进容器的配置文件
2. **可读产物**：draw.io 拓扑图、`facts.json` 事实快照

所有手工修改都应改 `gen.py` 后重新 `python3 gen.py`，**不要直接改生成物**。

---

## 2. 目录职责

```text
campus-lab/
├─ gen.py              ← 架构核心：设计 → 产物的编译器（约 1100 行）
├─ campus-lab.clab.yml ← 【生成】Containerlab 拓扑（44 节点 / 66 链路）
├─ configs/            ← 【生成】各节点配置，由 gen.py 写出
│  ├─ frr/<节点>/      ←   frr.conf / prestart.sh / keepalived.conf / acl.nft
│  ├─ access/<节点>/   ←   二层交换机 setup.sh（VLAN、bridge、trunk/access）
│  ├─ fw/              ←   防火墙 nftables 规则 + 双机 keepalived
│  ├─ hosts/<节点>/    ←   终端/服务器地址、DHCP 客户端、dnsmasq
│  └─ facts.json       ←   事实快照（测试与报告读取）
├─ images/             ← 【手写】四个镜像的 Dockerfile + ENTRYPOINT
│  ├─ frr/             ←   FRRouting + keepalived + nftables + dnsmasq
│  ├─ l2/              ←   Linux bridge 模拟二层交换机
│  ├─ fw/              ←   nftables + conntrack
│  └─ host/            ←   终端/服务器
├─ tests/              ← 【手写】65 条用例 + 预检
├─ build-images.sh     ← 【手写】构建镜像
├─ deploy-lab.sh       ← 【手写】统一部署入口
└─ topoviewer.sh       ← 【手写】启动 TopoViewer
```

**规则**：`gen.py`、`images/`、`tests/`、`*.sh` 是手写的；`campus-lab.clab.yml`、`configs/`、`facts.json` 是生成的（改了就白改）。

---

## 3. 镜像与容器的对应关系

每个容器就是一个 Linux 网络设备。镜像决定它"会什么协议"：

| 镜像 | 节点数 | 承载 | 关键软件 |
| --- | --- | --- | --- |
| `campus-frr` | 14 | 双核心、10 台汇聚、2 台出口路由 | FRRouting、keepalived、nftables、dnsmasq(Relay) |
| `campus-l2` | 11 | 接入交换机 + 4 台传输二层交换机 | iproute2（bridge + vlan filtering） |
| `campus-fw` | 2 | 边界防火墙 | nftables、conntrack-tools、keepalived |
| `campus-host` | 17 | 终端、服务器、Internet 模拟 | iproute2、dnsmasq（DHCP/DNS/HTTP） |

合计 **44 个容器**。

---

## 4. 网络拓扑分层

拓扑是**严格分层**的，`graph-level` 标签决定各层在图上的纵坐标。

```text
 Level 9   终端 / 服务器        pc-*  ap-*  srv-*  mgmt-pc  pc-dyn*
 Level 8   接入交换机          acc-ta acc-tb acc-d1 acc-la acc-lib acc-life dc-sw
 Level 7   区域汇聚            agg-t1/2  agg-d1/2  agg-l1/2  agg-lib1/2  agg-life1/2
 Level 6   双核心              core1  core2                    ← OSPF Area 0 + bond0 聚合
 Level 5   Trust / DMZ 二层    trust-sw  dmz-sw
 Level 4   边界防火墙          fw1  fw2                        ← VRRP 热备
 Level 3   Untrust 二层        untrust-sw
 Level 2   出口路由            r1  r2                         ← 静态路由 + VRRP
 Level 1   Internet 二层       inet-sw
 Level 0   Internet 模拟       internet
```

### 4.1 核心层（Level 6）

- `core1` / `core2`，FRR 跑 OSPF Area 0，Loopback `10.255.0.1/32` / `.2/32`
- 两台核心之间**两条链路**（`eth11`、`eth14`）在容器内做成 `bond0`（802.3ad LACP），对下表现为**一条逻辑链路**
- 因此 `core1` 的 OSPF Full 邻居数是 **11**（10 台汇聚 + 1 个 peer core），不是 12
- VRRP VIP：`10.0.100.253`（Trust）、VLAN 70/90 网关
- 对 Trust（`eth12`）和数据中心（`eth13`）做**双上联**（每台各连一个）

### 4.2 汇聚层（Level 7）

5 个业务区 × 2 台 = 10 台，每台承担三件事：

1. **VRRP 网关**：`agg-t1/2` → `10.10.0.1`，`agg-d1/2` → `10.32.0.1`，等
2. **DHCP Relay**：`dhcp-relay.conf` 把终端的 DHCP Discover 转发到数据中心的 `srv-dc1`
3. **区域 ACL**：`acl.nft` 实现教学区/宿舍区/实验区的访问控制矩阵

双汇聚与双核心之间是**交叉上联**（`core1→agg-t1`、`core2→agg-t2`、`core1→agg-t2`、`core2→agg-t1`），保证任一核心或汇聚故障都不黑洞。

### 4.3 接入层（Level 8）

Linux bridge + VLAN filtering：每个业务 VLAN 一个 `br0`，Trunk 口承载多个 VLAN，Access 口接终端。

### 4.4 边界与出口（Level 3~0）

```text
core ──trust-sw── fw1/fw2 ──untrust-sw── r1/r2 ──inet-sw── internet
                └──── dmz-sw ──── srv-dmz
```

- `fw1/fw2`：nftables 三区策略（Trust/Untrust/DMZ），VRRP `10.0.100.254` 热备
- 源 NAT：Trust → Internet 在 `fw` 上做 SNAT
- 目的 NAT：Untrust 访问 `198.51.100.80` 的 TCP 80/443 被 DNAT 到 `srv-dmz`
- `r1/r2`：静态路由 + VRRP，模拟运营商出口

---

## 5. 用 TopoViewer 查看拓扑

Containerlab 内置了 **TopoViewer**（`clab graph --srv`），能交互式查看运行中的拓扑。

### 5.1 启动

在**保持打开的 WSL 终端**里执行：

```bash
cd /mnt/d/code/net_prac/campus-lab
sh topoviewer.sh
```

输出会列出可访问的地址：

```text
==> 浏览器访问地址：
    http://localhost:50080          (Windows 侧)
    http://172.19.130.20:50080      (同网段其他机器)
```

然后在 Windows 浏览器打开 <http://localhost:50080/>。

### 5.2 界面用法

| 操作 | 方式 |
| --- | --- |
| 平移 | 拖拽画布空白处 |
| 缩放 | 滚轮，或右侧工具栏 "Zoom by selection" |
| 适配全图 | 右侧工具栏 "Fit stage" |
| 全屏 | 右侧工具栏 "Enter full screen mode" |
| 切换横/纵布局 | 左上角 "Horizontal Layout" / "Vertical Layout" |
| 点节点看详情 | 点击节点，显示接口、IP、标签 |
| 显示为圆点 | 右上 "Display icons as dots" |

### 5.3 其它导出格式

```bash
# draw.io 图形（可再编辑）
~/bin/clab graph --drawio -t campus-lab.clab.yml

# mermaid 流程图（可贴进 Markdown）
~/bin/clab graph --mermaid -t campus-lab.clab.yml

# 只看部分节点
~/bin/clab graph --srv 0.0.0.0:50080 --node-filter core1,core2 -t campus-lab.clab.yml
```

### 5.4 注意事项

- TopoViewer 读的是**运行中**的容器状态，所以**必须先部署**（`sh deploy-lab.sh deploy`）才有内容。
- `topoviewer.sh` 会顺带启动一个 keeper 进程。因为 WSL2 实例在没有活跃进程时会被 Windows 回收，届时 veth 链路丢失，拓扑图会显示为断链。
- 默认端口 50080，可改：`sh topoviewer.sh 0.0.0.0:8080`。

---

## 6. 一次完整流程

```bash
# 全部在同一个 WSL 会话里完成，窗口不要关
cd /mnt/d/code/net_prac/campus-lab

bash build-images.sh      # 构建 4 个镜像（首次或改 Dockerfile 后）
python3 gen.py            # 生成拓扑与全部节点配置
sh deploy-lab.sh deploy   # 销毁旧环境 → 部署 → 等 120s 收敛 → 预检
bash tests/run-all.sh     # 65 条用例
sh topoviewer.sh          # 另开浏览器看拓扑
```

### 数据流

```text
                    gen.py  (设计)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
campus-lab.clab.yml  configs/     facts.json
   (拓扑定义)        (节点配置)    (事实快照)
        │              │              │
        ▼              ▼              ▼
  clab deploy      bind mount     测试/报告读取
        │
        ▼
   44 个容器 ──── 66 条 veth ──── 运行中的校园网
        │
        ▼
   clab graph --srv  →  TopoViewer（浏览器）
```

### 关键设计点

**配置是自愈的**：`images/*/start.sh` 作为 ENTRYPOINT，容器每次启动都会重新执行 `/setup.sh`，重建 bridge、VLAN、地址、ACL、VRRP。这样容器重启后网络不会"失忆"。

**但 veth 不会自愈**：Containerlab 注入的 veth 链路在 dockerd 重启后不会回来（Containerlab 不会自动重建）。所以 WSL/宿主机重启后必须**重新 `deploy`**，`tests/preflight.sh` 会检测这种状态并明确提示。

**预检先行**：`tests/run-all.sh` 先跑 `tests/preflight.sh`，检查 11 台二层交换机的 bridge、core1 的 11 个 OSPF Full 邻居、4 组 VRRP VIP 的唯一持有者，以及 dockerd 是否在部署后被重启过。不健康就直接以退出码 2 终止，避免 65 条用例产生一堆无意义的失败。
