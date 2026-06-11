# 校园网络模拟器 v3.5.0

基于 Mininet 的双校区校园网络模拟项目。系统由 Windows 前端和 WSL/Ubuntu 中的 Mininet 后端组成，通过 HTTP API 联动，重点展示分层校园网、VLAN、ACL、DMZ、边界防火墙、GRE VPN、敏感部门保护和运行观测。

## 核心特性

- 核心、汇聚、接入三层校园网络
- 主校区与第二校区互联
- 多 VLAN 划分及跨 VLAN 路由
- 宿舍、办公、人事、财务、服务器等区域 ACL
- Internet、DMZ、校园内网三安全区
- 独立边界防火墙 `fw1`
- DMZ 校园公网门户与 VPN 接入服务器
- 公网访客 `gst3` 经 GRE VPN 进入内网
- 公网入站、DMZ 横向移动和敏感部门外联控制
- 前后端真实 API 联调
- API 与 Mininet CLI 共用同一个网络实例
- RTT、丢包、抖动、接口吞吐和安全命中实时观测

## 最终架构

```text
外部网站 ext_web ─┐
公网访客 gst3 ────┴─ sw18 公网边界 ─ fw1 边界防火墙 ─ cs1 核心
                                           │                 │
                                           │                 ├─ as1 办公/保密区
                                           │                 ├─ as2 宿舍/生活区
                                           │                 ├─ as3 服务器区
                                           │                 └─ cs2 第二校区
                                           │
                                           └─ sw15 DMZ
                                               ├─ vpn_srv
                                               └─ dmz_web
```

VPN 开启后的完整路径：

```text
gst3 → sw18 → fw1 → sw15 → vpn_srv
     → sw15 → fw1 → cs1 → 校园内网
```

## 快速启动

### Windows 一键启动

推荐直接双击：

```text
run_demo.bat
```

脚本会打开两个窗口：

1. `MininetAPI`：构建网络、运行 API，并提供 `mininet>` 交互终端。
2. `FrontendHTTP`：在 `8000` 端口提供前端页面。

浏览器随后自动打开前端。请保持两个窗口运行。

`MininetAPI` 中可以直接输入：

```text
nodes
net
dA1 ping -c 2 ofc1
ext_web ping -c 2 ofc3
ext_web ping -c 2 dmz_web
sh ovs-ofctl dump-flows fw1
sh iptables -L CAMPUS_EDGE_FILTER -n -v
```

输入 `exit` 会关闭 CLI、API 和当前 Mininet 网络。

### WSL 命令行启动

API 与交互 CLI 并行：

```bash
sudo mn -c
sudo python3 campus_network.py --api
```

只运行 API：

```bash
sudo mn -c
sudo python3 campus_network.py --api-only
```

只运行 Mininet CLI：

```bash
sudo mn -c
sudo python3 campus_network.py
```

指定 API 端口：

```bash
sudo python3 campus_network.py --api --api-port 5001
```

### 仅启动前端

```text
run_frontend.bat
```

或：

```bash
cd frontend
python -m http.server 8000
```

仅启动前端时会使用本地演示逻辑，运行观测指标不会伪造 Mininet 数据。

## 环境要求

- Windows 10/11
- WSL2 与 Ubuntu
- Python 3
- Mininet
- Open vSwitch
- Windows Python，用于前端静态服务器

Ubuntu 中安装基础依赖：

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch
```

## 网络区域

| 区域 | VLAN | 网段 | 说明 |
| --- | ---: | --- | --- |
| 管理网络 | 1 | `10.0.1.0/24` | 网络管理 |
| 宿舍 A | 10 | `10.0.10.0/24` | 学生宿舍 |
| 宿舍 B | 11 | `10.0.11.0/24` | 学生宿舍 |
| 宿舍 C | 12 | `10.0.12.0/24` | 学生宿舍 |
| 食堂 | 13 | `10.0.13.0/24` | 生活区 |
| 办公楼 | 20 | `10.0.20.0/24` | 普通办公 |
| 实验室 | 21 | `10.0.21.0/24` | 教学实验 |
| 图书馆 | 30 | `10.0.30.0/24` | 公共资源 |
| 科研楼 | 40 | `10.0.40.0/24` | 教学科研 |
| 人事处 | 50 | `10.0.50.0/24` | 敏感部门 |
| 财务处 | 60 | `10.0.60.0/24` | 敏感部门 |
| 后勤处 | 70 | `10.0.70.0/24` | 后勤管理 |
| 办公 WiFi | 80 | `10.0.80.0/24` | 无线办公 |
| 隔离访客 WiFi | 90 | `10.0.90.0/24` | `gst1/gst2` 二层隔离岛 |
| 公网 VPN 访客 | 91 | `10.0.91.0/24` | `gst3` |
| 服务器区 | 100 | `10.0.100.0/24` | 内部服务器 |
| DMZ | 110 | `10.0.110.0/24` | 公网门户与 VPN |
| 第二校区 | 200 | `10.1.0.0/24` | `c2h1/c2h2` |
| 模拟 Internet | 250 | `203.0.113.0/24` | 外部网站 |

## 关键节点

| 节点 | 地址 | 位置/用途 |
| --- | --- | --- |
| `fw1` | 无独立主机 IP | 边界防火墙与三层策略入口 |
| `web` | `10.0.100.2` | 内网 HTTP 服务 |
| `ftp` | `10.0.100.3` | 内网 FTP 服务 |
| `dns` | `10.0.100.4` | 内网 DNS 节点 |
| `vpn_srv` | `10.0.110.10` | DMZ VPN 服务器 |
| `dmz_web` | `10.0.110.20` | DMZ 校园公网门户 |
| `ext_web` | `203.0.113.10` | 模拟外部网站 |
| `gst3` | `10.0.91.3` | 公网 VPN 客户端 |

## DMZ 与边界策略

三层网关 trunk 终结在：

```text
vrouter-vr0 ↔ fw1-vr0 ↔ fw1
```

Linux `iptables` 自定义链：

```text
CAMPUS_EDGE_FILTER
```

主要策略：

- 外部网站可以访问 DMZ 校园门户的 HTTP 服务。
- 外部网站可以 Ping DMZ 校园门户。
- 外部网站不能主动访问普通校园内网。
- 内网非敏感区域可以主动访问外部网站。
- 人事、财务不能访问普通外部网站。
- 人事、财务可以访问白名单校园门户。
- DMZ 门户不能主动访问内网，防止失陷后的横向移动。
- 公网不能进入 GRE 隧道网段。

公网 Ping 策略还在 `fw1` 设置 OVS 规则：

```text
priority=641：允许 Internet → dmz_web
priority=640：拒绝 Internet → 其他 10.0.0.0/8 地址
```

## VPN

VPN 使用 GRE 数据面：

| 参数 | 值 |
| --- | --- |
| 隧道设备 | `gre1` |
| 客户端 | `gst3` |
| 服务端 | `vpn_srv` |
| 客户端隧道地址 | `172.16.0.2/30` |
| 服务端隧道地址 | `172.16.0.1/30` |
| GRE key | `42` |

策略：

- VPN 关闭：`gst3 → sw18 → fw1` 后被阻断。
- VPN 开启：内网路由改走 GRE。
- GRE 不可用时 fail-closed，不回退到普通直连。
- VPN 访客可访问普通内网，但不能访问人事、财务。

注意：GRE 用于课程中的隧道数据面演示，不等同于具备加密和身份认证的生产 VPN。

## 校园 ACL

| 源 | 目标 | 结果 |
| --- | --- | --- |
| 宿舍 A/B | 人事、财务 | 拒绝 |
| 人事、财务 | 宿舍 | 允许主动访问 |
| 隔离访客 `gst1/gst2` | 校园内网 | 拒绝 |
| `gst3` 未开 VPN | 校园内网 | 拒绝 |
| `gst3` 开 VPN | 普通内网 | 允许 |
| `gst3` 开 VPN | 人事、财务 | 拒绝 |
| 人事、财务 | 普通外网 | 拒绝 |
| 人事、财务 | DMZ 校园门户 | 白名单允许 |

## 第二校区

主校区与第二校区通过：

```text
cs1 ↔ cs2
```

连接。当前使用普通 Mininet link：

```python
self.addLink(core_sw, cs2)
```

没有人工写死 `delay`、`loss` 或 `bw`。前端展示的 RTT、丢包、抖动和吞吐均来自运行时采样，而不是固定 SLA。

## 网络运行观测

前端“网络运行观测”面板每 8 秒刷新，也支持手动刷新。

### 跨校区质量

通过 `c2h1 → ofc1` 三包 Ping 获取：

- RTT
- 丢包率
- 抖动
- 最近样本趋势

### 接口吞吐

读取 `cs1-cs2` 接口计数器并计算：

- RX/TX Mbps
- RX/TX 包数
- 实际采样间隔
- `tc qdisc` 状态

### DMZ 与安全状态

- 公网 → 校园门户 HTTP 探测
- 公网 → 内网 Web 阻断探测
- 人事 → 白名单门户探测
- VPN 状态
- `cs1/fw1` OVS 流表命中
- `iptables` DROP 计数

接口：

```text
GET /api/observability
GET /api/observability?force=1
GET /api/security-metrics
```

## API

默认地址：

```text
http://localhost:5000
```

主要接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/status` | 后端状态与版本 |
| GET | `/api/ping?src=dA1&dst=ofc1&count=1` | Ping |
| GET | `/api/http?src=dA1&dst=web` | HTTP |
| GET | `/api/ftp?src=dA1&dst=ftp` | FTP |
| GET | `/api/security-metrics` | OVS 与防火墙计数 |
| GET | `/api/observability` | 运行观测 |
| POST | `/api/vpn-sync` | 同步 VPN 开关 |

`POST /api/vpn-sync` 需要请求头：

```text
X-Campus-Token: campus-demo-control-v2
```

## CLI 测试命令

### 基础通信

```text
mininet> nodes
mininet> net
mininet> dA1 ping -c 2 ofc1
mininet> c2h1 ping -c 2 ofc1
mininet> ofc1 curl http://10.0.100.2/
```

### ACL

```text
mininet> dA1 ping -c 2 hr1
mininet> dB1 ping -c 2 fin1
mininet> hr1 ping -c 2 dA1
mininet> gst1 ping -c 2 gst2
mininet> gst1 ping -c 2 ofc1
```

### Internet 与 DMZ

```text
# 内网主动访问外部网站，应成功
mininet> dA1 ping -c 2 ext_web

# 外网主动访问普通内网，应失败
mininet> ext_web ping -c 2 ofc3

# 外网访问公开的 DMZ 门户，应成功
mininet> ext_web ping -c 2 dmz_web
mininet> ext_web curl http://10.0.110.20/

# DMZ 门户横向访问内网，应失败
mininet> dmz_web ping -c 2 ofc1

# 敏感部门访问外网，应失败
mininet> hr1 ping -c 2 ext_web

# 敏感部门访问白名单门户，应成功
mininet> hr1 curl http://10.0.110.20/
```

### VPN

前端 VPN 开关会调用 `/api/vpn-sync`。终端可用于检查状态：

```text
mininet> gst3 ping -c 2 vpn_srv
mininet> gst3 ping -c 2 ofc1
mininet> gst3 ping -c 2 hr1
mininet> gst3 ip route
mininet> gst3 ip -d link show gre1
```

### 安全规则

```text
mininet> sh ovs-ofctl dump-flows fw1
mininet> sh ovs-ofctl dump-flows cs1
mininet> sh iptables -L CAMPUS_EDGE_FILTER -n -v -x
mininet> sh ip route
```

## API 与 CLI 并行

`--api` 模式中，HTTP Server 运行在后台线程，Mininet CLI 运行在前台。因此：

- 浏览器操作与终端命令使用同一套节点和流表。
- 不需要另开第二个 Mininet。
- 前端修改 VPN 状态后，终端可以立即查看路由和 GRE 状态。
- CLI 输入 `exit` 后统一清理 API、iptables、OVS 动态规则和 Mininet。

后端 API 日志默认静默，避免前端轮询打断 `mininet>`。需要调试时：

```bash
sudo CAMPUS_API_VERBOSE=1 python3 campus_network.py --api
```

前端页面中的“API 联调日志”不受该环境变量影响。

## 项目文件

```text
.
├── campus_network.py          # Mininet 拓扑、路由、ACL、DMZ、VPN
├── api_server.py              # HTTP API、VPN 同步、运行观测
├── frontend/
│   ├── index.html             # 演示页面
│   └── js/
│       ├── api.js             # API 客户端
│       ├── topology_data.js   # 拓扑与策略数据
│       ├── topology.js        # D3 拓扑和路径高亮
│       └── treeview.js        # 树状视图
├── run_demo.bat               # Windows 一键启动
├── run_frontend.bat           # 仅启动前端
├── run_mininet.sh             # 仅启动 Mininet CLI
├── start_api.sh               # API + CLI
├── test_topology_logic.js     # 前端拓扑与策略回归测试
├── test_mininet.py            # 基础测试脚本
├── 修改报告-v3.5.0.md         # 完整修改报告
└── README.md
```

## 验证

静态与前端逻辑检查：

```bash
python -m py_compile campus_network.py api_server.py
node --check frontend/js/api.js
node --check frontend/js/topology_data.js
node --check frontend/js/topology.js
node --check frontend/js/treeview.js
node test_topology_logic.js
```

预期：

```text
topology logic regression checks passed
```

## 故障排查

### 后端版本仍是旧版本

必须退出旧的 MininetAPI 窗口并重新运行 `run_demo.bat`。只刷新浏览器不会重新加载 Python 拓扑和防火墙规则。

前端状态应显示：

```text
后端在线 v3.5.0
```

### API 在线但没有 `mininet>` 提示符

确认启动参数是：

```bash
sudo python3 campus_network.py --api
```

`--api-only` 不提供 CLI。

### VPN 返回 503

检查：

```text
mininet> gst3 ping -c 2 vpn_srv
mininet> gst3 ip -d link show gre1
mininet> vpn_srv ip -d link show gre1
```

GRE 不可用时系统会保持 fail-closed。

### 公网仍能访问普通内网

先确认后端已经重启，再检查：

```text
mininet> sh ovs-ofctl dump-flows fw1
mininet> sh iptables -L CAMPUS_EDGE_FILTER -n -v -x
```

应存在公网 ICMP 拒绝规则，且 `ext_web → ofc3` 应失败。

### 清理残留

```bash
sudo mn -c
sudo ip link del fw1-vr0 2>/dev/null || true
sudo ip link del vrouter-vr0 2>/dev/null || true
```

## 版本历史

- `v3.5.0`
  - API 与 Mininet CLI 在同一后端实例中并行运行
  - 增加 `--api-only`
  - 默认静默后台 API 日志
- `v3.4.0`
  - 修复公网 Ping 普通内网
  - 增加 `fw1 ↔ DMZ` 方向箭头
  - 开放公网访问 DMZ 校园门户
- `v3.3.0`
  - `gst3` 迁移到公网边界
  - 三层网关 trunk 迁移到 `fw1`
- `v3.1.0`
  - 增加运行观测 API 与前端面板
- `v3.0.0`
  - 增加 DMZ 门户、Internet 区域和外部网站
- `v2.x`
  - 双校区、基础 VLAN、ACL 和 WSL 兼容

## 说明

项目用于课程演示。当前实现强调架构、策略和可观测性的闭环，不应将 GRE 描述为具备生产级加密认证的完整 VPN，也不应将本机 Mininet 测得的低延迟包装为真实跨城 WAN SLA。
