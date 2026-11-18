# 双部门静态路由实验指南

这是一个可以独立完成的入门实验：两个部门各使用一个 VLAN 和一个业务网段，两台路由器通过独立的 `/30` 互联网段连接，最后用静态路由实现跨部门通信。

> 下面给出目标、地址和验收方法，但实际搭建、配置、抓包与结果记录需要你在 eNSP 中完成。解析 `.topo` 只能整理结构，不能代替 ping 测试。

## 1. 实验目标

- 熟悉 eNSP 设备添加、连线、启动和工程保存。
- 配置交换机 Access 接口与 VLAN。
- 配置路由器接口地址和静态路由。
- 使用 PC 与路由器的 ping、路由表验证结果。
- 使用本仓库脚本生成拓扑文档，并人工核对连线和接口。

## 2. 设备与连线

添加以下设备，并将设备名改为表中名称：

| 设备 | 数量 | 建议名称 |
|---|---:|---|
| AR1220 | 2 | R1、R2 |
| S5700 | 2 | LSW1、LSW2 |
| PC | 4 | PC1、PC2、PC3、PC4 |

按表连线。若实际选用接口不同，记录真实接口，不要照搬文档。

| 本端 | 本端接口 | 对端 | 对端接口 |
|---|---|---|---|
| PC1 | Ethernet0/0/1 | LSW1 | GE0/0/1 |
| PC2 | Ethernet0/0/1 | LSW1 | GE0/0/2 |
| LSW1 | GE0/0/3 | R1 | GE0/0/0 |
| R1 | GE0/0/1 | R2 | GE0/0/1 |
| R2 | GE0/0/0 | LSW2 | GE0/0/3 |
| PC3 | Ethernet0/0/1 | LSW2 | GE0/0/1 |
| PC4 | Ethernet0/0/1 | LSW2 | GE0/0/2 |

完成后应为 **8 台设备、7 条链路**。

## 3. 地址规划

### 业务与互联网段

| 网段 | 用途 | 网关 |
|---|---|---|
| `192.168.10.0/24` | 左侧部门，VLAN 10 | R1：`192.168.10.1` |
| `192.168.20.0/24` | 右侧部门，VLAN 20 | R2：`192.168.20.1` |
| `10.0.12.0/30` | R1—R2 点对点互联 | 无 PC 网关 |

### PC 地址

| PC | IP 地址 | 子网掩码 | 默认网关 |
|---|---|---|---|
| PC1 | `192.168.10.11` | `255.255.255.0` | `192.168.10.1` |
| PC2 | `192.168.10.12` | `255.255.255.0` | `192.168.10.1` |
| PC3 | `192.168.20.11` | `255.255.255.0` | `192.168.20.1` |
| PC4 | `192.168.20.12` | `255.255.255.0` | `192.168.20.1` |

### 路由器接口

| 设备 | 接口 | IP/掩码 |
|---|---|---|
| R1 | GE0/0/0 | `192.168.10.1/24` |
| R1 | GE0/0/1 | `10.0.12.1/30` |
| R2 | GE0/0/0 | `192.168.20.1/24` |
| R2 | GE0/0/1 | `10.0.12.2/30` |

## 4. 配置参考

在 eNSP 中启动设备，等待设备就绪后进入 CLI。以下命令用于核对配置思路；请按真实设备提示和接口执行。

### LSW1

```text
system-view
sysname LSW1
vlan batch 10
interface GigabitEthernet0/0/1
 port link-type access
 port default vlan 10
interface GigabitEthernet0/0/2
 port link-type access
 port default vlan 10
interface GigabitEthernet0/0/3
 port link-type access
 port default vlan 10
return
save
```

### LSW2

```text
system-view
sysname LSW2
vlan batch 20
interface GigabitEthernet0/0/1
 port link-type access
 port default vlan 20
interface GigabitEthernet0/0/2
 port link-type access
 port default vlan 20
interface GigabitEthernet0/0/3
 port link-type access
 port default vlan 20
return
save
```

这里每台交换机只有一个 VLAN，因此上联路由器的接口也配置为该 VLAN 的 Access 接口，不需要 Trunk。

### R1

```text
system-view
sysname R1
interface GigabitEthernet0/0/0
 ip address 192.168.10.1 255.255.255.0
 undo shutdown
interface GigabitEthernet0/0/1
 ip address 10.0.12.1 255.255.255.252
 undo shutdown
quit
ip route-static 192.168.20.0 255.255.255.0 10.0.12.2
return
save
```

### R2

```text
system-view
sysname R2
interface GigabitEthernet0/0/0
 ip address 192.168.20.1 255.255.255.0
 undo shutdown
interface GigabitEthernet0/0/1
 ip address 10.0.12.2 255.255.255.252
 undo shutdown
quit
ip route-static 192.168.10.0 255.255.255.0 10.0.12.1
return
save
```

执行 `save` 时按设备提示确认保存。不同 eNSP 镜像的提示可能略有不同。

## 5. 验证与留证

按顺序验证，不要只保存最后一张成功截图。

1. **接口状态**：在 R1、R2 执行 `display ip interface brief`，核对四个接口的 IP 和状态。
2. **路由表**：执行 `display ip routing-table`，R1 应有到 `192.168.20.0/24` 的静态路由，R2 应有到 `192.168.10.0/24` 的静态路由。
3. **同网段**：PC1 ping PC2，PC3 ping PC4。
4. **网关**：PC1 ping `192.168.10.1`，PC3 ping `192.168.20.1`。
5. **路由器互联**：R1 ping `10.0.12.2`。
6. **跨网段**：PC1 ping PC3 和 PC4，PC2 也至少完成一次跨网段测试。

在自己的实验记录中填写真实结果：

| 检查项 | 实际结果 | 证据文件/说明 |
|---|---|---|
| R1、R2 接口状态 | 待测试 | 待补充 |
| 两端静态路由 | 待测试 | 待补充 |
| 同网段 ping | 待测试 | 待补充 |
| 跨网段 ping | 待测试 | 待补充 |

如果失败，先记录报错和测试位置，再依次检查 PC 网关、VLAN、接口状态、IP/掩码和静态路由下一跳。不要把未测试的项目写成“成功”。

## 6. 保存并生成拓扑文档

1. 在 eNSP 中将工程保存为 `dual-dept-static-route`，找到该工程的 `.topo` 文件。
2. 在仓库根目录运行（路径换成你的真实路径）：

```powershell
python scripts/ensp_topology.py "D:\ensp-lab\dual-dept-static-route\dual-dept-static-route.topo" -o "out\dual-dept-static-route"
```

3. 打开 `out\dual-dept-static-route\topology.md`，与 eNSP 画布逐项核对。
4. 预期解析结果是 8 台设备、7 条链路；若出现 `#索引`，先记录实际接口，不要手动把未知值改成看似正确的值。
5. 可将自己的 `.topo`、报告和 ping 截图整理到独立实验目录后再提交。发布前删除真实单位信息、个人路径和任何敏感配置。

## 7. 完成标准

- eNSP 拓扑、连线和地址表一致。
- 两端 VLAN 与接口配置正确。
- 静态路由下一跳正确，路由表有对应条目。
- 同网段、网关和跨网段测试均有真实记录。
- 自动报告中的设备数、链路数和接口已经人工核对。
- 文档明确区分“拓扑解析成功”和“网络连通性验证成功”。
