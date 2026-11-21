# 中小型企业园区网实验（本人实做）

本目录是 [企业园区网综合实验任务书](../../docs/eNSP企业园区网综合实验任务书.docx) 的本人实验工程，
在 eNSP V1.3.00.100 上搭建、配置并保存。

## 目录内容

| 文件 | 说明 |
|---|---|
| `enterprise-campus.topo` | eNSP 工程文件，只含拓扑结构与设备位置，**不含设备配置** |
| `configs/*.cfg` | 从工程保存目录中提取的七台设备已保存配置（`local-user` 密码行已移除） |
| `topology.md` | 用 `scripts/ensp_topology.py` 解析本工程得到的设备清单、连线清单和 Mermaid 图 |
| `diagram.mmd` | 上表中同一份拓扑的 Mermaid 源码，便于嵌入其他文档 |

设备：AR1220 × 2（AR1、AR2）、S5700 × 2（LSW3、LSW4）、S3700 × 3（LSW1、LSW2、LSW5）、
PC × 4、Server × 1，共 12 台设备、14 条链路。

## 地址与协议规划

| 项目 | 内容 |
|---|---|
| 业务 VLAN | VLAN10 行政 192.168.10.0/24、VLAN20 研发 192.168.20.0/24、VLAN30 财务 192.168.30.0/24、VLAN50 服务器 192.168.50.0/24 |
| 传输 VLAN | VLAN100 10.0.1.0/30（AR1—LSW3）、VLAN101 10.0.2.0/30（AR1—LSW4）、VLAN102 10.0.3.0/30（LSW3—LSW4） |
| 总会话 | AR1—AR2 10.0.12.0/30，分支 VLAN40 192.168.40.0/24 |
| 网关冗余 | VRRP 虚拟网关 .1；LSW3 主 VLAN10/30，LSW4 主 VLAN20/50 |
| 二层 | MSTP 域 COMPANY，实例 1 承载 VLAN10/30（根 LSW3），实例 2 承载 VLAN20/50（根 LSW4） |
| 路由 | OSPF 进程 1、Area 0，业务 Vlanif 全部 Silent Interface |
| 地址分配 | AR1 集中 DHCP 池（VLAN10/20/30）+ 双核心 Relay；AR2 为分支 VLAN40 提供 DHCP |
| 访问控制 | ACL 3000 在两个核心的 Vlanif30 出方向：允许行政访问财务，拒绝研发与分支访问财务 |

## 已经验证的内容

- 拓扑：解析结果 12 台设备、14 条链路，与 eNSP 画布人工核对一致。
- 二层与中继：PC1 通过 `ipconfig` 获得 `192.168.10.254/24`，网关 `192.168.10.1`，DNS `192.168.10.1`。
  说明 VLAN10 接入端口归属、LSW1—LSW3 的 trunk、DHCP 中继到 AR1、AR1 按 `giaddr` 选池与回程路由均正常。

## 还没有验证的内容

下面这些属于任务书验收项，**本仓库尚未提供实测结果，不能视为已通过**：

- 跨 VLAN、跨网段的 T1–T10 通信测试与 ACL 允许/拒绝双向验证。
- 断开或停用一个核心后的 VRRP/MSTP/OSPF 收敛与恢复。
- 完整验收表 A1–A12 的填写与截图。

## 注意事项

- 本目录只提交 `.topo` 与文本配置。设备 `flash.efz`、VirtualBox 镜像体积大且不可移植，
  已在 `.gitignore` 中排除；把本工程换到另一台机器时，按 `configs/` 里的命令重新配置设备。
- `configs/` 中的配置由 eNSP 保存目录提取，是"设备上实际运行的配置"的原始记录，
  行序与 eNSP `display current-configuration` 输出略有差异，但不影响阅读。
- 两核心配置里 `traffic-filter outbound acl 3000` 在保存文件中显示在全局段。
  如需确认 ACL 实际挂载位置，在 LSW3、LSW4 上执行：

  ```text
  display traffic-filter applied-record
  display acl 3000
  ```

  两条命令的输出应是 `Vlanif30` 上 `outbound` 应用了 `acl 3000`。