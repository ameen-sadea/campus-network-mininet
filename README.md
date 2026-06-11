# 校园网络模拟器 - Campus Network Simulator

基于Mininet的校园网络模拟项目，采用分层架构设计（核心层/汇聚层/接入层），实现多区域网络划分、VLAN隔离、ACL访问控制和多种网络服务。

## 前端演示 - 快速启动

前端是纯静态页面，**无需任何构建工具**，直接运行。

### 方式一：双击启动脚本（推荐）

```bash
# Windows: 双击运行
run_frontend.bat
```

### 方式二：命令行启动

```bash
# 进入前端目录
cd frontend

# 启动 Python HTTP 服务器
python -m http.server 8000

# 浏览器打开 http://localhost:8000
```

### 方式三：直接打开 HTML 文件

```bash
# Windows: 双击打开
frontend\index.html
```

> 注意：部分浏览器安全限制可能导致直接打开时某些功能异常，推荐使用方式一或二。

### 技术栈

| 技术 | 说明 |
|------|------|
| Tailwind CSS | 通过 CDN 引入，无需安装 |
| D3.js | 拓扑可视化 |
| Font Awesome | 图标库 |
| 原生 JavaScript | 无框架依赖 |

### 目录结构

```
frontend/
├── index.html          # 主页面
├── css/
│   └── style.css       # 自定义样式
├── js/
│   ├── topology_data.js   # 拓扑配置数据
│   ├── api.js             # API 模拟客户端
│   ├── topology.js        # D3.js 拓扑图渲染
│   └── treeview.js        # 树状结构组件
├── run_frontend.bat    # Windows 启动脚本
└── README.md           # 前端说明
```

## 演示功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 拓扑可视化 | ✓ | D3.js 显示三层网络结构 |
| 树状结构面板 | ✓ | 层级展示各网络区域 |
| Ping 测试 | ✓ | 模拟 ACL 阻断场景 |
| ACL 显示 | ✓ | 高亮被 ACL 拦截的路径 |

### 测试用例

| 源 | 目标 | 预期 | 说明 |
|----|------|------|------|
| dA1 | ofc1 | ✓ 成功 | 跨 VLAN 正常通信 |
| dA1 | hr1 | ✗ 失败 | ACL 阻断：宿舍→人事处 |
| dA1 | fin1 | ✗ 失败 | ACL 阻断：宿舍→财务处 |
| gst1 | ofc1 | ✗ 失败 | ACL 阻断：访客→内网 |
| dA1 | web | ✓ 成功 | 宿舍→服务器（允许） |

## 项目概述

本项目构建了一个完整的校园网络模拟环境，覆盖学生宿舍、办公楼、图书馆、教学楼、人事处、财务处等多个区域。

### 目录结构

```
.
├── campus_network.py      # Mininet 网络定义（需要 Linux/WSL）
├── frontend/              # 前端演示（Windows 直接运行）
│   ├── index.html         # 主页面
│   ├── css/style.css      # 样式
│   └── js/
│       ├── topology_data.js  # 拓扑数据配置
│       ├── api.js           # API 客户端
│       ├── topology.js       # D3.js 拓扑图
│       └── treeview.js       # 树状结构
├── run_frontend.bat       # Windows 启动脚本
└── README.md
```

### 网络区域

| 区域 | VLAN ID | IP网段 | 说明 |
|-----|---------|--------|------|
| 管理网络 | 1 | 10.0.1.0/24 | 网络设备管理 |
| 学生宿舍A区 | 10 | 10.0.10.0/24 | 学生日常上网 |
| 学生宿舍B区 | 11 | 10.0.11.0/24 | 学生宿舍楼B |
| 教学楼 | 40 | 10.0.40.0/24 | 多媒体教学 |
| 办公楼 | 20 | 10.0.20.0/24 | 行政办公 |
| 人事处 | 50 | 10.0.50.0/24 | 机密区域 |
| 财务处 | 60 | 10.0.60.0/24 | 机密区域 |
| 访客无线 | 90 | 10.0.90.0/24 | 访客无线 |
| 服务器区 | 100 | 10.0.100.0/24 | 内部服务器 |

### 服务器清单

| 服务器 | IP地址 | 服务 |
|-------|--------|------|
| web | 10.0.100.2 | HTTP |
| ftp | 10.0.100.3 | FTP |
| dns | 10.0.100.4 | DNS |

## 功能特性

### 1. 分层网络架构

```
核心层 (Core)     → CS1 (核心交换机)
    │
    ├── 汇聚层 (Aggregation)
    │   ├── AS1 (办公区域汇聚)
    │   ├── AS2 (宿舍区域汇聚)
    │   └── AS3 (服务器汇聚)
    │
    └── 接入层 (Access)
        ├── sw1-sw7 (办公区域)
        ├── sw8-sw13 (宿舍区域)
        └── sw14-sw15 (服务器区域)
```

### 2. VLAN二层隔离
- 每个区域独立的VLAN
- 接入交换机端口划分VLAN

### 3. 三层互通 (VLAN间路由)
- 核心交换机作为三层网关
- 各VLAN网关指向核心交换机

### 4. ACL访问控制
- 人事处/财务处: 仅允许特定区域访问
- 学生区域: 禁止访问人事处/财务处
- 访客网络: 完全隔离，无法访问内网

## 网络拓扑

```
                           ┌─────────────────────────────────────┐
                           │           外部网络 (Internet)        │
                           └───────────────────────────────────┘
                                              │
                           ┌─────────────────┴─────────────────┐
                           │        核心交换机 CS1               │
                           │        (VLAN间路由核心)            │
                           └─────────────────┬─────────────────┘
                                             │
              ┌────────────────────────────────┼────────────────────────────────┐
              │                                │                                │
    ┌─────────┴─────────┐           ┌─────────┴─────────┐           ┌─────────┴─────────┐
    │    汇聚交换机AS1   │           │    汇聚交换机AS2   │           │    汇聚交换机AS3   │
    │   (办公区域汇聚)   │           │   (宿舍区域汇聚)   │           │   (服务器汇聚)     │
    └─────────┬─────────┘           └─────────┬─────────┘           └─────────┬─────────┘
              │                                │                                │
    ┌─────────┼─────────┐           ┌─────────┼─────────┐           ┌─────────┼─────────┐
    │         │         │           │         │         │           │         │         │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐   ┌───┴───┐ ┌───┴───┐ ┌───┴───┐   ┌───┴───┐ ┌───┴───┐
│sw1    │ │sw5    │ │sw6    │   │sw8    │ │sw9    │ │sw13   │   │sw14   │ │sw15   │
│(办公) │ │(人事) │ │(财务) │   │(宿舍A)│ │(宿舍B)│ │(访客) │   │(服务器)│ │(DMZ)  │
└───┬───┘ └───┬───┘ └───┬───┘   └───┬───┘ └───┬───┘ └───┬───┘   └───┬───┘ └───┬───┘
    │         │         │           │         │         │           │         │
┌───┴───┐ ┌───┴───┐ ┌───┴───┐   ┌───┴───┐ ┌───┴───┐ ┌───┴───┐   ┌───┴───┐ ┌───┴───┐
│ofc1   │ │hr1    │ │fin1   │   │dA1    │ │dB1    │ │gst1   │   │web    │ │dmz    │
│ofc2   │ │hr2    │ │fin2   │   │dA2    │ │dB2    │ │gst2   │   │ftp    │ │       │
│ofc3   │ │       │ │       │   │dA3    │ │dB3    │ │       │   │dns    │ │       │
└───┴───┘ └───────┘ └───────┘   └───────┘ └───────┘ └───────┘   └───────┘ └───────┘
```

## 环境要求

- Linux环境 (推荐WSL on Windows)
- Mininet 2.3+
- Python 3.8+
- OpenVSwitch 2.17+

## 快速开始

### 1. 安装WSL（Windows用户）

```powershell
wsl --install
```

### 2. 安装Mininet

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch openvswitch-controller
```

### 3. 启动OVS服务

```bash
# 如果OVS数据库未运行，先杀掉旧进程
sudo kill -9 6727 2>/dev/null
sudo rm -f /var/lib/openvswitch/.conf.db.~lock~

# 重新启动OVS数据库
sudo mkdir -p /var/run/openvswitch
sudo ovsdb-server --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --remote=ptcp:6640 --pidfile --detach
sudo ovs-vsctl init
```

### 4. 运行校园网络

```bash
cd /mnt/c/Users/18301/.aa_gcd/gcd/mininet/
sudo python3 campus_network.py
```

## 主机名称

| 区域 | 主机名 | IP地址 | VLAN |
|-----|--------|--------|------|
| 教学楼 | acd1, acd2, acd3 | 10.0.40.3-5 | 40 |
| 办公楼 | ofc1, ofc2, ofc3 | 10.0.20.3-5 | 20 |
| 宿舍A | dA1, dA2, dA3 | 10.0.10.3-5 | 10 |
| 宿舍B | dB1, dB2, dB3 | 10.0.11.3-5 | 11 |
| 人事处 | hr1, hr2 | 10.0.50.3-4 | 50 |
| 财务处 | fin1, fin2 | 10.0.60.3-4 | 60 |
| 访客 | gst1, gst2 | 10.0.90.3-4 | 90 |
| Web服务器 | web | 10.0.100.2 | 100 |
| FTP服务器 | ftp | 10.0.100.3 | 100 |
| DNS服务器 | dns | 10.0.100.4 | 100 |

## 测试命令

### 连通性测试

```bash
# 同VLAN内通信 (二层)
mininet> dA1 ping dA2

# 跨VLAN通信 (三层)
mininet> dA1 ping ofc1
mininet> dA1 ping web

# 服务器访问
mininet> ofc1 ping web
mininet> dA1 ping dns
```

### ACL测试

```bash
# 应失败的访问 (被ACL拦截)
mininet> dA1 ping hr1       # 学生宿舍A → 人事处 (拒绝)
mininet> dB1 ping fin1      # 学生宿舍B → 财务处 (拒绝)
mininet> gst1 ping ofc1     # 访客 → 办公楼 (拒绝)
mininet> gst1 ping web      # 访客 → 服务器 (拒绝)

# 应成功的访问
mininet> ofc1 ping hr1      # 办公楼 → 人事处 (放行)
mininet> ofc1 ping fin1     # 办公楼 → 财务处 (放行)
mininet> dA1 ping web       # 宿舍 → Web服务器
```

### CLI其他命令

```bash
# 查看所有节点
mininet> nodes

# 查看网络连接
mininet> net

# 查看节点详细信息
mininet> dump

# 打开xterm终端
mininet> xterm dA1 ofc1

# 退出CLI
mininet> exit
```

## 交换机列表

| 交换机 | 类型 | 说明 |
|-------|------|------|
| cs1 | 核心 | 全网核心交换机 |
| as1 | 汇聚 | 办公区域汇聚 |
| as2 | 汇聚 | 宿舍区域汇聚 |
| as3 | 汇聚 | 服务器区域汇聚 |
| sw1 | 接入 | 办公楼 (VLAN 20) |
| sw2 | 接入 | 科研楼 (VLAN 21) |
| sw3 | 接入 | 图书馆 (VLAN 30) |
| sw4 | 接入 | 教学楼 (VLAN 40) |
| sw5 | 接入 | 人事处 (VLAN 50) |
| sw6 | 接入 | 财务处 (VLAN 60) |
| sw7 | 接入 | 后勤 (VLAN 70) |
| sw8 | 接入 | 宿舍A (VLAN 10) |
| sw9 | 接入 | 宿舍B (VLAN 11) |
| sw10 | 接入 | 宿舍C (VLAN 12) |
| sw11 | 接入 | 食堂 (VLAN 13) |
| sw12 | 接入 | 无线办公 (VLAN 80) |
| sw13 | 接入 | 访客无线 (VLAN 90) |
| sw14 | 接入 | 服务器 (VLAN 100) |
| sw15 | 接入 | DMZ (VLAN 110) |

## ACL规则

| 规则ID | 源网络 | 目标网络 | 动作 | 说明 |
|-------|--------|---------|------|------|
| 100 | 10.0.10.0/24 | 10.0.50.0/24 | drop | 宿舍A→人事处 |
| 101 | 10.0.11.0/24 | 10.0.50.0/24 | drop | 宿舍B→人事处 |
| 102 | 10.0.10.0/24 | 10.0.60.0/24 | drop | 宿舍A→财务处 |
| 103 | 10.0.11.0/24 | 10.0.60.0/24 | drop | 宿舍B→财务处 |
| 104 | 10.0.90.0/24 | 10.0.0.0/8 | drop | 访客→内网 |
| 200 | 任意 | 任意 | normal | 默认放行 |

## 网络规模

| 设备类型 | 数量 |
|---------|------|
| 核心交换机 | 1 (cs1) |
| 汇聚交换机 | 3 (as1, as2, as3) |
| 接入交换机 | 15 (sw1-sw15) |
| 主机 | 21 |
| 服务器 | 3 |

## 扩展指南

### 添加新主机

编辑 `HOSTS` 列表：

```python
HOSTS.append({'name': 'newhost', 'ip': '10.0.20.10', 'vlan': 20, 'gw': '10.0.20.1'})
```

### 修改ACL规则

编辑 `_setup_acl()` 方法中的规则：

```python
rules = [
    ('100', '10.0.10.0/24', '10.0.50.0/24', 'drop'),
    # 添加新规则...
]
```

## 故障排查

### OVS数据库未运行

```
Error connecting to ovs-db with ovs-vsctl
ovsdb-server: database connection failed
```

**解决：**

```bash
# 杀掉旧进程
sudo kill -9 6727 2>/dev/null
sudo rm -f /var/lib/openvswitch/.conf.db.~lock~

# 重新启动OVS
sudo mkdir -p /var/run/openvswitch
sudo ovsdb-server --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --remote=ptcp:6640 --pidfile --detach
sudo ovs-vsctl init

# 运行校园网络
sudo python3 campus_network.py
```

### 常见问题

```bash
# 清理残留
sudo mn -c

# 检查交换机状态
sudo ovs-vsctl show

# 检查流表
sudo ovs-ofctl dump-flows cs1

# 检查主机IP
mininet> dA1 ip addr show
```

### 连通性测试失败

如果ping不通，先测试到网关：

```bash
mininet> dA1 ping 10.0.10.1
```

如果网关也ping不通，检查VLAN配置：

```bash
mininet> sh sudo ovs-vsctl list interface | grep -i vlan
```

## 文件结构

```
campus_network/
├── README.md               # 项目说明文档
├── campus_network.py       # 主程序
└── test_mininet.py        # 测试脚本
```

## 版本历史

- **v2.0** (2026-04-20) - WSL兼容版
  - 缩短交换机/主机名称以满足WSL接口名限制
  - 简化网络拓扑
  - 分层架构: 核心/汇聚/接入
  - ACL访问控制
  - 无需外部控制器

- **v1.0** (2026-04-20) - 基础版本
  - 基础VLAN划分
  - 基础ACL控制
