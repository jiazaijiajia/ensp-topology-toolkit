# eNSP Topology Toolkit

一个只依赖 Python 标准库的 eNSP `.topo` 解析工具：把实验拓扑转换为设备清单、接口连线表和 Mermaid 图，减少手工整理文档的工作。

仓库同时提供一个可亲手完成的 eNSP 实验：中级企业园区网综合实验。程序负责整理拓扑，网络配置与连通性验证仍在 eNSP 中完成。

## 功能

- 读取 eNSP 保存的 `.topo` 文件，不要求启动设备。
- 生成设备名称、型号、Console 端口和接口数量清单。
- 将内部接口索引转换为真实接口名，生成连线表：交换机和终端（PC、Server）的端口从 1 编号，
  路由器从 0 编号，扩展卡端口带槽位号（如 `GE2/0/0`）。
- 生成可由 GitHub 显示的 Mermaid 拓扑图。
- 标记缺失端点、缺失接口信息和无法识别的接口索引，不静默猜测。
- 支持中文设备名和包含空格的路径。

## 环境与限制

- Windows 10/11；其他可运行 Python 3.9+ 的系统也可使用命令行。
- Python 3.9 或更高版本，无第三方依赖。
- 已在本机 eNSP V1.3.00.100 自带的 40 个 `.topo` 示例上完成解析回归。
- 当前只解析拓扑结构，**不读取设备运行状态，不下发配置，也不证明网络互通**。
- 接口名按 eNSP 的编号习惯还原，并用真实设备配置核对过；无法确认的索引会显示为 `#索引`，请结合 eNSP 界面核对。

## 快速使用

### 方法一：拖放文件（Windows）

1. 安装 Python，并在安装界面勾选 **Add Python to PATH**。
2. 在 eNSP 中保存实验，找到对应的 `.topo` 文件。
3. 将 `.topo` 文件拖到 `scripts/run-parse.bat` 上。
4. 在原拓扑旁查看 `ensp-out\拓扑名\`：

```text
topology.md   完整报告，GitHub 可直接显示其中的 Mermaid 图
diagram.mmd   单独的 Mermaid 源码
```

### 方法二：命令行

在仓库根目录执行：

```powershell
python scripts/ensp_topology.py "D:\ensp-lab\campus\campus.topo" -o "out\campus"
```

不指定 `-o` 时，报告直接打印到终端：

```powershell
python scripts/ensp_topology.py "D:\ensp-lab\campus\campus.topo"
```

查看完整参数：

```powershell
python scripts/ensp_topology.py --help
```

## 本人的实验工程

[中小型企业园区网实验](labs/enterprise-campus/README.md) 是按任务书实际搭建并保存的工程：
包含 `.topo`、七台设备的已保存配置、解析后的设备与连线清单，以及
[已完成的验证记录](labs/enterprise-campus/README.md#已经验证的内容)和
[尚未验证的验收项](labs/enterprise-campus/README.md#还没有验证的内容)。

这个工程同时也是解析器的输出示例：[topology.md](labs/enterprise-campus/topology.md) 是设备与连线清单，
[diagram.mmd](labs/enterprise-campus/diagram.mmd) 是 Mermaid 图源。

## 实验任务书

- **中级综合实验**：[中小型企业园区网综合实验任务书](docs/eNSP企业园区网综合实验任务书.docx)，包含双核心、MSTP、VRRP、OSPF、DHCP Relay、ACL 和冗余切换验证。
- **设备配置**：[企业园区网逐台设备配置](docs/enterprise-campus-device-configs.md)，按截图设备名给出 AR1、AR2、LSW1～LSW5 的完整命令，并逐条说明每条命令的作用。
- [查看企业园区网高清拓扑图](docs/images/enterprise-campus-topology.png)。图中设备名与接口名取自本人工程保存的 `.topo`；具体 MSTP 阻塞端口、VRRP 主备和 OSPF 路径以真实设备输出为准。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

测试使用代码内构造的最小拓扑，不依赖本机安装 eNSP，也不包含厂商示例文件。

本次本地验证结果：

- Python 3.14.5：17 项单元测试全部通过。
- eNSP 自带示例：40/40 解析成功，共读取 212 台设备、211 条链路。
- `Campus_Network.topo`：43 台设备、76 条链路。

## 项目结构

```text
ensp-topology-toolkit/
├─ scripts/
│  ├─ ensp_topology.py      # 解析器与命令行入口
│  └─ run-parse.bat         # Windows 拖放启动器
├─ tests/
│  └─ test_topology.py      # 标准库 unittest 测试
├─ labs/
│  └─ enterprise-campus/    # 本人实做的企业园区网工程
│     ├─ enterprise-campus.topo  # 拓扑文件
│     ├─ configs/                # 七台设备的已保存配置
│     ├─ topology.md             # 解析得到的设备与连线清单
│     └─ diagram.mmd             # Mermaid 源码
├─ docs/
│  ├─ eNSP企业园区网综合实验任务书.docx     # 中级综合任务书
│  ├─ enterprise-campus-device-configs.md # 中级实验逐台设备配置
│  └─ images/enterprise-campus-topology.png
└─ .github/workflows/
   └─ tests.yml             # GitHub Actions 自动测试
```

## 发布前注意

- 不要上传整个 eNSP 安装目录、VirtualBox 镜像或设备 `flash.efz`。
- 自己的 `.topo` 可以按需提交，但发布前先检查其中是否含路径、设备名等隐私信息。
- 不要公开真实单位的网络配置、地址规划、密码、密码哈希或 SNMP 团体字。
- 示例报告与自己的实验结果分开保存，不把解析成功写成“网络已互通”。

## License

[MIT](LICENSE)
