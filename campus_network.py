#!/usr/bin/env python
"""
校园网络模拟器 - Campus Network Simulator v3.4.0
分校区 cs2 / 访客 VPN（gst3 经 sw16 直连 cs1，vpn_srv 挂 DMZ sw15）
"""
from mininet.cli import CLI
from mininet.clean import cleanup
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.node import Controller, Switch, OVSKernelSwitch, Node as MininetNode
from mininet.topo import Topo
from mininet.util import quietRun

# =============================================================================
# 网络配置 - 缩短名称以满足WSL接口名限制(≤15字符)
# =============================================================================

VLAN_CONFIG = {
    'mgmt':      {'id': 1,   'network': '10.0.1.0/24',   'gateway': '10.0.1.1'},
    'dormA':     {'id': 10,  'network': '10.0.10.0/24', 'gateway': '10.0.10.1'},
    'dormB':     {'id': 11,  'network': '10.0.11.0/24', 'gateway': '10.0.11.1'},
    'dormC':     {'id': 12,  'network': '10.0.12.0/24', 'gateway': '10.0.12.1'},
    'canteen':   {'id': 13,  'network': '10.0.13.0/24', 'gateway': '10.0.13.1'},
    'office':    {'id': 20,  'network': '10.0.20.0/24', 'gateway': '10.0.20.1'},
    'lab':       {'id': 21,  'network': '10.0.21.0/24', 'gateway': '10.0.21.1'},
    'library':   {'id': 30,  'network': '10.0.30.0/24', 'gateway': '10.0.30.1'},
    'academic':  {'id': 40,  'network': '10.0.40.0/24', 'gateway': '10.0.40.1'},
    'hr':        {'id': 50,  'network': '10.0.50.0/24', 'gateway': '10.0.50.1', 'secure': True},
    'finance':   {'id': 60,  'network': '10.0.60.0/24', 'gateway': '10.0.60.1', 'secure': True},
    'logistics': {'id': 70,  'network': '10.0.70.0/24', 'gateway': '10.0.70.1'},
    'wifiOfc':   {'id': 80,  'network': '10.0.80.0/24', 'gateway': '10.0.80.1'},
    'wifiGst':   {'id': 90,  'network': '10.0.90.0/24', 'gateway': '10.0.90.1'},
    'guestCampus': {'id': 91, 'network': '10.0.91.0/24', 'gateway': '10.0.91.1'},
    'server':    {'id': 100, 'network': '10.0.100.0/24', 'gateway': '10.0.100.1'},
    'dmz':       {'id': 110, 'network': '10.0.110.0/24', 'gateway': '10.0.110.1'},
    'campus2':   {'id': 200, 'network': '10.1.0.0/24',   'gateway': '10.1.0.1',  'campus': 2},
    'internet':  {'id': 250, 'network': '203.0.113.0/24', 'gateway': '203.0.113.1', 'external': True},
}

# VPN 隧道配置（校园访客 gst3，连上后权限等同宿舍；gst1/gst2 为隔离 WiFi）
VPN_CONFIG = {
    'server': {'host': 'vpn_srv', 'ip': '10.0.110.10'},
    'client': {
        'host': 'gst3', 'ip': '10.0.91.3', 'gw': '10.0.91.1', 'tunnel_dev': 'gre1',
        'tunnel_ip': '172.16.0.2', 'server_tun_ip': '172.16.0.1',
    },
    'tunnel_net': '172.16.0.0/30',
    'mode': 'gre',
    'routes': ['10.0.0.0/8'],
}

# 应用层服务配置
SERVICE_CONFIG = {
    'web': {'host': 'web', 'port': 80,  'protocol': 'http', 'root': '/tmp/www'},
    'ftp': {'host': 'ftp', 'port': 21,  'protocol': 'ftp',  'root': '/tmp/ftp'},
    'dmz_web': {'host': 'dmz_web', 'port': 80, 'protocol': 'http', 'root': '/tmp/dmz-www'},
    'ext_web': {'host': 'ext_web', 'port': 80, 'protocol': 'http', 'root': '/tmp/ext-www'},
}

# 交换机配置 (名称≤14字符)
SWITCHES = {
    'cs1': {'type': 'core', 'campus': 1, 'vlans': [k for k in VLAN_CONFIG if k != 'campus2']},
    'cs2': {'type': 'core', 'campus': 2, 'vlans': ['campus2']},
    'fw1': {'type': 'firewall', 'campus': 1, 'vlans': ['internet', 'dmz']},
    'as1': {'type': 'agg', 'campus': 1, 'vlans': ['office', 'lab', 'library', 'academic', 'hr', 'finance', 'logistics']},
    'as2': {'type': 'agg', 'campus': 1, 'vlans': ['dormA', 'dormB', 'dormC', 'canteen', 'wifiOfc']},
    'as3': {'type': 'agg', 'campus': 1, 'vlans': ['server', 'mgmt']},
    'as4': {'type': 'agg', 'campus': 2, 'vlans': ['campus2']},
}

# 接入交换机配置
ACCESS_SW = {
    'sw1': {'vlan': 'office', 'agg': 'as1'},
    'sw2': {'vlan': 'lab', 'agg': 'as1'},
    'sw3': {'vlan': 'library', 'agg': 'as1'},
    'sw4': {'vlan': 'academic', 'agg': 'as1'},
    'sw5': {'vlan': 'hr', 'agg': 'as1', 'secure': True},
    'sw6': {'vlan': 'finance', 'agg': 'as1', 'secure': True},
    'sw7': {'vlan': 'logistics', 'agg': 'as1'},
    'sw8': {'vlan': 'dormA', 'agg': 'as2'},
    'sw9': {'vlan': 'dormB', 'agg': 'as2'},
    'sw10': {'vlan': 'dormC', 'agg': 'as2'},
    'sw11': {'vlan': 'canteen', 'agg': 'as2'},
    'sw12': {'vlan': 'wifiOfc', 'agg': 'as2'},
    'sw13': {'vlan': 'wifiGst', 'isolated': True},
    'sw14': {'vlan': 'server', 'agg': 'as3'},
    'sw15': {'vlan': 'dmz', 'agg': 'fw1'},
    'sw16': {'vlan': 'guestCampus', 'isolated': True},
    'sw17': {'vlan': 'campus2', 'agg': 'as4'},
    'sw18': {'vlan': 'internet', 'agg': 'fw1'},
}

# 主机配置
HOSTS = []
base = 2

# 办公楼
for i in range(1, 4):
    HOSTS.append({'name': f'ofc{i}', 'ip': f'10.0.20.{base+i}/24', 'vlan': 20, 'gw': '10.0.20.1'})
# 教学楼
for i in range(1, 4):
    HOSTS.append({'name': f'acd{i}', 'ip': f'10.0.40.{base+i}/24', 'vlan': 40, 'gw': '10.0.40.1'})
# 宿舍A
for i in range(1, 4):
    HOSTS.append({'name': f'dA{i}', 'ip': f'10.0.10.{base+i}/24', 'vlan': 10, 'gw': '10.0.10.1'})
# 宿舍B
for i in range(1, 4):
    HOSTS.append({'name': f'dB{i}', 'ip': f'10.0.11.{base+i}/24', 'vlan': 11, 'gw': '10.0.11.1'})
# 人事处
for i in range(1, 3):
    HOSTS.append({'name': f'hr{i}', 'ip': f'10.0.50.{base+i}/24', 'vlan': 50, 'gw': '10.0.50.1'})
# 财务处
for i in range(1, 3):
    HOSTS.append({'name': f'fin{i}', 'ip': f'10.0.60.{base+i}/24', 'vlan': 60, 'gw': '10.0.60.1'})
# 访客 WiFi 隔离网（gst1/gst2 同交换机二层互访，sw13 无上联）
for i in range(1, 3):
    HOSTS.append({
        'name': f'gst{i}', 'ip': f'10.0.90.{base+i}/24', 'vlan': 90,
        'gw': '10.0.90.1', 'wifi_island': True,
    })
# 校园访客（接核心，VPN 客户端）
HOSTS.append({'name': 'gst3', 'ip': f'10.0.91.{base+1}/24', 'vlan': 91, 'gw': '10.0.91.1', 'vpn_client': True})
# 校区2 (分校区)
for i in range(1, 3):
    HOSTS.append({'name': f'c2h{i}', 'ip': f'10.1.0.{base+i}/24', 'vlan': 200, 'gw': '10.1.0.1', 'campus': 2})
# 全部终端（供端口识别）
ALL_TERMINALS = HOSTS
# 服务器（需要defaultRoute才能跨VLAN通信）
SRV_HOSTS = [
    {'name': 'web', 'ip': '10.0.100.2/24', 'vlan': 100, 'gw': '10.0.100.1', 'service': 'http'},
    {'name': 'ftp', 'ip': '10.0.100.3/24', 'vlan': 100, 'gw': '10.0.100.1', 'service': 'ftp'},
    {'name': 'dns', 'ip': '10.0.100.4/24', 'vlan': 100, 'gw': '10.0.100.1'},
    {'name': 'vpn_srv', 'ip': '10.0.110.10/24', 'vlan': 110, 'gw': '10.0.110.1', 'vpn': True},
    {
        'name': 'dmz_web', 'ip': '10.0.110.20/24', 'vlan': 110,
        'gw': '10.0.110.1', 'service': 'dmz_http',
    },
    {
        'name': 'ext_web', 'ip': '203.0.113.10/24', 'vlan': 250,
        'gw': '203.0.113.1', 'service': 'external_http',
    },
]

# 内置简易 FTP 服务脚本（stdlib，无额外依赖）
FTP_SERVER_PY = r'''#!/usr/bin/env python3
import os, socket, threading
ROOT = "/tmp/ftp"
def handle(conn):
    conn.send(b"220 Campus FTP Ready\r\n")
    buf = b""
    while True:
        data = conn.recv(1024)
        if not data:
            break
        buf += data
        if b"\r\n" not in buf:
            continue
        line, buf = buf.split(b"\r\n", 1)
        cmd = line.decode(errors="ignore").strip()
        upper = cmd.upper()
        if upper.startswith("USER") or upper.startswith("PASS"):
            conn.send(b"230 Login OK\r\n")
        elif upper.startswith("SYST"):
            conn.send(b"215 UNIX Type: L8\r\n")
        elif upper.startswith("TYPE"):
            conn.send(b"200 Type set\r\n")
        elif upper.startswith("PWD"):
            conn.send(b'257 "/"\r\n')
        elif upper.startswith("LIST") or upper.startswith("NLST"):
            files = os.listdir(ROOT)
            body = "".join(f"-rw-r--r-- 1 root root 0 Jan  1 00:00 {f}\r\n" for f in files)
            conn.send(b"150 Opening ASCII mode data connection\r\n")
            conn.send(body.encode())
            conn.send(b"226 Transfer complete\r\n")
        elif upper.startswith("RETR"):
            fn = cmd.split()[1] if len(cmd.split()) > 1 else ""
            path = os.path.join(ROOT, os.path.basename(fn))
            if os.path.isfile(path):
                conn.send(b"150 Opening BINARY mode data connection\r\n")
                with open(path, "rb") as f:
                    conn.send(f.read())
                conn.send(b"\r\n226 Transfer complete\r\n")
            else:
                conn.send(b"550 File not found\r\n")
        elif upper.startswith("QUIT"):
            conn.send(b"221 Goodbye\r\n")
            break
        else:
            conn.send(b"200 OK\r\n")
    conn.close()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 21))
s.listen(8)
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
'''

EDGE_FILTER_CHAIN = 'CAMPUS_EDGE_FILTER'


class CampusTopo(Topo):
    def __init__(self):
        super(CampusTopo, self).__init__()

        info("=== 构建校园网络拓扑 ===\n")

        # 创建核心/汇聚交换机
        info("创建核心/汇聚交换机...\n")
        core_sw = self.addSwitch('cs1', cls=OVSKernelSwitch)
        cs2 = self.addSwitch('cs2', cls=OVSKernelSwitch)
        edge_fw = self.addSwitch('fw1', cls=OVSKernelSwitch)
        as1 = self.addSwitch('as1', cls=OVSKernelSwitch)
        as2 = self.addSwitch('as2', cls=OVSKernelSwitch)
        as3 = self.addSwitch('as3', cls=OVSKernelSwitch)
        as4 = self.addSwitch('as4', cls=OVSKernelSwitch)

        # 创建接入交换机
        info("创建接入交换机...\n")
        access_sws = {}
        for sw_name, sw_config in ACCESS_SW.items():
            s = self.addSwitch(sw_name, cls=OVSKernelSwitch)
            access_sws[sw_name] = s
            vlan_name = sw_config['vlan']
            info(f"  {sw_name} -> VLAN {VLAN_CONFIG[vlan_name]['id']} ({vlan_name})\n")

        # 创建主机
        info("创建主机...\n")
        host_nodes = {}
        for h in HOSTS:
            node = self.addHost(h['name'], ip=h['ip'], defaultRoute=f"via {h['gw']}")
            host_nodes[h['name']] = node
            info(f"  {h['name']} -> {h['ip']}\n")

        # 创建服务器
        info("创建服务器...\n")
        srv_nodes = {}
        for s in SRV_HOSTS:
            node = self.addHost(s['name'], ip=s['ip'], defaultRoute=f"via {s['gw']}")
            srv_nodes[s['name']] = node
            info(f"  {s['name']} -> {s['ip']}\n")

        # 创建链路 - 核心到汇聚 + 校区间专线
        info("创建链路 (核心-汇聚 / 校区间)...\n")
        self.addLink(core_sw, as1)
        self.addLink(core_sw, as2)
        self.addLink(core_sw, as3)
        self.addLink(core_sw, edge_fw)
        self.addLink(core_sw, cs2)
        info("  cs1 <-> cs2 (校区间专线)\n")
        self.addLink(cs2, as4)

        # 创建链路 - 汇聚/核心到接入
        info("创建链路 (汇聚/核心-接入)...\n")
        for sw_name, sw_config in ACCESS_SW.items():
            if sw_config.get('isolated'):
                info(f"  {sw_name}: 访客WiFi隔离（无上联，仅互访）\n")
                continue
            agg_sw = sw_config['agg']
            if sw_config.get('direct_core'):
                self.addLink(core_sw, access_sws[sw_name])
                info(f"  cs1 <-> {sw_name} (直连)\n")
            elif agg_sw == 'as1':
                self.addLink(as1, access_sws[sw_name])
                info(f"  {agg_sw} <-> {sw_name}\n")
            elif agg_sw == 'as2':
                self.addLink(as2, access_sws[sw_name])
                info(f"  {agg_sw} <-> {sw_name}\n")
            elif agg_sw == 'as3':
                self.addLink(as3, access_sws[sw_name])
                info(f"  {agg_sw} <-> {sw_name}\n")
            elif agg_sw == 'fw1':
                self.addLink(edge_fw, access_sws[sw_name])
                info(f"  fw1 <-> {sw_name} (edge security zone)\n")
            elif agg_sw == 'as4':
                self.addLink(as4, access_sws[sw_name])
                info(f"  {agg_sw} <-> {sw_name}\n")

        # 创建链路 - 主机到接入交换机
        info("创建链路 (主机-接入)...\n")
        vlan_to_sw = {}
        for sw_name, sw_config in ACCESS_SW.items():
            vlan_to_sw[sw_config['vlan']] = sw_name
        # gst3 校园访客接 sw16；VPN 服务端位于 sw15/DMZ
        # gst3 is an external VPN client and enters through the Internet edge.
        vlan_to_sw['guestCampus'] = 'sw18'

        for h in HOSTS:
            vlan_name = None
            for vn, vc in VLAN_CONFIG.items():
                if vc['id'] == h['vlan']:
                    vlan_name = vn
                    break
            if vlan_name and vlan_name in vlan_to_sw:
                sw_name = vlan_to_sw[vlan_name]
                self.addLink(host_nodes[h['name']], access_sws[sw_name])

        # 创建链路 - 服务器到接入交换机
        info("创建链路 (服务器-接入)...\n")
        for s in SRV_HOSTS:
            vlan_name = None
            for vn, vc in VLAN_CONFIG.items():
                if vc['id'] == s['vlan']:
                    vlan_name = vn
                    break
            if vlan_name and vlan_name in vlan_to_sw:
                sw_name = vlan_to_sw[vlan_name]
                self.addLink(srv_nodes[s['name']], access_sws[sw_name])

        info("\n=== 拓扑构建完成 ===\n")


class CampusNetwork:
    def __init__(self):
        self.net = None
        self.vrouter = None
        self.vpn_ready = False
        self.vpn_mode = 'off'

    def _cleanup_stale(self):
        """上次异常退出后清理 Mininet 残留接口，避免 File exists"""
        import subprocess

        info(">> 清理上次残留...\n")
        try:
            from api_server import clear_ovs_vpn_acl, clear_root_vpn_nat
            clear_root_vpn_nat()
            self._clear_edge_firewall()
            if self.net:
                clear_ovs_vpn_acl(self.net)
        except Exception:
            pass

        cleanup()
        subprocess.run('mn -c 2>/dev/null; true', shell=True)
        subprocess.run(
            'ip link del cs1-vr0 2>/dev/null; ip link del fw1-vr0 2>/dev/null; '
            'ip link del vrouter-vr0 2>/dev/null; true',
            shell=True,
        )
        for vid in [v['id'] for v in VLAN_CONFIG.values()]:
            subprocess.run(f'ip link del vrouter-vr0.{vid} 2>/dev/null; true', shell=True)

    def build(self):
        info("="*60 + "\n")
        info("  校园网络构建系统 v3.4.0 (Directional Firewall/DMZ/VPN)")
        info("="*60 + "\n\n")

        self._cleanup_stale()

        topo = CampusTopo()

        info(">> 启动网络...\n")
        self.net = Mininet(
            topo=topo,
            switch=OVSKernelSwitch,
            controller=None
        )

        info(">> 启动Mininet...\n")
        self.net.start()

        # 配置交换机为独立模式
        info(">> 配置交换机为独立模式...\n")
        for sw in self.net.switches:
            sw.cmd('ovs-vsctl set-fail-mode', sw, 'standalone')
            sw.cmd('ip link set', sw, 'up')

        # 配置接入端口VLAN
        info(">> 配置接入端口VLAN...\n")
        self._setup_access_ports()

        # 配置三层路由
        info(">> 配置三层路由（vrouter节点）...\n")
        self._setup_router()

        info(">> 配置边界状态防火墙...\n")
        self._setup_edge_firewall()

        # 配置ACL
        info(">> 配置ACL...\n")
        self._setup_acl()

        # 配置应用层服务 (Web/FTP)
        info(">> 配置应用层服务...\n")
        self._setup_services()

        # 配置 VPN 隧道
        info(">> 配置 VPN 隧道...\n")
        self._setup_vpn()

        info("\n" + "="*60 + "\n")
        info("  校园网络构建完成!")
        info("="*60 + "\n")

        return self.net

    def _setup_access_ports(self):
        """配置接入端口VLAN + 明确配置所有trunk端口允许所有VLAN"""
        all_vlans = ','.join(str(v['id']) for v in VLAN_CONFIG.values())

        for sw in self.net.switches:
            sw_name = sw.name
            for intf in sw.intfList():
                if not intf.link:
                    continue
                port_name = intf.name
                # 跳过回路端口
                if port_name == 'lo':
                    continue
                # 判断是主机端口还是交换机间端口
                intf1_node = intf.link.intf1.node.name if intf.link.intf1 else None
                intf2_node = intf.link.intf2.node.name if intf.link.intf2 else None

                is_host_port = (intf1_node in [h['name'] for h in ALL_TERMINALS] or
                                intf2_node in [h['name'] for h in ALL_TERMINALS] or
                                intf1_node in [s['name'] for s in SRV_HOSTS] or
                                intf2_node in [s['name'] for s in SRV_HOSTS])

                if is_host_port:
                    # 接入端口：配置VLAN tag
                    vlan_id = None
                    host_name = None
                    for h in ALL_TERMINALS:
                        if intf1_node == h['name'] or intf2_node == h['name']:
                            vlan_id = h['vlan']
                            host_name = h['name']
                            break
                    if vlan_id is None:
                        for s in SRV_HOSTS:
                            if intf1_node == s['name'] or intf2_node == s['name']:
                                vlan_id = s['vlan']
                                host_name = s['name']
                                break
                    if vlan_id is not None:
                        sw.cmd(f'ovs-vsctl set port {port_name} tag={vlan_id}')
                        info(f"  {port_name}: access VLAN {vlan_id}\n")
                else:
                    # 交换机间trunk端口：明确允许所有VLAN
                    sw.cmd(f'ovs-vsctl set port {port_name} trunks={all_vlans}')
                    info(f"  {port_name}: trunk allowed={all_vlans}\n")

    def _setup_router(self):
        """配置vrouter：所有网络配置在 root namespace 通过 subprocess 执行"""
        import subprocess

        info("  配置 vrouter 网络（root namespace）...\n")

        all_vlans = ','.join(str(v['id']) for v in VLAN_CONFIG.values())

        # 清理旧接口
        def run(cmd):
            subprocess.run(cmd, shell=True)

        run(
            'ip link del cs1-vr0 2>/dev/null; ip link del fw1-vr0 2>/dev/null; '
            'ip link del vrouter-vr0 2>/dev/null; true'
        )
        for vid in [v['id'] for v in VLAN_CONFIG.values()]:
            run(f'ip link del vrouter-vr0.{vid} 2>/dev/null; true')

        # 创建 veth pair（两端都在 root namespace）
        run('ip link add vrouter-vr0 type veth peer name fw1-vr0')
        run('ip link set vrouter-vr0 up')
        info("  created veth pair (root ns)\n")

        # 在 vrouter-vr0 上创建 VLAN sub-interfaces 并配置网关 IP
        info("  配置 VLAN sub-interfaces:\n")
        for vlan_name, config in VLAN_CONFIG.items():
            vid = config['id']
            gw = config['gateway']
            run(f'ip link add link vrouter-vr0 name vrouter-vr0.{vid} type vlan id {vid}')
            run(f'ip addr add {gw}/24 dev vrouter-vr0.{vid}')
            run(f'ip link set vrouter-vr0.{vid} up')
            info(f"    vlan{vid} ({vlan_name}): {gw}\n")

        # 启用 IP 转发
        run('sysctl -w net.ipv4.ip_forward=1')
        info("  IP forwarding enabled\n")

        # cs1 端：添加 trunk port（用 os.system 确保在 root ns）
        import os
        os.system('ip link set fw1-vr0 up')
        os.system(f'ovs-vsctl add-port fw1 fw1-vr0')
        os.system(f'ovs-vsctl set port fw1-vr0 trunks={all_vlans}')
        info(f"  fw1-vr0: routed firewall trunk vlans={all_vlans}\n")

        # 保存 vrouter 引用（用于后续 CLI 命令）
        self.vrouter = None  # 不再需要 vrouter 节点，所有命令在 root 执行

    def _clear_edge_firewall(self):
        import subprocess

        subprocess.run(
            f'while iptables -D FORWARD -j {EDGE_FILTER_CHAIN} 2>/dev/null; do :; done; '
            f'iptables -F {EDGE_FILTER_CHAIN} 2>/dev/null; '
            f'iptables -X {EDGE_FILTER_CHAIN} 2>/dev/null; true',
            shell=True,
        )

    def _setup_edge_firewall(self):
        """Stateful perimeter policy for Internet and compromised DMZ services."""
        import subprocess

        self._clear_edge_firewall()
        commands = [
            f'iptables -N {EDGE_FILTER_CHAIN}',
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 203.0.113.0/24 '
                '-d 10.0.110.20/32 -p icmp --icmp-type echo-request -j ACCEPT'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 203.0.113.0/24 '
                '-d 10.0.0.0/8 -p icmp --icmp-type echo-request -j DROP'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -m conntrack '
                '--ctstate ESTABLISHED,RELATED -j ACCEPT'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 10.0.91.0/24 '
                '-d 10.0.110.10/32 -j ACCEPT'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 10.0.91.0/24 '
                '-d 10.0.110.20/32 -j ACCEPT'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 10.0.91.0/24 '
                '-d 10.0.0.0/8 -m conntrack --ctstate NEW -j DROP'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 203.0.113.0/24 '
                '-d 10.0.110.20/32 -p tcp --dport 80 '
                '-m conntrack --ctstate NEW -j ACCEPT'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 203.0.113.0/24 '
                '-d 10.0.0.0/8 -m conntrack --ctstate NEW -j DROP'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 203.0.113.0/24 '
                '-d 172.16.0.0/30 -m conntrack --ctstate NEW -j DROP'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 10.0.110.20/32 '
                '-d 10.0.0.0/8 -m conntrack --ctstate NEW -j DROP'
            ),
            (
                f'iptables -A {EDGE_FILTER_CHAIN} -s 10.0.110.20/32 '
                '-d 172.16.0.0/30 -m conntrack --ctstate NEW -j DROP'
            ),
            f'iptables -A {EDGE_FILTER_CHAIN} -j RETURN',
            f'iptables -I FORWARD 1 -j {EDGE_FILTER_CHAIN}',
        ]
        for command in commands:
            subprocess.run(command, shell=True, check=False)
        info("  conntrack: allow ESTABLISHED/RELATED; deny new Internet/DMZ -> internal\n")

    def _setup_acl(self):
        """配置访问控制"""
        cs1 = self.net.get('cs1')

        # ACL规则：优先级600-607，高于路由规则的500
        rules = [
            # 允许人事/财务主动访问宿舍后的 ICMP 回包，不开放宿舍主动访问
            ('626', '10.0.10.0/24', '10.0.50.0/24', 'normal', 'icmp,icmp_type=0'),
            ('626', '10.0.11.0/24', '10.0.50.0/24', 'normal', 'icmp,icmp_type=0'),
            ('626', '10.0.10.0/24', '10.0.60.0/24', 'normal', 'icmp,icmp_type=0'),
            ('626', '10.0.11.0/24', '10.0.60.0/24', 'normal', 'icmp,icmp_type=0'),
            # VPN 隧道 → 敏感区（拒绝，等同宿舍权限）
            ('615', '172.16.0.0/30', '10.0.50.0/24', 'drop', 'ip'),
            ('614', '172.16.0.0/30', '10.0.60.0/24', 'drop', 'ip'),
            # VPN 隧道 → 内网（放行）
            ('608', '172.16.0.0/30', '10.0.0.0/8', 'normal', 'ip'),
            # 校园访客可访问 DMZ 的 VPN 接入点与校园公网门户
            ('623', '10.0.91.0/24', '10.0.110.10/32', 'normal', 'ip'),
            ('623', '10.0.91.0/24', '10.0.110.20/32', 'normal', 'ip'),
            # Sensitive departments may reach only the trusted campus portal.
            ('629', '10.0.50.0/24', '10.0.110.20/32', 'normal', 'ip'),
            ('629', '10.0.60.0/24', '10.0.110.20/32', 'normal', 'ip'),
            # 宿舍A/B → 人事处/财务处（drop）
            ('607', '10.0.10.0/24', '10.0.50.0/24', 'drop', 'ip'),
            ('606', '10.0.11.0/24', '10.0.50.0/24', 'drop', 'ip'),
            ('605', '10.0.10.0/24', '10.0.60.0/24', 'drop', 'ip'),
            ('604', '10.0.11.0/24', '10.0.60.0/24', 'drop', 'ip'),
            # 校园访客 gst3 未连 VPN → 内网（drop）
            ('603', '10.0.91.0/24', '10.0.0.0/8', 'drop', 'ip'),
            # 人事/财务 → DMZ（含 VPN 服务器，保密区禁止外出连边界服务）
            ('612', '10.0.50.0/24', '10.0.110.0/24', 'drop', 'ip'),
            ('613', '10.0.60.0/24', '10.0.110.0/24', 'drop', 'ip'),
            # 人事/财务 → 模拟外网（禁止上外网）
            ('616', '10.0.50.0/24', '203.0.113.0/24', 'drop', 'ip'),
            ('617', '10.0.60.0/24', '203.0.113.0/24', 'drop', 'ip'),
            # 人事/财务 → VPN 隧道网段
            ('618', '10.0.50.0/24', '172.16.0.0/30', 'drop', 'ip'),
            ('619', '10.0.60.0/24', '172.16.0.0/30', 'drop', 'ip'),
            # 宿舍区 → 办公/教学服务器区（仅允许到server VLAN 100）
            ('602', '10.0.10.0/24', '10.0.100.0/24', 'normal', 'ip'),
            ('602', '10.0.11.0/24', '10.0.100.0/24', 'normal', 'ip'),
            # 默认放行
            ('1', '0.0.0.0/0', '0.0.0.0/0', 'normal', 'ip'),
        ]

        for priority, src, dst, action, match in rules:
            cmd = f'ovs-ofctl add-flow cs1 "priority={priority},{match},nw_src={src},nw_dst={dst},actions={action}"'
            cs1.cmd(cmd)
            info(f"  ACL: {src} -> {dst} [{action}]\n")

        # Enforce the public-to-campus ping boundary at fw1 before routing.
        fw1 = self.net.get('fw1')
        fw1.cmd(
            'ovs-ofctl add-flow fw1 '
            '"priority=641,icmp,nw_src=203.0.113.0/24,nw_dst=10.0.110.20/32,'
            'icmp_type=8,actions=normal"'
        )
        fw1.cmd(
            'ovs-ofctl add-flow fw1 '
            '"priority=640,icmp,nw_src=203.0.113.0/24,nw_dst=10.0.0.0/8,'
            'icmp_type=8,actions=drop"'
        )

        info("  ACL: 访客WiFi物理隔离；gst3未连VPN仅VPN服务器；vpn-sync切换内网\n")

    def _setup_services(self):
        """配置 Web/FTP 应用层服务"""
        import base64

        web_cfg = SERVICE_CONFIG['web']
        ftp_cfg = SERVICE_CONFIG['ftp']
        dmz_web_cfg = SERVICE_CONFIG['dmz_web']
        ext_web_cfg = SERVICE_CONFIG['ext_web']

        web = self.net.get(web_cfg['host'])
        ftp = self.net.get(ftp_cfg['host'])
        dmz_web = self.net.get(dmz_web_cfg['host'])
        ext_web = self.net.get(ext_web_cfg['host'])

        # Web 服务
        web_root = web_cfg['root']
        web.cmd(f'mkdir -p {web_root}')
        web.cmd(f'echo "<html><body><h1>Campus Web Server</h1><p>资源共享测试页</p></body></html>" > {web_root}/index.html')
        web.cmd(f'cd {web_root} && python3 -m http.server {web_cfg["port"]} > /dev/null 2>&1 &')
        info(f"  Web: http://{web.IP()}/ (port {web_cfg['port']})\n")

        dmz_root = dmz_web_cfg['root']
        dmz_web.cmd(f'mkdir -p {dmz_root}')
        dmz_web.cmd(
            f'echo "<html><body><h1>Campus Public Portal</h1>'
            f'<p>Published from the DMZ security zone.</p></body></html>" '
            f'> {dmz_root}/index.html'
        )
        dmz_web.cmd(
            f'cd {dmz_root} && python3 -m http.server {dmz_web_cfg["port"]} '
            '> /dev/null 2>&1 &'
        )
        info(f"  DMZ Web: http://{dmz_web.IP()}/ (public portal)\n")

        ext_root = ext_web_cfg['root']
        ext_web.cmd(f'mkdir -p {ext_root}')
        ext_web.cmd(
            f'echo "<html><body><h1>External Website</h1>'
            f'<p>Simulated Internet resource outside the campus DMZ.</p></body></html>" '
            f'> {ext_root}/index.html'
        )
        ext_web.cmd(
            f'cd {ext_root} && python3 -m http.server {ext_web_cfg["port"]} '
            '> /dev/null 2>&1 &'
        )
        info(f"  External Web: http://{ext_web.IP()}/ (Internet zone)\n")

        # FTP 服务
        ftp_root = ftp_cfg['root']
        ftp.cmd(f'mkdir -p {ftp_root}')
        ftp.cmd(f'echo "Campus shared file - FTP resource" > {ftp_root}/share.txt')
        ftp_b64 = base64.b64encode(FTP_SERVER_PY.encode()).decode()
        ftp.cmd(f'echo {ftp_b64} | base64 -d > /tmp/ftp_server.py')
        ftp.cmd('python3 /tmp/ftp_server.py > /dev/null 2>&1 &')
        info(f"  FTP: ftp://{ftp.IP()}/share.txt (port {ftp_cfg['port']})\n")

    def _setup_vpn(self):
        """配置 GRE VPN 隧道（校园访客 gst3，权限等同宿舍）"""
        import subprocess

        srv = VPN_CONFIG['server']
        cli = VPN_CONFIG['client']
        tun_dev = cli['tunnel_dev']

        vpn_srv = self.net.get(srv['host'])
        vpn_cli = self.net.get(cli['host'])
        srv_ip = srv['ip']
        cli_ip = cli['ip']
        srv_tun = cli['server_tun_ip']
        cli_tun = cli['tunnel_ip']

        vpn_srv.cmd(f'ip link del {tun_dev} 2>/dev/null; true')
        vpn_cli.cmd(f'ip link del {tun_dev} 2>/dev/null; true')

        gre_key = 42
        vpn_srv.cmd(
            f'ip tunnel add {tun_dev} mode gre remote {cli_ip} local {srv_ip} '
            f'key {gre_key} ttl 255'
        )
        vpn_srv.cmd(f'ip addr add {srv_tun}/30 dev {tun_dev}')
        vpn_srv.cmd(f'ip link set {tun_dev} up')
        vpn_srv.cmd('sysctl -w net.ipv4.ip_forward=1')
        info(f"  VPN server {tun_dev}: {srv_tun} (GRE -> {cli_ip})\n")

        vpn_cli.cmd(
            f'ip tunnel add {tun_dev} mode gre remote {srv_ip} local {cli_ip} '
            f'key {gre_key} ttl 255'
        )
        vpn_cli.cmd(f'ip addr add {cli_tun}/30 dev {tun_dev}')
        vpn_cli.cmd(f'ip link set {tun_dev} up')
        info(f"  VPN client {cli['host']}: {cli_tun} (GRE -> {srv_ip})\n")

        vpn_srv.cmd('sysctl -w net.ipv4.ip_forward=1 net.ipv4.conf.all.rp_filter=0')
        vpn_srv.cmd(f'sysctl -w net.ipv4.conf.{tun_dev}.rp_filter=0')
        vpn_cli.cmd('sysctl -w net.ipv4.conf.all.rp_filter=0')
        vpn_cli.cmd(f'sysctl -w net.ipv4.conf.{tun_dev}.rp_filter=0')
        info(f"  VPN 数据面: 开关联后 gst3 内网路由走 {tun_dev} -> {srv_tun}，源 {cli_tun}\n")

        # 回程：各 VLAN 回包到隧道网段须经 vpn_srv（勿绑死在单个子接口）
        tun_net = VPN_CONFIG['tunnel_net']
        subprocess.run(
            f'ip route replace {tun_net} via {srv_ip} 2>/dev/null; true',
            shell=True
        )
        info(f"  vrouter route: {tun_net} via {srv_ip}\n")

        self.vpn_ready = True

    def run_api(self, port=5000):
        """启动 REST API，供前端调用真实 Ping/HTTP/FTP 测试"""
        import time
        from api_server import clear_root_vpn_nat, restore_cs1_guest_block, start_api_server

        clear_root_vpn_nat()
        if self.net:
            restore_cs1_guest_block(self.net)
        host_names = [h['name'] for h in HOSTS] + [s['name'] for s in SRV_HOSTS]
        server, _api = start_api_server(self, host_names, port)
        info(f"\n>> API 服务已启动: http://0.0.0.0:{port}\n")
        info("  GET /api/status\n")
        info("  GET /api/ping?src=dA1&dst=ofc1\n")
        info("  GET /api/http?src=dA1\n")
        info("  GET /api/ftp?src=dA1\n")
        info("  GET /api/security-metrics\n")
        info("  GET /api/observability\n")
        info("  POST /api/vpn-sync (X-Campus-Token)\n")
        info("  前端演示: 另开终端 python -m http.server 8000\n")
        info("  Ctrl+C 停止\n\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            info("\n>> 停止 API...\n")
        finally:
            try:
                server.shutdown()
            except Exception:
                pass
            self._clear_edge_firewall()

    def run_cli(self):
        info("\n>> 启动CLI...\n")
        info("常用命令:\n")
        info("  nodes                    - 查看节点\n")
        info("  net                      - 查看网络\n")
        info("  dA1 ping ofc1           - 测试三层连通性\n")
        info("  c2h1 ping -c 4 ofc1     - 校区间通信 (cs1-cs2)\n")
        info("  gst1 ping -c 4 gst2      - 访客WiFi经sw13二层互访\n")
        info("  gst1 ping -c 4 ofc1     - 访客WiFi访内网(应失败)\n")
        info("  gst3 ping -c 4 vpn_srv  - 校园访客访问DMZ VPN(无需开隧道)\n")
        info("  gst3 ping -c 4 ofc1     - 校园访客未连VPN访内网(应失败)；开VPN后成功\n")
        info("  gst3 ping -c 4 hr1      - 校园访客VPN访问人事(应失败)\n")
        info("  gst3 ping -c 4 web      - 校园访客经VPN访问Web\n")
        info("  dA1 ping hr1            - 测试ACL(应失败)\n")
        info("  ofc1 curl http://10.0.100.2/           - HTTP 访问\n")
        info("  dA1 curl http://203.0.113.10/          - 宿舍访问外部网站\n")
        info("  hr1 curl http://203.0.113.10/          - 人事访问外网(应失败)\n")
        info("  hr1 curl http://10.0.110.20/           - 人事访问官网白名单\n")
        info("  ofc1 curl ftp://10.0.100.3/share.txt  - FTP 下载\n")
        info("  gst3 ping -c 4 172.16.0.1          - VPN 隧道\n")
        info("  exit                     - 退出\n\n")
        CLI(self.net)

    def stop(self):
        """只清理一次；Mininet 重复 stop 会因链路已删而抛 AttributeError"""
        try:
            from api_server import clear_ovs_vpn_acl, clear_root_vpn_nat
            clear_root_vpn_nat()
            self._clear_edge_firewall()
            if self.net:
                clear_ovs_vpn_acl(self.net)
        except Exception:
            pass
        if not self.net:
            return
        net_ref = self.net
        self.net = None
        try:
            net_ref.stop()
        except (AttributeError, OSError):
            pass
        except Exception as exc:
            info(f"  Mininet stop: {exc}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='校园网络 Mininet 模拟器')
    parser.add_argument('--api', action='store_true', help='启动 REST API（供前端联调）')
    parser.add_argument('--api-port', type=int, default=5000, help='API 端口（默认 5000）')
    args = parser.parse_args()

    setLogLevel('info')

    campus = CampusNetwork()
    try:
        campus.build()
        if args.api:
            campus.run_api(args.api_port)
        else:
            campus.run_cli()
    except KeyboardInterrupt:
        info("\n>> 已中断\n")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        campus.stop()


if __name__ == '__main__':
    main()
