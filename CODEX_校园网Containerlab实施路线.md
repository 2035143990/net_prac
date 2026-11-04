# 校园网工程 Containerlab 实施路线

## 1 结论

本项目采用 **Containerlab + VS Code Containerlab 扩展 + TopoViewer** 作为主仿真平台。

老师已确认只要完成任务即可自由选择软件，因此不再受限于 eNSP、Boson 或 Packet Tracer。Containerlab 的拓扑工程是可编辑的 `*.clab.yml` 文本文件，适合由 AI 生成、检查和持续维护，同时能够真正部署网络节点、执行配置、测试连通性、抓包和模拟故障。

注意：只在 TopoViewer 中绘制拓扑不算完成仿真。必须部署实验并保存运行、配置和测试证据。

## 2 软件组合

| 用途 | 推荐软件或组件 |
| --- | --- |
| 主仿真平台 | Containerlab |
| 图形化编辑和演示 | VS Code Containerlab 扩展中的 TopoViewer |
| 动态路由和网关冗余 | FRRouting |
| 二层 VLAN、Trunk 和交换 | Open vSwitch |
| PC、服务器和测试终端 | Linux 容器 |
| 防火墙、NAT 和 DMZ | Linux nftables 或 VyOS |
| 抓包 | Wireshark 或 Edgeshark |
| 报告拓扑图 | TopoViewer 导出的 SVG 或 Draw.io 文件 |

如能合法取得华为 VRP 虚拟镜像，可以把部分核心和汇聚设备替换为 Containerlab 的 `huawei_vrp` 节点。但第一版不建议依赖大量 VRP 虚拟机，因为其资源占用和启动时间明显高于普通容器。

## 3 Containerlab 与普通绘图的区别

| 操作 | 是否属于实际仿真 |
| --- | --- |
| 在 TopoViewer 中摆放节点和连线 | 否，仅为拓扑绘图 |
| 编写 `campus.clab.yml` 但不部署 | 否，仅为工程定义 |
| Deploy 并成功启动网络节点 | 是 |
| 进入节点配置 VLAN、OSPF、VRRP、DHCP 和安全策略 | 是 |
| 执行 Ping、Traceroute、主备切换和抓包 | 是，且应作为验收证据 |

## 4 AI 生成可编辑工程的方法

AI 不生成不可解释的二进制工程，而是维护以下可审查文件：

- `campus.clab.yml`：节点、接口、镜像和链路；
- `campus.annotations.json`：TopoViewer 布局和标注；
- `requirements/*.yaml`：楼宇、VLAN、地址和需求；
- `configs/`：每台节点的启动配置；
- `tests/`：连通性、安全和故障切换测试；
- `evidence/`：截图、抓包和测试结果。

生成过程如下：

1. 将课程任务书转成结构化需求清单；
2. 生成楼宇、设备、接口、VLAN 和 IP 地址矩阵；
3. 检查重复地址、冲突 VLAN、缺失接口和不完整路由；
4. 生成 `*.clab.yml` 和各节点启动配置；
5. 在 TopoViewer 中检查和调整布局；
6. Deploy 实验；
7. 执行自动测试并保存证据；
8. Destroy 后重新 Deploy，验证工程可复现。

## 5 建议的工程目录

```text
campus-network/
├─ campus.clab.yml
├─ campus.annotations.json
├─ README.md
├─ requirements/
│  ├─ buildings.yaml
│  ├─ vlans.yaml
│  └─ address-plan.yaml
├─ configs/
│  ├─ core1/
│  ├─ core2/
│  ├─ aggregation/
│  ├─ firewall/
│  └─ services/
├─ tests/
│  ├─ connectivity.sh
│  ├─ routing.sh
│  ├─ failover.sh
│  └─ security.sh
└─ evidence/
   ├─ screenshots/
   ├─ pcaps/
   └─ test-results/
```

## 6 必须实现的校园网内容

1. 信息大楼网络中心部署双核心；
2. 教学区、宿舍区和实验区分别设置区域汇聚；
3. 图书馆、信息楼计算机实验中心和数据中心独立接入核心；
4. 各教学楼、宿舍楼和实验楼使用独立子网；
5. 拓扑和文档明确标注 10Gb、1Gb 和 100Mb 链路；
6. 使用 OSPF 或等价动态路由实现全网路由；
7. 配置 VLAN、Trunk、三层网关和 DHCP；
8. 配置 VRRP 或等价机制实现核心网关冗余；
9. 配置 Trust、Untrust 和 DMZ 三个安全区域；
10. 配置内网访问外网的 NAT；
11. 限制外网只能访问 DMZ 中指定的服务；
12. 完成主核心或主链路故障后的自动恢复测试；
13. 保存 Ping、Traceroute、路由表、VRRP 状态和抓包证据。

## 7 建议的综合实验

### 7.1 VLAN 与三层交换

配置每栋楼的 VLAN、接入口、Trunk、三层网关和区域汇聚。测试同 VLAN、跨 VLAN 和跨区域通信，并检查 VLAN 表、MAC 表、ARP 表和路由表。

### 7.2 OSPF 路由

核心与汇聚之间运行 OSPF。验证邻居关系、路由学习和链路断开后的重新收敛。

### 7.3 VRRP 核心冗余

配置双核心虚拟网关。持续 Ping 时停止主核心或主接口，记录备用核心接管及业务恢复过程。

### 7.4 DHCP

为不同区域配置独立地址池或 DHCP Relay，验证终端获得的地址、掩码、网关和 DNS 均符合地址规划。

### 7.5 防火墙、NAT 与 DMZ

验证以下策略：

- 内网可以访问 Internet 模拟端；
- 外网只能访问 DMZ 开放服务；
- 外网不能直接访问校内终端；
- 宿舍区不能访问受保护的管理网络；
- 安全策略和 NAT 存在有效命中记录。

### 7.6 故障与抓包

模拟核心故障、上联中断、丢包和延迟，记录恢复情况；使用 Wireshark 或 Edgeshark 抓取 ARP、ICMP、OSPF、VRRP 和应用流量。

## 8 无线部分的处理

Containerlab 可以验证无线业务的逻辑网络，但不能模拟真实射频覆盖、信道、手机关联和漫游。

工程中应完成：

- 宿舍区和实验区无线业务 VLAN；
- 其他楼宇无线业务 VLAN；
- 无线地址池；
- 无线用户访问策略；
- 每栋大楼每层至少一个 AP 的数量规划；
- SSID、地址、认证和安全策略设计。

报告应明确区分“无线逻辑网络验证”和“真实无线射频验证”，不得把逻辑连通测试描述成已经验证了实际信号覆盖。

## 9 完整设计图与可运行拓扑

建议同时保留两种视图：

1. **完整设计图**：展示任务书要求的全部楼宇、楼层、AP、带宽和链路；
2. **可运行验证拓扑**：每个区域选取代表性楼宇和终端，实际验证 VLAN、路由、冗余、安全和 DHCP。

重复楼宇可以共用同一配置模板，但必须在完整设计图、地址表和设备数量表中完整列出。这样既覆盖任务书要求，也不会为了视觉上的节点数量启动大量没有额外测试价值的容器。

## 10 验收证据清单

最终至少保存以下证据：

1. TopoViewer 完整拓扑；
2. `containerlab inspect` 的运行状态；
3. 核心、汇聚和防火墙配置；
4. 教学区、宿舍区、实验区和数据中心之间的 Ping；
5. OSPF 邻居和路由表；
6. VRRP Master/Backup 状态；
7. 主核心故障切换过程；
8. NAT 转换或连接状态；
9. 外网到 DMZ 成功、外网到内网失败的对照测试；
10. Wireshark 或 Edgeshark 抓包；
11. Destroy 后重新 Deploy 成功；
12. 可编辑的 `*.clab.yml`、配置文件和测试脚本。

## 11 实施顺序

1. 确定建筑数量、楼层和信息点假设；
2. 完成 VLAN 与 IP 地址规划；
3. 绘制完整逻辑和物理拓扑；
4. 建立设备与接口矩阵；
5. 生成 Containerlab 工程和启动配置；
6. 分别验证 VLAN、路由、DHCP、VRRP 和防火墙；
7. 进行端到端和故障测试；
8. 保存截图、抓包和自动测试结果；
9. 冻结仿真工程；
10. 最后编写报告和准备答辩。

## 12 参考资料

- Containerlab VS Code Extension：<https://containerlab.dev/manual/gui/vsc-extension/>
- Containerlab GUI 与 TopoViewer：<https://containerlab.dev/manual/gui/>
- Containerlab 拓扑定义：<https://containerlab.dev/manual/topo-def-file/>
- FRRouting 节点：<https://containerlab.dev/manual/kinds/frr/>
- Huawei VRP 节点：<https://containerlab.dev/manual/kinds/huawei_vrp/>
- 链路故障注入：<https://containerlab.dev/manual/impairments/>

