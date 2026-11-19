# 中小型企业园区网设备配置

> 本文件按截图中的设备名给出每台设备的配置。
> 所有命令基于常见华为 VRP 语法，eNSP V1.3.00.100 可直接粘贴到设备 CLI。
> 配置前请先确认拓扑与连接表一致，并保存工程。

## 设备映射

| 任务书 | 截图 | 型号 | 角色 |
|---|---|---|---|
| R1 | AR1 | AR1220 | 总部出口、DHCP 服务器 |
| R2 | AR2 | AR1220 | 分支出口、分支 DHCP 服务器 |
| CSW1 | LSW3 | S5700 | MSTI1 根、VLAN10/30 主网关 |
| CSW2 | LSW4 | S5700 | MSTI2 根、VLAN20/50 主网关 |
| ASW1 | LSW1 | S5700 | 行政、研发接入 |
| ASW2 | LSW2 | S5700 | 财务、服务器接入 |
| BSW1 | LSW5 | S5700 | 分支接入 |

---

## 配置注意事项

以下 6 条直接决定实验能否跑通，请先读完再粘贴配置。

1. **LSW5 的 `GE0/0/24` 必须是 access VLAN 40。**
   AR2 的 `GE0/0/1` 是普通三层物理接口，不是 dot1q 子接口，所以这里不能配 trunk。

2. **LSW1、LSW2、LSW3、LSW4 必须配置完全相同的 MST 域。**
   区域名、修订级别、VLAN 实例映射都要一致，并执行 `active region-configuration`。
   接入交换机不配根桥是对的，但不能不配域，否则会形成不同 MST 区域。

3. **AR1 的 `GE0/0/0` 和 `GE0/0/1` 都必须配置 `dhcp select global`。**
   AR1 是 DHCP 服务器，核心把请求中继过来后，AR1 根据中继填入的 `giaddr` 选择地址池，
   不是根据入接口 IP 选池。两个接口都要开全局 DHCP。

4. **不要在核心面向客户端的 Vlanif 上配置 `dhcp select global`。**
   核心侧只配 `dhcp select relay` 和 `dhcp relay server-ip`。

5. **ACL 3000 的地址后面是通配符掩码 `0.0.0.255`，不是 `255.255.255.0`。**
   完整关键字是 `destination`。两台核心都要在 `Vlanif 30` 的 `outbound` 方向应用。

6. **ACL 是无状态的。**
   当前规则只拦截"研发/分支主动访问财务"的去程报文。
   财务主动访问研发时，研发返回财务的报文源是研发、目的是财务，也会被 rule 10 拒绝。
   本实验只要求验证"研发/分支不能访问财务"，所以按任务书执行即可；
   不要把这个 ACL 理解成防火墙。

---

## 一、粘贴顺序

请按以下顺序配置，每完成一段保存一次：

```text
1. LSW1、LSW2、LSW3、LSW4 的 MST 域与 VLAN
2. LSW1、LSW2、LSW3、LSW4 的 Access、Trunk
3. LSW5 的 VLAN 与 Access
4. LSW3、LSW4 的 VLANIF、VRRP
5. AR1、AR2 的接口地址、OSPF
6. LSW3、LSW4 的 OSPF 与 silent-interface
7. AR1、AR2 的 DHCP
8. LSW3、LSW4 的 DHCP Relay
9. LSW3、LSW4 的 ACL
10. PC、服务器地址
11. 保存与验证
```

---

## 二、LSW1：行政、研发接入

```text
system-view
sysname LSW1
vlan batch 10 20 30 50

stp enable
stp mode mstp
stp region-configuration
 region-name COMPANY
 revision-level 1
 instance 1 vlan 10 30
 instance 2 vlan 20 50
 active region-configuration
#
interface GigabitEthernet 0/0/1
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/2
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/10
 port link-type access
 port default vlan 10
 stp edged-port enable
#
interface GigabitEthernet 0/0/11
 port link-type access
 port default vlan 20
 stp edged-port enable
#
```

---

## 三、LSW2：财务、服务器接入

```text
system-view
sysname LSW2
vlan batch 10 20 30 50

stp enable
stp mode mstp
stp region-configuration
 region-name COMPANY
 revision-level 1
 instance 1 vlan 10 30
 instance 2 vlan 20 50
 active region-configuration
#
interface GigabitEthernet 0/0/1
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/2
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/10
 port link-type access
 port default vlan 30
 stp edged-port enable
#
interface GigabitEthernet 0/0/11
 port link-type access
 port default vlan 50
 stp edged-port enable
#
```

---

## 四、LSW5：分支接入

```text
system-view
sysname LSW5
vlan batch 40

interface GigabitEthernet 0/0/1
 port link-type access
 port default vlan 40
 stp edged-port enable
#
interface GigabitEthernet 0/0/24
 port link-type access
 port default vlan 40
#
```

> 说明：AR2 的 `GE0/0/1` 是普通三层物理接口，不是 dot1q 子接口，
> 所以 LSW5 的 `GE0/0/24` 必须是 **access VLAN 40**，不能配 trunk。

---

## 五、LSW3：核心 1

```text
system-view
sysname LSW3
vlan batch 10 20 30 50 100 102

stp enable
stp mode mstp
stp region-configuration
 region-name COMPANY
 revision-level 1
 instance 1 vlan 10 30
 instance 2 vlan 20 50
 active region-configuration
#
stp instance 1 root primary
stp instance 2 root secondary
#
interface Vlanif 10
 ip address 192.168.10.2 255.255.255.0
 vrrp vrid 10 virtual-ip 192.168.10.1
 vrrp vrid 10 priority 120
#
interface Vlanif 20
 ip address 192.168.20.2 255.255.255.0
 vrrp vrid 20 virtual-ip 192.168.20.1
#
interface Vlanif 30
 ip address 192.168.30.2 255.255.255.0
 vrrp vrid 30 virtual-ip 192.168.30.1
 vrrp vrid 30 priority 120
#
interface Vlanif 50
 ip address 192.168.50.2 255.255.255.0
 vrrp vrid 50 virtual-ip 192.168.50.1
#
interface Vlanif 100
 ip address 10.0.1.2 255.255.255.252
#
interface Vlanif 102
 ip address 10.0.3.1 255.255.255.252
#
interface GigabitEthernet 0/0/1
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/2
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/3
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50 102
#
interface GigabitEthernet 0/0/24
 port link-type access
 port default vlan 100
#
dhcp enable
#
interface Vlanif 10
 dhcp select relay
 dhcp relay server-ip 10.0.1.1
#
interface Vlanif 20
 dhcp select relay
 dhcp relay server-ip 10.0.1.1
#
interface Vlanif 30
 dhcp select relay
 dhcp relay server-ip 10.0.1.1
#
acl 3000
 rule 5 permit ip source 192.168.10.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 10 deny ip source 192.168.20.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 15 deny ip source 192.168.40.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 20 permit ip
#
interface Vlanif 30
 traffic-filter outbound acl 3000
#
ospf 1 router-id 11.11.11.11
 silent-interface Vlanif 10
 silent-interface Vlanif 20
 silent-interface Vlanif 30
 silent-interface Vlanif 50
 area 0.0.0.0
  network 192.168.10.0 0.0.0.255
  network 192.168.20.0 0.0.0.255
  network 192.168.30.0 0.0.0.255
  network 192.168.50.0 0.0.0.255
  network 10.0.1.0 0.0.0.3
  network 10.0.3.0 0.0.0.3
#
```

---

## 六、LSW4：核心 2

```text
system-view
sysname LSW4
vlan batch 10 20 30 50 101 102

stp enable
stp mode mstp
stp region-configuration
 region-name COMPANY
 revision-level 1
 instance 1 vlan 10 30
 instance 2 vlan 20 50
 active region-configuration
#
stp instance 1 root secondary
stp instance 2 root primary
#
interface Vlanif 10
 ip address 192.168.10.3 255.255.255.0
 vrrp vrid 10 virtual-ip 192.168.10.1
#
interface Vlanif 20
 ip address 192.168.20.3 255.255.255.0
 vrrp vrid 20 virtual-ip 192.168.20.1
 vrrp vrid 20 priority 120
#
interface Vlanif 30
 ip address 192.168.30.3 255.255.255.0
 vrrp vrid 30 virtual-ip 192.168.30.1
#
interface Vlanif 50
 ip address 192.168.50.3 255.255.255.0
 vrrp vrid 50 virtual-ip 192.168.50.1
 vrrp vrid 50 priority 120
#
interface Vlanif 101
 ip address 10.0.2.2 255.255.255.252
#
interface Vlanif 102
 ip address 10.0.3.2 255.255.255.252
#
interface GigabitEthernet 0/0/1
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/2
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50
#
interface GigabitEthernet 0/0/3
 port link-type trunk
 port trunk allow-pass vlan 10 20 30 50 102
#
interface GigabitEthernet 0/0/24
 port link-type access
 port default vlan 101
#
dhcp enable
#
interface Vlanif 10
 dhcp select relay
 dhcp relay server-ip 10.0.2.1
#
interface Vlanif 20
 dhcp select relay
 dhcp relay server-ip 10.0.2.1
#
interface Vlanif 30
 dhcp select relay
 dhcp relay server-ip 10.0.2.1
#
acl 3000
 rule 5 permit ip source 192.168.10.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 10 deny ip source 192.168.20.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 15 deny ip source 192.168.40.0 0.0.0.255 destination 192.168.30.0 0.0.0.255
 rule 20 permit ip
#
interface Vlanif 30
 traffic-filter outbound acl 3000
#
ospf 1 router-id 12.12.12.12
 silent-interface Vlanif 10
 silent-interface Vlanif 20
 silent-interface Vlanif 30
 silent-interface Vlanif 50
 area 0.0.0.0
  network 192.168.10.0 0.0.0.255
  network 192.168.20.0 0.0.0.255
  network 192.168.30.0 0.0.0.255
  network 192.168.50.0 0.0.0.255
  network 10.0.2.0 0.0.0.3
  network 10.0.3.0 0.0.0.3
#
```

---

## 七、AR1：总部出口与 DHCP 服务器

```text
system-view
sysname AR1
vlan batch 100 101
#
dhcp enable
#
ip pool vlan10
 network 192.168.10.0 mask 255.255.255.0
 gateway-list 192.168.10.1
 excluded-ip-address 192.168.10.1 192.168.10.20
 dns-list 192.168.10.1
#
ip pool vlan20
 network 192.168.20.0 mask 255.255.255.0
 gateway-list 192.168.20.1
 excluded-ip-address 192.168.20.1 192.168.20.20
 dns-list 192.168.20.1
#
ip pool vlan30
 network 192.168.30.0 mask 255.255.255.0
 gateway-list 192.168.30.1
 excluded-ip-address 192.168.30.1 192.168.30.20
 dns-list 192.168.30.1
#
interface GigabitEthernet 0/0/0
 ip address 10.0.1.1 255.255.255.252
 dhcp select global
#
interface GigabitEthernet 0/0/1
 ip address 10.0.2.1 255.255.255.252
 dhcp select global
#
interface GigabitEthernet 0/0/2
 ip address 10.0.12.1 255.255.255.252
#
ospf 1 router-id 1.1.1.1
 area 0.0.0.0
  network 10.0.1.0 0.0.0.3
  network 10.0.2.0 0.0.0.3
  network 10.0.12.0 0.0.0.3
#
```

> 说明：AR1 是 DHCP 服务器。核心把请求中继到 AR1 后，
> AR1 **根据中继填入的 giaddr 选择对应地址池**，不是根据入接口 IP 选池。
> 因此 `GE0/0/0` 和 `GE0/0/1` 都必须配置 `dhcp select global`，
> 且 AR1 到四个业务网段的 OSPF 回程路由必须存在。
> 不要在核心面向客户端的 Vlanif 上配置 `dhcp select global`。

---

## 八、AR2：分支出口与分支 DHCP 服务器

```text
system-view
sysname AR2
vlan batch 40
#
dhcp enable
#
ip pool vlan40
 network 192.168.40.0 mask 255.255.255.0
 gateway-list 192.168.40.1
 excluded-ip-address 192.168.40.1 192.168.40.20
 dns-list 192.168.40.1
#
interface GigabitEthernet 0/0/0
 ip address 10.0.12.2 255.255.255.252
#
interface GigabitEthernet 0/0/1
 ip address 192.168.40.1 255.255.255.0
 dhcp select global
#
ospf 1 router-id 2.2.2.2
 silent-interface GigabitEthernet 0/0/1
 area 0.0.0.0
  network 10.0.12.0 0.0.0.3
  network 192.168.40.0 0.0.0.255
#
```

---

## 九、终端地址

| 设备 | 地址 | IPv4 掩码 | 网关 | 获取方式 |
|---|---|---|---|---|
| PC1 行政 | 192.168.10.x | 255.255.255.0 | 192.168.10.1 | DHCP |
| PC2 研发 | 192.168.20.x | 255.255.255.0 | 192.168.20.1 | DHCP |
| PC3 财务 | 192.168.30.x | 255.255.255.0 | 192.168.30.1 | DHCP |
| Server1 服务器 | 192.168.50.10 | 255.255.255.0 | 192.168.50.1 | 静态 |
| PC4 分支 | 192.168.40.x | 255.255.255.0 | 192.168.40.1 | DHCP |

eNSP 终端填写时，请确认 IPv4 掩码为 `255.255.255.0`，不要只写 `/24` 或 `24`。

---

## 十、保存与检查命令

每台设备配置完成后执行：

```text
return
save
```

检查命令：

```text
display version
display stp region-configuration
display stp brief
display stp instance 1
display stp instance 2
display vrrp brief
display ip interface brief
display ospf peer brief
display ip routing-table protocol ospf
display ip pool
display dhcp relay statistics
display acl 3000
display traffic-filter applied-record
```

关键判断标准：

- LSW1、LSW2、LSW3、LSW4 的 MST 区域名、修订级别和 VLAN 实例映射完全一致。
- LSW3 的 MSTI1 为根，LSW4 的 MSTI2 为根。
- VLAN10/30 的 VRRP Master 是 LSW3，VLAN20/50 的 VRRP Master 是 LSW4。
- 四个业务虚拟网关 `.1` 可以 ping 通。
- OSPF 邻居数量符合：AR1 有 CSW1、CSW2、R2；CSW1、CSW2 互为邻居；AR2 只有 R1。
- 路由表包含四个总部业务网段和 `192.168.40.0/24`。
- PC1、PC2、PC3、PC4 获得对应网段地址。

---

## 十一、可选优化

以下内容不是完成实验的必要条件，可在基础功能验证通过后再尝试。

### 11.1 VRRP 延迟抢占

防止链路抖动导致反复抢占：

```text
vrrp vrid 10 preempt-mode timer delay 20
```

### 11.2 上行链路跟踪

若希望 AR1 方向链路故障时降低 Master 优先级：

```text
vrrp vrid 10 track interface GigabitEthernet 0/0/24 reduced 30
```

120 降至 90 后低于备份侧 100。此功能不是所有场景都必须，因为流量仍可能经另一核心绕达 AR1。

### 11.3 点到点 OSPF 链路

`/30` 传输链路可在两端一致配置：

```text
ospf network-type p2p
```

减少 DR/BDR 过程，不配置也能工作。

---

## 十二、版本差异验证方法

本次配置基于常见华为 VRP 语法，未在真实 eNSP 中逐条运行。
请在对应设备上先执行：

```text
display version
```

然后在**准确视图**下用 `?` 验证命令是否被支持：

```text
dhcp select ?
dhcp relay server-ip ?
stp instance ?
vrrp vrid 10 ?
traffic-filter ?
```

如果某个命令不被接受，先记录设备型号和 VRP 版本，再按 `display this` 的当前上下文调整，不要凭猜测继续粘贴。

---

## 十三、DHCP 冗余说明（可选进阶）

当前基础设计中：

- LSW3 的 DHCP Relay 指向 `10.0.1.1`
- LSW4 的 DHCP Relay 指向 `10.0.2.1`

如果只断开 **AR1—LSW3** 这条链路，`10.0.1.1` 会不可达，
LSW3 中继的 DHCP 请求会失败；反向断开 **AR1—LSW4** 同理。
这不影响任务书里的验收项，但如果你希望验证"链路级 DHCP 冗余"，
需要把 DHCP 服务器地址改成不依赖单条物理链路的地址。

推荐做法是在 AR1 上创建 Loopback 并发布到 OSPF：

```text
interface LoopBack0
 ip address 1.1.1.1 255.255.255.255
#
ospf 1 router-id 1.1.1.1
 area 0.0.0.0
  network 1.1.1.1 0.0.0.0
#
```

然后把 LSW3、LSW4 所有业务中继接口统一指向：

```text
dhcp select relay
dhcp relay server-ip 1.1.1.1
```

注意：

- `router-id` 本身不是可达地址，必须实际创建 Loopback 并发布。
- AR1 的两个物理接口仍然保留 `dhcp select global`。
- 这只能消除对单条物理链路地址的依赖，AR1 本身仍是单点。
- 双核心同时中继会产生重复中继报文，这是正常现象，
  不要通过删除备份核心中继来"修复"，否则核心故障时 DHCP 会失去冗余。
