# 中小型企业园区网设备配置

> 本文件按截图中的设备名给出每台设备的配置。
> 所有命令基于常见华为 VRP 语法，eNSP V1.3.00.100 可直接粘贴到设备 CLI。
> 配置前请先确认拓扑与连接表一致，并保存工程。

## 阅读说明

- 每个设备小节分两部分：**配置命令** 和 **命令说明**。
- **配置命令** 代码块是可直接粘贴的纯配置，里面没有注释符。
- **命令说明** 表格逐条解释每条命令的作用，顺序与代码块一一对应。
- 不要在配置代码块里自行加 `#` 或 `//` 注释，VRP CLI 不识别这些符号，粘贴后会报错。
- 想看某条命令的作用，直接到同节的「命令说明」表格里找对应行。

## 设备映射

| 任务书 | 截图 | 型号 | 角色 |
|---|---|---|---|
| R1 | AR1 | AR1220 | 总部出口、DHCP 服务器 |
| R2 | AR2 | AR1220 | 分支出口、DHCP 服务器 |
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

### 2.1 配置命令

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

### 2.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 从用户视图进入系统视图，才能开始配置设备 |
| `sysname LSW1` | 把设备名称改成 LSW1，方便识别 |
| `vlan batch 10 20 30 50` | 一次性创建 VLAN 10、20、30、50 |
| `stp enable` | 在全局启用生成树功能 |
| `stp mode mstp` | 把生成树模式设为 MSTP，才能按实例配置 |
| `stp region-configuration` | 进入 MST 域配置视图 |
| `region-name COMPANY` | 设置 MST 域名为 COMPANY，四台总部交换机必须相同 |
| `revision-level 1` | 设置 MST 修订级别为 1，四台总部交换机必须相同 |
| `instance 1 vlan 10 30` | 把 VLAN 10 和 30 映射到 MST 实例 1 |
| `instance 2 vlan 20 50` | 把 VLAN 20 和 50 映射到 MST 实例 2 |
| `active region-configuration` | 激活 MST 域配置，不激活则映射不生效 |
| `interface GigabitEthernet 0/0/1` | 进入 GE0/0/1 接口视图 |
| `port link-type trunk` | 把该接口设为 trunk 模式，用于跨设备传多个 VLAN |
| `port trunk allow-pass vlan 10 20 30 50` | 允许 trunk 放通这四个业务 VLAN |
| `interface GigabitEthernet 0/0/2` | 进入第二条上联 trunk 接口视图 |
| `port link-type trunk` | 第二条上联也设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 第二条上联放通这四个业务 VLAN |
| `interface GigabitEthernet 0/0/10` | 进入 PC1（行政）的接入端口视图 |
| `port link-type access` | 把该端口设为 access 模式，只属于一个 VLAN |
| `port default vlan 10` | 把该接入端口划入 VLAN 10（行政） |
| `stp edged-port enable` | 把该终端端口设为边缘端口，跳过生成树计算、快速转发 |
| `interface GigabitEthernet 0/0/11` | 进入 PC2（研发）的接入端口视图 |
| `port link-type access` | 设为 access 模式 |
| `port default vlan 20` | 划入 VLAN 20（研发） |
| `stp edged-port enable` | 设为边缘端口 |

---

## 三、LSW2：财务、服务器接入

### 3.1 配置命令

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

### 3.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname LSW2` | 把设备名称改成 LSW2 |
| `vlan batch 10 20 30 50` | 创建 VLAN 10、20、30、50 |
| `stp enable` | 启用生成树 |
| `stp mode mstp` | 生成树模式设为 MSTP |
| `stp region-configuration` | 进入 MST 域配置视图 |
| `region-name COMPANY` | MST 域名设为 COMPANY，与 LSW1/3/4 一致 |
| `revision-level 1` | 修订级别设为 1，与 LSW1/3/4 一致 |
| `instance 1 vlan 10 30` | VLAN 10/30 映射到实例 1 |
| `instance 2 vlan 20 50` | VLAN 20/50 映射到实例 2 |
| `active region-configuration` | 激活 MST 域配置 |
| `interface GigabitEthernet 0/0/1` | 进入第一条上联 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/2` | 进入第二条上联 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/10` | 进入 PC3（财务）接入端口视图 |
| `port link-type access` | 设为 access |
| `port default vlan 30` | 划入 VLAN 30（财务） |
| `stp edged-port enable` | 设为边缘端口 |
| `interface GigabitEthernet 0/0/11` | 进入 Server1（服务器）接入端口视图 |
| `port link-type access` | 设为 access |
| `port default vlan 50` | 划入 VLAN 50（服务器） |
| `stp edged-port enable` | 设为边缘端口 |

---

## 四、LSW5：分支接入

### 4.1 配置命令

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

### 4.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname LSW5` | 把设备名称改成 LSW5 |
| `vlan batch 40` | 创建 VLAN 40（分支） |
| `interface GigabitEthernet 0/0/1` | 进入 PC4 接入端口视图 |
| `port link-type access` | 设为 access |
| `port default vlan 40` | 划入 VLAN 40（分支） |
| `stp edged-port enable` | 设为边缘端口 |
| `interface GigabitEthernet 0/0/24` | 进入上联 AR2 的端口视图 |
| `port link-type access` | 设为 access（不是 trunk） |
| `port default vlan 40` | 划入 VLAN 40 |

> 说明：AR2 的 `GE0/0/1` 是普通三层物理接口，不是 dot1q 子接口，
> 所以 LSW5 的 `GE0/0/24` 必须是 **access VLAN 40**，不能配 trunk。

---

## 五、LSW3：核心 1

### 5.1 配置命令

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

### 5.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname LSW3` | 把设备名称改成 LSW3 |
| `vlan batch 10 20 30 50 100 102` | 创建四个业务 VLAN 和传输 VLAN 100、102 |
| `stp enable` | 启用生成树 |
| `stp mode mstp` | 生成树模式设为 MSTP |
| `stp region-configuration` | 进入 MST 域配置视图 |
| `region-name COMPANY` | MST 域名设为 COMPANY |
| `revision-level 1` | 修订级别设为 1 |
| `instance 1 vlan 10 30` | VLAN 10/30 映射到实例 1 |
| `instance 2 vlan 20 50` | VLAN 20/50 映射到实例 2 |
| `active region-configuration` | 激活 MST 域配置 |
| `stp instance 1 root primary` | 让本设备成为 MST 实例 1 的主根桥 |
| `stp instance 2 root secondary` | 让本设备成为 MST 实例 2 的备份根桥 |
| `interface Vlanif 10` | 进入 VLAN 10 的三层虚接口视图 |
| `ip address 192.168.10.2 255.255.255.0` | 给 VLAN 10 网关配置本端实地址 |
| `vrrp vrid 10 virtual-ip 192.168.10.1` | 创建 VRRP 备份组 10，虚拟网关为 192.168.10.1 |
| `vrrp vrid 10 priority 120` | 把备份组 10 优先级设为 120，让本设备成为 Master |
| `interface Vlanif 20` | 进入 VLAN 20 的三层虚接口视图 |
| `ip address 192.168.20.2 255.255.255.0` | 配置 VLAN 20 网关实地址 |
| `vrrp vrid 20 virtual-ip 192.168.20.1` | 创建 VRRP 备份组 20，虚拟网关为 192.168.20.1 |
| `interface Vlanif 30` | 进入 VLAN 30 的三层虚接口视图 |
| `ip address 192.168.30.2 255.255.255.0` | 配置 VLAN 30 网关实地址 |
| `vrrp vrid 30 virtual-ip 192.168.30.1` | 创建 VRRP 备份组 30，虚拟网关为 192.168.30.1 |
| `vrrp vrid 30 priority 120` | 把备份组 30 优先级设为 120，让本设备成为 Master |
| `interface Vlanif 50` | 进入 VLAN 50 的三层虚接口视图 |
| `ip address 192.168.50.2 255.255.255.0` | 配置 VLAN 50 网关实地址 |
| `vrrp vrid 50 virtual-ip 192.168.50.1` | 创建 VRRP 备份组 50，虚拟网关为 192.168.50.1 |
| `interface Vlanif 100` | 进入 VLAN 100 的三层虚接口视图 |
| `ip address 10.0.1.2 255.255.255.252` | 配置到 AR1 的传输网段地址 |
| `interface Vlanif 102` | 进入 VLAN 102 的三层虚接口视图 |
| `ip address 10.0.3.1 255.255.255.252` | 配置核心互联传输网段地址 |
| `interface GigabitEthernet 0/0/1` | 进入连接 LSW1 的 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/2` | 进入连接 LSW2 的 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/3` | 进入连接 LSW4 的核心互联 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50 102` | 放通四个业务 VLAN 和核心互联 VLAN 102 |
| `interface GigabitEthernet 0/0/24` | 进入连接 AR1 的接口视图 |
| `port link-type access` | 设为 access |
| `port default vlan 100` | 划入 VLAN 100（到 AR1 的传输） |
| `dhcp enable` | 全局开启 DHCP 功能，本设备要提供 DHCP 中继 |
| `interface Vlanif 10` | 再次进入 VLAN 10 虚接口，配置中继 |
| `dhcp select relay` | 把该接口设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.1.1` | 指定 DHCP 请求转发到 AR1 的 10.0.1.1 |
| `interface Vlanif 20` | 进入 VLAN 20 虚接口 |
| `dhcp select relay` | 设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.1.1` | 转发到 AR1 的 10.0.1.1 |
| `interface Vlanif 30` | 进入 VLAN 30 虚接口 |
| `dhcp select relay` | 设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.1.1` | 转发到 AR1 的 10.0.1.1 |
| `acl 3000` | 创建并进入高级 ACL 3000 视图 |
| `rule 5 permit ip source 192.168.10.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 5：允许行政网段访问财务网段 |
| `rule 10 deny ip source 192.168.20.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 10：拒绝研发网段访问财务网段 |
| `rule 15 deny ip source 192.168.40.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 15：拒绝分支网段访问财务网段 |
| `rule 20 permit ip` | 规则 20：放行其他所有 IP 流量 |
| `interface Vlanif 30` | 再次进入 VLAN 30 虚接口，应用 ACL |
| `traffic-filter outbound acl 3000` | 在 VLAN 30 出方向应用 ACL 3000 做流量过滤 |
| `ospf 1 router-id 11.11.11.11` | 启动 OSPF 进程 1，Router ID 设为 11.11.11.11 |
| `silent-interface Vlanif 10` | 抑制 VLAN 10 虚接口的 OSPF Hello，不建邻居但仍发布该网段 |
| `silent-interface Vlanif 20` | 抑制 VLAN 20 虚接口的 OSPF Hello |
| `silent-interface Vlanif 30` | 抑制 VLAN 30 虚接口的 OSPF Hello |
| `silent-interface Vlanif 50` | 抑制 VLAN 50 虚接口的 OSPF Hello |
| `area 0.0.0.0` | 进入 OSPF Area 0（骨干区域） |
| `network 192.168.10.0 0.0.0.255` | 发布 VLAN 10 网段，通配符掩码 0.0.0.255 表示 /24 |
| `network 192.168.20.0 0.0.0.255` | 发布 VLAN 20 网段 |
| `network 192.168.30.0 0.0.0.255` | 发布 VLAN 30 网段 |
| `network 192.168.50.0 0.0.0.255` | 发布 VLAN 50 网段 |
| `network 10.0.1.0 0.0.0.3` | 发布到 AR1 的传输网段 /30 |
| `network 10.0.3.0 0.0.0.3` | 发布核心互联传输网段 /30 |

---

## 六、LSW4：核心 2

### 6.1 配置命令

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

### 6.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname LSW4` | 把设备名称改成 LSW4 |
| `vlan batch 10 20 30 50 101 102` | 创建四个业务 VLAN 和传输 VLAN 101、102 |
| `stp enable` | 启用生成树 |
| `stp mode mstp` | 生成树模式设为 MSTP |
| `stp region-configuration` | 进入 MST 域配置视图 |
| `region-name COMPANY` | MST 域名设为 COMPANY |
| `revision-level 1` | 修订级别设为 1 |
| `instance 1 vlan 10 30` | VLAN 10/30 映射到实例 1 |
| `instance 2 vlan 20 50` | VLAN 20/50 映射到实例 2 |
| `active region-configuration` | 激活 MST 域配置 |
| `stp instance 1 root secondary` | 让本设备成为 MST 实例 1 的备份根桥 |
| `stp instance 2 root primary` | 让本设备成为 MST 实例 2 的主根桥 |
| `interface Vlanif 10` | 进入 VLAN 10 的三层虚接口视图 |
| `ip address 192.168.10.3 255.255.255.0` | 配置 VLAN 10 网关实地址 |
| `vrrp vrid 10 virtual-ip 192.168.10.1` | 创建 VRRP 备份组 10，虚拟网关为 192.168.10.1 |
| `interface Vlanif 20` | 进入 VLAN 20 的三层虚接口视图 |
| `ip address 192.168.20.3 255.255.255.0` | 配置 VLAN 20 网关实地址 |
| `vrrp vrid 20 virtual-ip 192.168.20.1` | 创建 VRRP 备份组 20，虚拟网关为 192.168.20.1 |
| `vrrp vrid 20 priority 120` | 把备份组 20 优先级设为 120，让本设备成为 Master |
| `interface Vlanif 30` | 进入 VLAN 30 的三层虚接口视图 |
| `ip address 192.168.30.3 255.255.255.0` | 配置 VLAN 30 网关实地址 |
| `vrrp vrid 30 virtual-ip 192.168.30.1` | 创建 VRRP 备份组 30，虚拟网关为 192.168.30.1 |
| `interface Vlanif 50` | 进入 VLAN 50 的三层虚接口视图 |
| `ip address 192.168.50.3 255.255.255.0` | 配置 VLAN 50 网关实地址 |
| `vrrp vrid 50 virtual-ip 192.168.50.1` | 创建 VRRP 备份组 50，虚拟网关为 192.168.50.1 |
| `vrrp vrid 50 priority 120` | 把备份组 50 优先级设为 120，让本设备成为 Master |
| `interface Vlanif 101` | 进入 VLAN 101 的三层虚接口视图 |
| `ip address 10.0.2.2 255.255.255.252` | 配置到 AR1 的传输网段地址 |
| `interface Vlanif 102` | 进入 VLAN 102 的三层虚接口视图 |
| `ip address 10.0.3.2 255.255.255.252` | 配置核心互联传输网段地址 |
| `interface GigabitEthernet 0/0/1` | 进入连接 LSW1 的 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/2` | 进入连接 LSW2 的 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50` | 放通四个业务 VLAN |
| `interface GigabitEthernet 0/0/3` | 进入连接 LSW3 的核心互联 trunk 接口视图 |
| `port link-type trunk` | 设为 trunk |
| `port trunk allow-pass vlan 10 20 30 50 102` | 放通四个业务 VLAN 和核心互联 VLAN 102 |
| `interface GigabitEthernet 0/0/24` | 进入连接 AR1 的接口视图 |
| `port link-type access` | 设为 access |
| `port default vlan 101` | 划入 VLAN 101（到 AR1 的传输） |
| `dhcp enable` | 全局开启 DHCP 功能，本设备要提供 DHCP 中继 |
| `interface Vlanif 10` | 再次进入 VLAN 10 虚接口，配置中继 |
| `dhcp select relay` | 把该接口设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.2.1` | 指定 DHCP 请求转发到 AR1 的 10.0.2.1 |
| `interface Vlanif 20` | 进入 VLAN 20 虚接口 |
| `dhcp select relay` | 设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.2.1` | 转发到 AR1 的 10.0.2.1 |
| `interface Vlanif 30` | 进入 VLAN 30 虚接口 |
| `dhcp select relay` | 设为 DHCP 中继模式 |
| `dhcp relay server-ip 10.0.2.1` | 转发到 AR1 的 10.0.2.1 |
| `acl 3000` | 创建并进入高级 ACL 3000 视图 |
| `rule 5 permit ip source 192.168.10.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 5：允许行政网段访问财务网段 |
| `rule 10 deny ip source 192.168.20.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 10：拒绝研发网段访问财务网段 |
| `rule 15 deny ip source 192.168.40.0 0.0.0.255 destination 192.168.30.0 0.0.0.255` | 规则 15：拒绝分支网段访问财务网段 |
| `rule 20 permit ip` | 规则 20：放行其他所有 IP 流量 |
| `interface Vlanif 30` | 再次进入 VLAN 30 虚接口，应用 ACL |
| `traffic-filter outbound acl 3000` | 在 VLAN 30 出方向应用 ACL 3000 做流量过滤 |
| `ospf 1 router-id 12.12.12.12` | 启动 OSPF 进程 1，Router ID 设为 12.12.12.12 |
| `silent-interface Vlanif 10` | 抑制 VLAN 10 虚接口的 OSPF Hello |
| `silent-interface Vlanif 20` | 抑制 VLAN 20 虚接口的 OSPF Hello |
| `silent-interface Vlanif 30` | 抑制 VLAN 30 虚接口的 OSPF Hello |
| `silent-interface Vlanif 50` | 抑制 VLAN 50 虚接口的 OSPF Hello |
| `area 0.0.0.0` | 进入 OSPF Area 0 |
| `network 192.168.10.0 0.0.0.255` | 发布 VLAN 10 网段 |
| `network 192.168.20.0 0.0.0.255` | 发布 VLAN 20 网段 |
| `network 192.168.30.0 0.0.0.255` | 发布 VLAN 30 网段 |
| `network 192.168.50.0 0.0.0.255` | 发布 VLAN 50 网段 |
| `network 10.0.2.0 0.0.0.3` | 发布到 AR1 的传输网段 /30 |
| `network 10.0.3.0 0.0.0.3` | 发布核心互联传输网段 /30 |

---

## 七、AR1：总部出口与 DHCP 服务器

### 7.1 配置命令

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

### 7.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname AR1` | 把设备名称改成 AR1 |
| `vlan batch 100 101` | 创建传输 VLAN 100、101 |
| `dhcp enable` | 全局开启 DHCP，本设备是 DHCP 服务器 |
| `ip pool vlan10` | 创建名为 vlan10 的 IP 地址池 |
| `network 192.168.10.0 mask 255.255.255.0` | 地址池网段为 192.168.10.0/24 |
| `gateway-list 192.168.10.1` | 给客户端分配的网关为 192.168.10.1 |
| `excluded-ip-address 192.168.10.1 192.168.10.20` | 排除 .1 到 .20，不分配给客户端 |
| `dns-list 192.168.10.1` | 给客户端分配的 DNS 地址 |
| `ip pool vlan20` | 创建名为 vlan20 的地址池 |
| `network 192.168.20.0 mask 255.255.255.0` | 地址池网段为 192.168.20.0/24 |
| `gateway-list 192.168.20.1` | 客户端网关为 192.168.20.1 |
| `excluded-ip-address 192.168.20.1 192.168.20.20` | 排除 .1 到 .20 |
| `dns-list 192.168.20.1` | 分配的 DNS 地址 |
| `ip pool vlan30` | 创建名为 vlan30 的地址池 |
| `network 192.168.30.0 mask 255.255.255.0` | 地址池网段为 192.168.30.0/24 |
| `gateway-list 192.168.30.1` | 客户端网关为 192.168.30.1 |
| `excluded-ip-address 192.168.30.1 192.168.30.20` | 排除 .1 到 .20 |
| `dns-list 192.168.30.1` | 分配的 DNS 地址 |
| `interface GigabitEthernet 0/0/0` | 进入连接 LSW3 的接口视图 |
| `ip address 10.0.1.1 255.255.255.252` | 配置接口地址 |
| `dhcp select global` | 让该接口使用全局地址池响应 DHCP 请求 |
| `interface GigabitEthernet 0/0/1` | 进入连接 LSW4 的接口视图 |
| `ip address 10.0.2.1 255.255.255.252` | 配置接口地址 |
| `dhcp select global` | 该接口也使用全局地址池响应 DHCP |
| `interface GigabitEthernet 0/0/2` | 进入连接 AR2 的接口视图 |
| `ip address 10.0.12.1 255.255.255.252` | 配置总部—分支互联地址 |
| `ospf 1 router-id 1.1.1.1` | 启动 OSPF 进程 1，Router ID 设为 1.1.1.1 |
| `area 0.0.0.0` | 进入 OSPF Area 0 |
| `network 10.0.1.0 0.0.0.3` | 发布到 LSW3 的传输网段 |
| `network 10.0.2.0 0.0.0.3` | 发布到 LSW4 的传输网段 |
| `network 10.0.12.0 0.0.0.3` | 发布到 AR2 的互联网段 |

> 说明：AR1 是 DHCP 服务器。核心把请求中继到 AR1 后，
> AR1 **根据中继填入的 giaddr 选择对应地址池**，不是根据入接口 IP 选池。
> 因此 `GE0/0/0` 和 `GE0/0/1` 都必须配置 `dhcp select global`，
> 且 AR1 到四个业务网段的 OSPF 回程路由必须存在。
> 不要在核心面向客户端的 Vlanif 上配置 `dhcp select global`。

---

## 八、AR2：分支出口与分支 DHCP 服务器

### 8.1 配置命令

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

### 8.2 命令说明

| 命令 | 作用 |
|---|---|
| `system-view` | 进入系统视图 |
| `sysname AR2` | 把设备名称改成 AR2 |
| `vlan batch 40` | 创建 VLAN 40（分支） |
| `dhcp enable` | 全局开启 DHCP，本设备是分支 DHCP 服务器 |
| `ip pool vlan40` | 创建名为 vlan40 的地址池 |
| `network 192.168.40.0 mask 255.255.255.0` | 地址池网段为 192.168.40.0/24 |
| `gateway-list 192.168.40.1` | 客户端网关为 192.168.40.1 |
| `excluded-ip-address 192.168.40.1 192.168.40.20` | 排除 .1 到 .20 |
| `dns-list 192.168.40.1` | 分配的 DNS 地址 |
| `interface GigabitEthernet 0/0/0` | 进入连接 AR1 的接口视图 |
| `ip address 10.0.12.2 255.255.255.252` | 配置总部—分支互联地址 |
| `interface GigabitEthernet 0/0/1` | 进入连接 LSW5 的接口视图 |
| `ip address 192.168.40.1 255.255.255.0` | 配置分支网段网关地址 |
| `dhcp select global` | 让该接口使用全局地址池响应分支 DHCP 请求 |
| `ospf 1 router-id 2.2.2.2` | 启动 OSPF 进程 1，Router ID 设为 2.2.2.2 |
| `silent-interface GigabitEthernet 0/0/1` | 抑制分支接口的 OSPF Hello，不建邻居但仍发布该网段 |
| `area 0.0.0.0` | 进入 OSPF Area 0 |
| `network 10.0.12.0 0.0.0.3` | 发布总部—分支互联网段 |
| `network 192.168.40.0 0.0.0.255` | 发布分支业务网段 |

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

### 10.1 配置命令

```text
return
save
```

### 10.2 命令说明

| 命令 | 作用 |
|---|---|
| `return` | 从任意配置视图退回用户视图 |
| `save` | 把当前运行配置保存到设备配置文件，重启后不丢失 |

### 10.3 检查命令

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

### 10.4 检查命令说明

| 命令 | 作用 |
|---|---|
| `display version` | 查看设备型号与软件版本，用于核对命令差异 |
| `display stp region-configuration` | 查看 MST 域配置，核对区域名、修订级别、VLAN 映射 |
| `display stp brief` | 查看生成树端口角色与状态 |
| `display stp instance 1` | 查看 MST 实例 1 的生成树状态 |
| `display stp instance 2` | 查看 MST 实例 2 的生成树状态 |
| `display vrrp brief` | 查看 VRRP 备份组的 Master/Backup 状态 |
| `display ip interface brief` | 查看各接口 IP、掩码与协议状态 |
| `display ospf peer brief` | 查看 OSPF 邻居关系 |
| `display ip routing-table protocol ospf` | 查看通过 OSPF 学到的路由 |
| `display ip pool` | 查看地址池使用与已分配地址 |
| `display dhcp relay statistics` | 查看 DHCP 中继统计，判断中继是否工作 |
| `display acl 3000` | 查看 ACL 3000 的规则与命中次数 |
| `display traffic-filter applied-record` | 查看流量过滤的应用记录 |

### 10.5 关键判断标准

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

#### 11.1.1 配置命令

```text
vrrp vrid 10 preempt-mode timer delay 20
```

#### 11.1.2 命令说明

| 命令 | 作用 |
|---|---|
| `vrrp vrid 10 preempt-mode timer delay 20` | 设置 VRRP 备份组 10 的抢占延迟为 20 秒，防止链路抖动导致反复抢占 |

### 11.2 上行链路跟踪

#### 11.2.1 配置命令

```text
vrrp vrid 10 track interface GigabitEthernet 0/0/24 reduced 30
```

#### 11.2.2 命令说明

| 命令 | 作用 |
|---|---|
| `vrrp vrid 10 track interface GigabitEthernet 0/0/24 reduced 30` | 跟踪 GE0/0/24 接口，接口故障时优先级降低 30，从 120 降到 90，低于备份侧的 100 |

> 说明：120 降至 90 后低于备份侧 100。此功能不是所有场景都必须，因为流量仍可能经另一核心绕达 AR1。

### 11.3 点到点 OSPF 链路

#### 11.3.1 配置命令

```text
ospf network-type p2p
```

#### 11.3.2 命令说明

| 命令 | 作用 |
|---|---|
| `ospf network-type p2p` | 把该传输链路的 OSPF 网络类型设为点到点，减少 DR/BDR 过程 |

> 说明：`/30` 传输链路可在两端一致配置，不配置也能工作。

---

## 十二、版本差异验证方法

本次配置基于常见华为 VRP 语法，未在真实 eNSP 中逐条运行。

### 12.1 配置命令

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
display this
```

### 12.2 命令说明

| 命令 | 作用 |
|---|---|
| `display version` | 查看设备型号与 VRP 版本 |
| `dhcp select ?` | 在当前视图下查看 `dhcp select` 支持的参数 |
| `dhcp relay server-ip ?` | 查看中继服务器地址命令的用法 |
| `stp instance ?` | 查看 `stp instance` 支持的参数 |
| `vrrp vrid 10 ?` | 查看 VRRP 备份组 10 下可用的子命令 |
| `traffic-filter ?` | 查看流量过滤命令的用法 |
| `display this` | 查看当前视图下已生效的配置 |

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

### 13.1 配置命令

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

### 13.2 命令说明

| 命令 | 作用 |
|---|---|
| `interface LoopBack0` | 进入 Loopback 0 虚接口视图 |
| `ip address 1.1.1.1 255.255.255.255` | 给 Loopback 配置一个 /32 地址，作为稳定的 DHCP 服务器地址 |
| `ospf 1 router-id 1.1.1.1` | 启动 OSPF 进程 1，Router ID 设为 1.1.1.1 |
| `network 1.1.1.1 0.0.0.0` | 发布 Loopback 的 /32 地址，让全网都能路由到它 |
| `dhcp select relay` | 核心侧仍设为 DHCP 中继模式 |
| `dhcp relay server-ip 1.1.1.1` | 把 DHCP 请求统一转发到 Loopback 地址，不再依赖单条物理链路 |

注意：

- `router-id` 本身不是可达地址，必须实际创建 Loopback 并发布。
- AR1 的两个物理接口仍然保留 `dhcp select global`。
- 这只能消除对单条物理链路地址的依赖，AR1 本身仍是单点。
- 双核心同时中继会产生重复中继报文，这是正常现象，
  不要通过删除备份核心中继来"修复"，否则核心故障时 DHCP 会失去冗余。

---

## 十四、接口名随设备型号变化

同一个拓扑位置换成不同型号，接口名就会变。上文代码按 `S5700` 接入交换机写；
如果接入或分支交换机用 `S3700`，**照抄会报错**，要按下面的对照替换：

| 位置 | S5700（上文代码） | S3700（实际工程） |
|---|---|---|
| LSW1 / LSW2 / LSW5 接终端 | `GigabitEthernet 0/0/10`、`0/0/11` | `Ethernet 0/0/10`、`0/0/11` |
| LSW1 / LSW2 / LSW5 上联核心 | `GigabitEthernet 0/0/1`、`0/0/2` | `Ethernet 0/0/1`、`0/0/2` |
| 核心 LSW3 / LSW4 | `GigabitEthernet 0/0/1`–`0/0/24` | 相同，S5700 只有千兆口 |
| AR1—AR2 互联 | `GigabitEthernet 0/0/2` | `GigabitEthernet 2/0/0`，需先 `board add 0/2 1GEC` |

编号规律：

- 交换机端口从 1 开始，`Ethernet 0/0/1` 是第一个百兆口，`GigabitEthernet 0/0/1` 是第一个千兆口。
- 终端（PC、Server）只有一个以太网口，接口名是 `Ethernet 0/0/1`。
- 路由器端口从 0 开始，`GigabitEthernet 0/0/0` 是第一个千兆口。
- 扩展卡端口带槽位号：AR1220 的单口 GE 卡插在 2 号槽，接口就是 `GigabitEthernet 2/0/0`。

核对办法：在设备上执行 `display interface brief`，或解析自己的 `.topo`，
连线表里给出的接口名就是设备上真实的名字。

```text
display interface brief
```
