# C 组 · 802.1X / Portal 认证与 RADIUS 动态 VLAN 设计

> 本文件由 `tools/c_8021x_plan.py --md` 生成，请勿手工编辑。
> 重新生成：`python3 tools/c_8021x_plan.py --md > docs/c-8021x-plan.md`

## 设计规则

- **认证前**：接入端口默认进入隔离 VLAN 999（`10.71.0.0/24`），只能访问 DHCP、DNS 与认证服务器；
- **认证后**：由 RADIUS 下发业务 VLAN（动态 VLAN），无线按 SSID 进入 VLAN 500/510，有线进入本楼栋业务 VLAN；
- **认证方式**：教职工有线/无线走 802.1X；学生无线走 802.1X（支持漫游）；访客走 Portal 临时账号并限时限速；
- **RADIUS**：主备 2 台（`radius1`/`radius2`），部署在数据中心；
- 认证前后的 VLAN 变化即实验七的验收证据。

## 认证规则表

| 场景 | SSID | 认证方式 | 认证前 VLAN | 认证前网段 | 认证后 VLAN | 认证后网段 | RADIUS 下发属性 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 有线-教职工 | — | 802.1X（PEAP-MSCHAPv2，域账号） | 999 | 10.71.0.0/24 | 对应楼栋业务 VLAN | 对应楼栋 /24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Filter-Id=teacher |
| 有线-学生 | — | 802.1X（EAP-TLS 或 PEAP），失败后回落 Portal | 999 | 10.71.0.0/24 | 对应楼栋业务 VLAN | 对应楼栋 /24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Filter-Id=student |
| 无线-教职工 | ECUST-EDU | 802.1X（ECUST-EDU） | 999 | 10.71.0.0/24 | 500 | 10.50.0.0/24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Egress-VLAN-ID=500; Filter-Id=teacher |
| 无线-学生 | ECUST-STU | 802.1X（ECUST-STU，支持漫游） | 999 | 10.71.0.0/24 | 510 | 10.51.0.0/24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Egress-VLAN-ID=510; Filter-Id=student; Session-Timeout=86400 |
| 无线-访客 | ECUST-GUEST | Portal（ECUST-GUEST，临时账号，限时限速） | 999 | 10.71.0.0/24 | 999（限时） | 10.71.0.0/24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Egress-VLAN-ID=999; Session-Timeout=28800; Filter-Id=guest; Mikrotik-Rate-Limit=10M/10M |
| 有线-访客 | — | Portal（临时账号） | 999 | 10.71.0.0/24 | 999（限时） | 10.71.0.0/24 | Tunnel-Type=VLAN; Tunnel-Medium-Type=IEEE-802; Egress-VLAN-Name; Egress-VLAN-ID=999; Session-Timeout=7200; Filter-Id=guest |

## RADIUS 返回属性

```
[有线-教职工] 802.1X（PEAP-MSCHAPv2，域账号）
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Filter-Id=teacher
[有线-学生] 802.1X（EAP-TLS 或 PEAP），失败后回落 Portal
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Filter-Id=student
[无线-教职工] 802.1X（ECUST-EDU）
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Egress-VLAN-ID=500
    Filter-Id=teacher
[无线-学生] 802.1X（ECUST-STU，支持漫游）
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Egress-VLAN-ID=510
    Filter-Id=student
    Session-Timeout=86400
[无线-访客] Portal（ECUST-GUEST，临时账号，限时限速）
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Egress-VLAN-ID=999
    Session-Timeout=28800
    Filter-Id=guest
    Mikrotik-Rate-Limit=10M/10M
[有线-访客] Portal（临时账号）
    Tunnel-Type=VLAN
    Tunnel-Medium-Type=IEEE-802
    Egress-VLAN-Name
    Egress-VLAN-ID=999
    Session-Timeout=7200
    Filter-Id=guest
```

## 隔离 VLAN 999

| 项目 | 值 |
| --- | --- |
| VLAN | 999（设计方案 5.2 定义，属保留/隔离用途） |
| 网段 | `10.71.0.0/24`（地址规划表中未被占用） |
| 网关 | `10.71.0.1` |
| 允许访问 | DHCP `10.60.0.10`、DNS、RADIUS `10.60.0.21/22` |
| 禁止访问 | 全部业务 VLAN、管理网、Internet |

## 仿真现状与差距

仿真差距：
  - 仿真未建模 802.1X / RADIUS：gen.py 中没有 dot1x、radius 或 ACL 认证动作
  - VLAN 999 隔离网段未在 campus-lab 中生成，实验七需要新增隔离 VLAN 与其 ACL
  - 实验七为加分项，风险表已标注“时间紧时后补”

检查通过
