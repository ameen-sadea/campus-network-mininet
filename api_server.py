#!/usr/bin/env python3
"""
Mininet 校园网 REST API（标准库实现，无 Flask 依赖）
供前端 api.js 调用真实 Ping / HTTP / FTP 测试结果。
"""
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# 浏览器超时/刷新会提前断开，写响应时忽略即可
_CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)

SERVICE_IPS = {
    'web': '10.0.100.2',
    'ftp': '10.0.100.3',
    'dmz_web': '10.0.110.20',
    'ext_web': '203.0.113.10',
}

API_TOKEN = os.environ.get('CAMPUS_API_TOKEN', 'campus-demo-control-v2')
ALLOWED_ORIGINS = {
    'http://localhost:8000',
    'http://127.0.0.1:8000',
}
BUILD_VERSION = '3.5.0'
API_VERBOSE = os.environ.get('CAMPUS_API_VERBOSE', '').lower() in ('1', 'true', 'yes', 'on')

VPN_CLIENT = 'gst3'
VPN_CLIENT_GW = '10.0.91.1'
VPN_CAMPUS_NET = '10.0.91.0/24'
VPN_TUN_DEV = 'gre1'
VPN_TUNNEL_IP = '172.16.0.2'
VPN_TUNNEL_GW = '172.16.0.1'
VPN_SERVER_IP = '10.0.110.10'
VPN_ROUTE_NETS = ['10.0.0.0/8']
VPN_CLIENT_IP = '10.0.91.3'
VPN_GRE_KEY = 42
VPN_SNAT_CHAIN = 'CAMPUS_GST1_SNAT'
VPN_DNAT_CHAIN = 'CAMPUS_GST1_DNAT'


def _root_iptables(args):
    """vrouter 在 root 命名空间，Mininet 主机里 iptables 常不可用"""
    try:
        proc = subprocess.run(
            ['iptables', *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0, (proc.stderr or proc.stdout or '').strip()
    except Exception as exc:
        return False, str(exc)


def clear_root_vpn_nat():
    for table_hook in ((VPN_SNAT_CHAIN, 'POSTROUTING'), (VPN_DNAT_CHAIN, 'PREROUTING')):
        chain, hook = table_hook
        _root_iptables(['-t', 'nat', '-D', hook, '-j', chain])
        _root_iptables(['-t', 'nat', '-F', chain])
        _root_iptables(['-t', 'nat', '-X', chain])


def apply_root_vpn_nat(enabled):
    """在 vrouter(root) 做 SNAT/DNAT：开 VPN 后 gst3 流量以 172.16.0.2 进内网"""
    clear_root_vpn_nat()
    if not enabled:
        return True, 'cleared'

    ok1, err1 = _root_iptables(['-t', 'nat', '-N', VPN_SNAT_CHAIN])
    ok2, err2 = _root_iptables(['-t', 'nat', '-N', VPN_DNAT_CHAIN])
    if not (ok1 and ok2):
        return False, err1 or err2

    rules = [
        ['-t', 'nat', '-A', VPN_SNAT_CHAIN, '-s', f'{VPN_CLIENT_IP}/32',
         '-d', '10.0.0.0/8',
         '-j', 'SNAT', '--to-source', VPN_TUNNEL_IP],
        ['-t', 'nat', '-A', VPN_DNAT_CHAIN, '-d', f'{VPN_TUNNEL_IP}/32',
         '-j', 'DNAT', '--to-destination', VPN_CLIENT_IP],
    ]
    for rule in rules:
        ok, err = _root_iptables(rule)
        if not ok:
            clear_root_vpn_nat()
            return False, err

    _root_iptables(['-t', 'nat', '-I', 'POSTROUTING', '1', '-j', VPN_SNAT_CHAIN])
    _root_iptables(['-t', 'nat', '-I', 'PREROUTING', '1', '-j', VPN_DNAT_CHAIN])
    return True, 'ok'


def root_vpn_nat_status():
    ok, out = _root_iptables(['-t', 'nat', '-L', VPN_SNAT_CHAIN, '-n'])
    if not ok:
        return 'none'
    lines = [ln for ln in out.splitlines() if 'SNAT' in ln or 'DNAT' in ln]
    return '; '.join(lines) if lines else 'empty'


VPN_OVS_PRIOS = (611,)
CS1_GUEST_BLOCK_PRIO = 603

# 与内置 FTP 服务配套：控制连接上直传 RETR 响应
_FTP_FETCH_PY = b"""import socket,sys
ip=sys.argv[1]
s=socket.create_connection((ip,21),12)
def r():
    d=b""
    while True:
        c=s.recv(8192)
        if not c:
            break
        d+=c
        if b"\\r\\n" in d:
            break
    return d
r()
s.sendall(b"USER anonymous\\r\\n")
r()
s.sendall(b"PASS x\\r\\n")
r()
s.sendall(b"RETR share.txt\\r\\n")
d=b""
while True:
    c=s.recv(8192)
    if not c:
        break
    d+=c
    if b"226" in d or b"550" in d:
        break
sys.stdout.write(d.decode("utf-8","replace"))
s.close()
"""
_FTP_FETCH_B64 = base64.b64encode(_FTP_FETCH_PY).decode()


def _ovs_add_flows(sw_name, switch, rules):
    for prio, src, dst, action in rules:
        switch.cmd(
            f'ovs-ofctl add-flow {sw_name} '
            f'"priority={prio},ip,nw_src={src},nw_dst={dst},actions={action}"'
        )


def clear_ovs_vpn_acl(net):
    """删除 cs1 上 VPN 动态流表 611"""
    try:
        cs1 = net.get('cs1')
    except Exception:
        return
    if not cs1:
        return
    for prio in VPN_OVS_PRIOS:
        cs1.cmd(f'ovs-ofctl del-flows cs1 "priority={prio}"')


def restore_cs1_guest_block(net):
    """VPN 关：恢复 cs1 603（gst3 校园访客网段）"""
    try:
        cs1 = net.get('cs1')
    except Exception:
        return
    if not cs1:
        return
    cs1.cmd(f'ovs-ofctl del-flows cs1 "priority={CS1_GUEST_BLOCK_PRIO}"')
    cs1.cmd(
        'ovs-ofctl add-flow cs1 '
        f'"priority={CS1_GUEST_BLOCK_PRIO},ip,nw_src={VPN_CAMPUS_NET},'
        'nw_dst=10.0.0.0/8,actions=drop"'
    )


def _vpn_client_restrict_rules():
    """VPN 开：gst3 仍禁止人事/财务"""
    return [
        (611, f'{VPN_CLIENT_IP}/32', '10.0.50.0/24', 'drop'),
        (611, f'{VPN_CLIENT_IP}/32', '10.0.60.0/24', 'drop'),
    ]


def _log_ovs_acl_state(net):
    """诊断：记录 cs1 关键 ACL"""
    try:
        cs1 = net.get('cs1')
    except Exception:
        return
    if not cs1:
        return
    raw = cs1.cmd('ovs-ofctl dump-flows cs1 2>/dev/null')
    hits = []
    for prio in (str(CS1_GUEST_BLOCK_PRIO), '611'):
        if f'priority={prio}' in raw:
            hits.append(prio)
    api_log(f'ovs-cs1 active={",".join(hits) or "none"}')


def apply_ovs_vpn_acl(net, enabled):
    """
    校园访客 gst3（sw16 直连 cs1，ACL 在 cs1）：
    - VPN 关：cs1 603 拒绝 gst3→内网
    - VPN 开：保留 603；仅 GRE 内层源 172.16.0.2 由静态规则 608 放行
    """
    clear_ovs_vpn_acl(net)
    if not enabled:
        restore_cs1_guest_block(net)
        return True, 'gst3-block-on'

    # Keep the physical guest subnet blocked even while VPN is enabled.
    # Only the GRE inner source (172.16.0.2) may enter through rule 608.
    restore_cs1_guest_block(net)
    try:
        cs1 = net.get('cs1')
    except Exception as exc:
        return False, str(exc)
    if not cs1:
        return False, 'no cs1'
    _ovs_add_flows('cs1', cs1, _vpn_client_restrict_rules())
    return True, 'gst3-direct-block-on; tunnel-only'


def _gre_link_up(cli_host):
    link = cli_host.cmd(f'ip link show {VPN_TUN_DEV} 2>/dev/null')
    return VPN_TUN_DEV in link and 'state DOWN' not in link


def _gre_tunnel_healthy(cli_host, probe=True):
    """检测 GRE 接口；probe=False 时只看接口状态，避免每次同步多等 2s"""
    if not _gre_link_up(cli_host):
        return False
    if not probe:
        return True
    tun = cli_host.cmd(f'ping -4 -c 1 -W 1 -I {VPN_TUN_DEV} {VPN_TUNNEL_GW} 2>&1')
    return ' 0% packet loss' in tun or '1 received' in tun


def ensure_gre_tunnel(net, cli_host, probe=True):
    """隧道正常则仅拉起；异常时才重建"""
    try:
        srv = net.get('vpn_srv')
    except Exception:
        return False
    if not srv:
        return False
    cli_host.cmd(f'ip link set {VPN_TUN_DEV} up 2>/dev/null; true')
    srv.cmd(f'ip link set {VPN_TUN_DEV} up 2>/dev/null; true')
    if _gre_tunnel_healthy(cli_host, probe=probe):
        return True
    if not repair_gre_tunnel(net, cli_host):
        return False
    return _gre_tunnel_healthy(cli_host, probe=True)


def repair_gre_tunnel(net, cli_host):
    """重建 GRE 隧道（WSL 下偶发失效；两端须相同 key）"""
    try:
        srv_host = net.get('vpn_srv')
    except Exception:
        return False
    if not srv_host:
        return False

    healthy = True
    for host, remote, local, tun_ip in (
        (cli_host, VPN_SERVER_IP, VPN_CLIENT_IP, VPN_TUNNEL_IP),
        (srv_host, VPN_CLIENT_IP, VPN_SERVER_IP, VPN_TUNNEL_GW),
    ):
        host.cmd(f'ip link del {VPN_TUN_DEV} 2>/dev/null; true')
        create_out = host.cmd(
            f'ip tunnel add {VPN_TUN_DEV} mode gre remote {remote} local {local} '
            f'key {VPN_GRE_KEY} ttl 255 2>&1'
        )
        addr_out = host.cmd(f'ip addr replace {tun_ip}/30 dev {VPN_TUN_DEV} 2>&1')
        up_out = host.cmd(f'ip link set {VPN_TUN_DEV} up 2>&1')
        host.cmd(
            'sysctl -w net.ipv4.ip_forward=1 net.ipv4.conf.all.rp_filter=0 '
            f'net.ipv4.conf.{VPN_TUN_DEV}.rp_filter=0 2>/dev/null; true'
        )
        link_out = host.cmd(f'ip -d link show {VPN_TUN_DEV} 2>&1')
        endpoint_ok = VPN_TUN_DEV in link_out and 'gre remote' in link_out
        if not endpoint_ok:
            healthy = False
            api_log(
                f'gre-repair {host.name}: create={create_out.strip()[:160]!r} '
                f'addr={addr_out.strip()[:120]!r} up={up_out.strip()[:120]!r} '
                f'link={link_out.strip()[:220]!r}'
            )
    return healthy


def _host_eth0(host):
    """Mininet 主机默认物理网卡（排除 lo / gre）"""
    for name in sorted(host.intfNames()):
        if name == 'lo' or name.startswith('gre'):
            continue
        return name
    return f'{host.name}-eth0'


class CampusNetworkAPI:
    def __init__(self, campus_network, host_names):
        self.campus = campus_network
        self.net = campus_network.net
        self.host_names = set(host_names)
        self.lock = threading.Lock()
        self._vpn_sync_state = None
        self._observability_lock = threading.Lock()
        self._link_counter_sample = None
        self._observability_cache = None
        self._observability_cache_at = 0.0

    def _get_host(self, name):
        if name not in self.host_names:
            return None, f'未知主机: {name}'
        try:
            return self.net.get(name), None
        except Exception as exc:
            return None, str(exc)

    def _run_cmd(self, host, command):
        with self.lock:
            return host.cmd(command)

    @staticmethod
    def _parse_vpn_flag(value):
        return str(value).lower() in ('1', 'true', 'yes', 'on')

    @staticmethod
    def _is_campus_internal_ip(ip):
        return ip.startswith('10.') or ip.startswith('172.16.')

    def _apply_vpn_client_gre_routes(self, host, enabled):
        """VPN 开：内网走 GRE 隧道(源 172.16.0.2，匹配 cs1 ACL 608)；关：恢复默认网关路由"""
        eth = _host_eth0(host)
        for net in VPN_ROUTE_NETS:
            self._run_cmd(host, f'ip route del {net} 2>/dev/null; true')
        self._run_cmd(host, f'ip route del {VPN_SERVER_IP}/32 2>/dev/null; true')
        if not enabled:
            return
        self._run_cmd(host, f'ip route replace {VPN_SERVER_IP}/32 via {VPN_CLIENT_GW} dev {eth}')
        for net in VPN_ROUTE_NETS:
            self._run_cmd(host, f'ip route replace {net} via {VPN_TUNNEL_GW} dev {VPN_TUN_DEV}')

    def _test_gre_tunnel(self, host):
        outer = self._run_cmd(host, f'ping -4 -c 1 -W 2 {VPN_SERVER_IP} 2>&1')
        outer_ok = self._parse_ping_success(outer)
        tun_ok = _gre_tunnel_healthy(host)
        return outer_ok, tun_ok

    def _gre_diagnostics(self, cli_host):
        try:
            srv_host = self.net.get('vpn_srv')
        except Exception:
            srv_host = None
        outer = self._run_cmd(cli_host, f'ping -4 -c 1 -W 1 {VPN_SERVER_IP} 2>&1')
        tunnel = self._run_cmd(
            cli_host,
            f'ping -4 -c 1 -W 1 -I {VPN_TUN_DEV} {VPN_TUNNEL_GW} 2>&1',
        )
        cli_link = self._run_cmd(cli_host, f'ip -d link show {VPN_TUN_DEV} 2>&1')
        srv_link = srv_host.cmd(f'ip -d link show {VPN_TUN_DEV} 2>&1') if srv_host else 'no vpn_srv'
        diag = {
            'outer_ok': self._parse_ping_success(outer),
            'tunnel_ok': self._parse_ping_success(tunnel),
            'client_link': cli_link.strip()[:240],
            'server_link': srv_link.strip()[:240],
            'tunnel_ping': tunnel.strip()[:240],
        }
        api_log(f'gre-diagnostics: {diag}')
        return diag

    def _sync_vpn_client(self, vpn_enabled, force=False):
        """gst3 VPN：物理直连始终被 603 阻断，开启后仅 GRE 内层流量入网。"""
        if not force and self._vpn_sync_state == vpn_enabled:
            return {
                'success': True,
                'enabled': bool(vpn_enabled),
                'mode': getattr(self.campus, 'vpn_mode', 'off'),
                'detail': 'unchanged',
            }

        host, err = self._get_host(VPN_CLIENT)
        if err:
            return {'success': False, 'enabled': False, 'mode': 'failed', 'error': err}

        self._apply_vpn_client_gre_routes(host, False)
        clear_root_vpn_nat()
        self._run_cmd(host, 'iptables -t nat -F 2>/dev/null; true')

        if not vpn_enabled:
            ovs_ok, ovs_msg = apply_ovs_vpn_acl(self.net, False)
            mode = 'blocked' if ovs_ok else 'failed'
            self.campus.vpn_mode = mode
            self._vpn_sync_state = False
            detail = f'{ovs_msg}; path=off'
            api_log(f'vpn-sync enabled=False mode={mode} ({detail})')
            _log_ovs_acl_state(self.net)
            return {
                'success': ovs_ok,
                'enabled': False,
                'mode': mode,
                'detail': detail,
            }

        gre_ok = ensure_gre_tunnel(self.net, host, probe=True)
        if not gre_ok:
            diag = self._gre_diagnostics(host)
            clear_ovs_vpn_acl(self.net)
            restore_cs1_guest_block(self.net)
            self.campus.vpn_mode = 'failed-closed'
            self._vpn_sync_state = False
            api_log('vpn-sync: GRE unavailable; guest access remains blocked (fail-closed)')
            _log_ovs_acl_state(self.net)
            return {
                'success': False,
                'enabled': False,
                'mode': 'failed-closed',
                'error': (
                    'GRE tunnel unavailable; '
                    f'outer={"ok" if diag["outer_ok"] else "fail"}, '
                    f'interface={"ok" if VPN_TUN_DEV in diag["client_link"] else "missing"}'
                ),
                'diagnostics': diag,
            }

        # GRE already uses 172.16.0.2 as its inner source. Root NAT would
        # rewrite return traffic toward the physical guest VLAN and create
        # an asymmetric path, so it must remain disabled.
        clear_root_vpn_nat()
        ovs_ok, ovs_msg = apply_ovs_vpn_acl(self.net, True)
        if not ovs_ok:
            self._apply_vpn_client_gre_routes(host, False)
            clear_root_vpn_nat()
            clear_ovs_vpn_acl(self.net)
            restore_cs1_guest_block(self.net)
            self.campus.vpn_mode = 'failed-closed'
            self._vpn_sync_state = False
            detail = f'ovs={ovs_msg}'
            api_log(f'vpn-sync: policy apply failed; guest access remains blocked ({detail})')
            _log_ovs_acl_state(self.net)
            return {
                'success': False,
                'enabled': False,
                'mode': 'failed-closed',
                'error': detail,
            }

        self._apply_vpn_client_gre_routes(host, True)
        mode = 'gre'
        detail = f'{ovs_msg}; nat=not-required; path=gre-via-dmz'
        self.campus.vpn_mode = mode
        self._vpn_sync_state = True
        sample = self._run_cmd(host, 'ip route get 10.0.11.4 2>&1 | head -1').strip()
        api_log(f'vpn-sync enabled=True mode={mode} route={sample} ({detail})')
        _log_ovs_acl_state(self.net)
        return {
            'success': True,
            'enabled': True,
            'mode': mode,
            'detail': detail,
        }

    def _run_ping_attempts(self, host, dst_ip, count):
        """真实 ping；VPN 策略由交换机 ACL 开/关控制"""
        tries = [f'ping -4 -c {count} -W 1 {dst_ip}']
        last_out = ''
        last_cmd = tries[0]
        for cmd in tries:
            last_cmd = cmd
            last_out = self._run_cmd(host, cmd)
            if self._parse_ping_success(last_out):
                return last_out, cmd, True
        return last_out, last_cmd, False

    @staticmethod
    def _parse_ping_success(output):
        if not output or not output.strip():
            return False
        if '100% packet loss' in output:
            return False
        if ' 0% packet loss' in output or ', 0% packet loss' in output:
            return True
        match = re.search(r'(\d+)\s+received', output)
        return bool(match and int(match.group(1)) > 0)

    @staticmethod
    def _ping_error_message(output):
        text = (output or '').strip()
        if not text:
            return 'ping 无输出'
        if 'Name or service not known' in text:
            return '无法解析目标地址'
        if '100% packet loss' in text:
            return '100% packet loss'
        first = text.splitlines()[0][:120]
        return first or 'ping failed'

    def ping(self, src, dst, count=1, vpn_enabled=False):
        src_host, err = self._get_host(src)
        if err:
            return {'success': False, 'error': err, 'source': 'mininet'}
        dst_host, err = self._get_host(dst)
        if err:
            return {'success': False, 'error': err, 'source': 'mininet'}

        count = max(1, min(int(count), 4))
        dst_ip = dst_host.IP()
        if src == VPN_CLIENT:
            self._sync_vpn_client(vpn_enabled)

        t0 = time.time()
        out, cmd, ok = self._run_ping_attempts(src_host, dst_ip, count)
        elapsed = round(time.time() - t0, 2)
        api_log(f'ping {src} -> {dst}({dst_ip}) vpn={vpn_enabled} cmd="{cmd.strip()}" {elapsed}s ok={ok}')
        if not ok:
            route_hint = self._run_cmd(src_host, f'ip route get {dst_ip} 2>&1 | head -1')
            gw_ping = self._run_cmd(src_host, f'ping -4 -c 1 -W 2 {VPN_CLIENT_GW} 2>&1')
            api_log(f'ping out: {(out or "").strip()[:200]}')
            api_log(f'route: {(route_hint or "").strip()[:120]}')
            api_log(f'gw {VPN_CLIENT_GW}: {"ok" if self._parse_ping_success(gw_ping) else "fail"}')

        success = ok

        rtt = None
        if success:
            match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', out)
            if not match:
                match = re.search(r'time=([\d.]+)\s*ms', out)
            avg = match.group(1) if match else '?'
            rtt = {'min': avg, 'avg': avg, 'max': avg}

        result = {
            'success': success,
            'output': out,
            'rtt': rtt,
            'source': 'mininet',
            'target_ip': dst_ip,
        }
        if not success:
            result['error'] = self._ping_error_message(out)
        return result

    def http_get(self, src, dst_host='web', vpn_enabled=False):
        if dst_host not in ('web', 'dmz_web', 'ext_web'):
            return {'success': False, 'error': '仅支持访问 web、dmz_web 或 ext_web', 'source': 'mininet'}

        src_host, err = self._get_host(src)
        if err:
            return {'success': False, 'error': err, 'source': 'mininet'}

        if src == VPN_CLIENT:
            self._sync_vpn_client(vpn_enabled)

        dst_ip = SERVICE_IPS[dst_host]
        url = f'http://{dst_ip}/'
        out = self._run_cmd(
            src_host,
            f'curl -s -m 8 -w "\\nHTTP_CODE:%{{http_code}}" {url}'
        )

        if 'HTTP_CODE:' in out:
            body, code_part = out.rsplit('HTTP_CODE:', 1)
            try:
                status = int(code_part.strip())
            except ValueError:
                status = 0
        else:
            body, status = out, 0

        success = 200 <= status < 400
        result = {
            'success': success,
            'output': body.strip(),
            'status': status,
            'source': 'mininet',
        }
        if not success:
            result['error'] = f'HTTP {status}' if status else 'connection failed'
        return result

    def ftp_get(self, src, dst_host='ftp', vpn_enabled=False):
        if dst_host != 'ftp':
            return {'success': False, 'error': '仅支持访问 ftp 服务器', 'source': 'mininet'}

        src_host, err = self._get_host(src)
        if err:
            return {'success': False, 'error': err, 'source': 'mininet'}

        if src == VPN_CLIENT:
            self._sync_vpn_client(vpn_enabled)

        dst_ip = SERVICE_IPS['ftp']
        try:
            ftp_srv = self.net.get('ftp')
            ftp_srv.cmd('pgrep -f ftp_server.py >/dev/null || python3 /tmp/ftp_server.py &')
        except Exception:
            pass
        self._run_cmd(src_host, f'echo {_FTP_FETCH_B64} | base64 -d > /tmp/ftpget.py')
        out = self._run_cmd(src_host, f'python3 /tmp/ftpget.py {dst_ip}')
        success = 'Campus shared file' in out or '226 Transfer complete' in out
        if not success:
            api_log(f'ftp raw: {(out or "")[:240]}')

        result = {
            'success': success,
            'output': out.strip(),
            'file': 'share.txt',
            'source': 'mininet',
        }
        if not success:
            result['error'] = 'ftp failed'
        return result

    def vpn_sync(self, vpn_enabled):
        result = self._sync_vpn_client(vpn_enabled, force=True)
        return {
            **result,
            'client': VPN_CLIENT,
            'source': 'mininet',
        }

    def vpn_enabled(self):
        return self._vpn_sync_state is True

    @staticmethod
    def _parse_flow_counters(raw, switch_name):
        rows = []
        for line in (raw or '').splitlines():
            if 'priority=' not in line:
                continue
            priority = re.search(r'priority=(\d+)', line)
            packets = re.search(r'n_packets=(\d+)', line)
            byte_count = re.search(r'n_bytes=(\d+)', line)
            src = re.search(r'nw_src=([^,\s]+)', line)
            dst = re.search(r'nw_dst=([^,\s]+)', line)
            actions = re.search(r'actions=(.+)$', line)
            if not priority:
                continue
            prio = int(priority.group(1))
            if prio < 600:
                continue
            rows.append({
                'switch': switch_name,
                'priority': prio,
                'src': src.group(1) if src else '*',
                'dst': dst.group(1) if dst else '*',
                'action': actions.group(1).strip() if actions else '',
                'packets': int(packets.group(1)) if packets else 0,
                'bytes': int(byte_count.group(1)) if byte_count else 0,
            })
        return rows

    def security_metrics(self):
        flows = []
        for switch_name in ('cs1', 'fw1'):
            try:
                switch = self.net.get(switch_name)
                raw = switch.cmd(f'ovs-ofctl dump-flows {switch_name} 2>/dev/null')
                flows.extend(self._parse_flow_counters(raw, switch_name))
            except Exception as exc:
                api_log(f'metrics {switch_name}: {exc}')
        flows.sort(key=lambda row: (row['switch'], -row['priority'], row['src'], row['dst']))
        fw_ok, fw_raw = _root_iptables(
            ['-L', 'CAMPUS_EDGE_FILTER', '-n', '-v', '-x']
        )
        fw_drop_packets = 0
        if fw_ok:
            for line in fw_raw.splitlines():
                match = re.match(r'\s*(\d+)\s+\d+\s+DROP\b', line)
                if match:
                    fw_drop_packets += int(match.group(1))
        return {
            'success': True,
            'source': 'mininet',
            'total_hits': sum(row['packets'] for row in flows),
            'flows': flows,
            'edge_firewall': {
                'active': fw_ok,
                'mode': 'conntrack-stateful',
                'chain': 'CAMPUS_EDGE_FILTER',
                'drop_packets': fw_drop_packets,
                'rules': fw_raw.splitlines()[2:] if fw_ok else [],
            },
        }

    @staticmethod
    def _parse_ping_metrics(output):
        transmitted = re.search(r'(\d+)\s+packets transmitted', output or '')
        received = re.search(r'(\d+)\s+(?:packets )?received', output or '')
        loss = re.search(r'([\d.]+)%\s+packet loss', output or '')
        rtt = re.search(
            r'(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = '
            r'([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
            output or '',
        )
        return {
            'transmitted': int(transmitted.group(1)) if transmitted else 0,
            'received': int(received.group(1)) if received else 0,
            'loss_pct': float(loss.group(1)) if loss else 100.0,
            'rtt_min_ms': float(rtt.group(1)) if rtt else None,
            'rtt_avg_ms': float(rtt.group(2)) if rtt else None,
            'rtt_max_ms': float(rtt.group(3)) if rtt else None,
            'rtt_jitter_ms': float(rtt.group(4)) if rtt else None,
        }

    def _intercampus_link_sample(self):
        cs1 = self.net.get('cs1')
        cs2 = self.net.get('cs2')
        pairs = cs1.connectionsTo(cs2)
        if not pairs:
            return {'available': False, 'error': 'cs1-cs2 link not found'}

        cs1_intf, cs2_intf = pairs[0]

        def read_counter(node, intf_name, field):
            raw = node.cmd(
                f'cat /sys/class/net/{intf_name}/statistics/{field} 2>/dev/null'
            ).strip()
            return int(raw) if raw.isdigit() else 0

        now = time.time()
        current = {
            'timestamp': now,
            'rx_bytes': read_counter(cs1, cs1_intf.name, 'rx_bytes'),
            'tx_bytes': read_counter(cs1, cs1_intf.name, 'tx_bytes'),
            'rx_packets': read_counter(cs1, cs1_intf.name, 'rx_packets'),
            'tx_packets': read_counter(cs1, cs1_intf.name, 'tx_packets'),
        }
        previous = self._link_counter_sample
        self._link_counter_sample = current
        rx_mbps = tx_mbps = 0.0
        interval = None
        if previous:
            interval = max(now - previous['timestamp'], 0.001)
            rx_mbps = max(current['rx_bytes'] - previous['rx_bytes'], 0) * 8 / interval / 1_000_000
            tx_mbps = max(current['tx_bytes'] - previous['tx_bytes'], 0) * 8 / interval / 1_000_000

        qdisc = cs1.cmd(f'tc qdisc show dev {cs1_intf.name} 2>/dev/null').strip()
        return {
            'available': True,
            'interface': cs1_intf.name,
            'peer_interface': cs2_intf.name,
            'rx_bytes': current['rx_bytes'],
            'tx_bytes': current['tx_bytes'],
            'rx_packets': current['rx_packets'],
            'tx_packets': current['tx_packets'],
            'rx_mbps': round(rx_mbps, 4),
            'tx_mbps': round(tx_mbps, 4),
            'sample_interval_s': round(interval, 3) if interval else None,
            'qdisc': qdisc,
            'fixed_impairment_configured': bool(
                re.search(r'\bnetem\b|\btbf\b|\bhtb\b', qdisc)
            ),
        }

    def _http_probe(self, src_name, target_ip, timeout_s=3):
        host = self.net.get(src_name)
        raw = self._run_cmd(
            host,
            f"curl -s -o /dev/null -m {timeout_s} -w '%{{http_code}} %{{time_total}}' "
            f"http://{target_ip}/ 2>&1",
        ).strip()
        match = re.search(r'(\d{3})\s+([\d.]+)', raw)
        code = int(match.group(1)) if match else 0
        seconds = float(match.group(2)) if match else None
        return {
            'success': 200 <= code < 400,
            'http_code': code,
            'latency_ms': round(seconds * 1000, 2) if seconds is not None else None,
        }

    def observability(self, force=False):
        with self._observability_lock:
            now = time.time()
            if (
                not force and self._observability_cache
                and now - self._observability_cache_at < 4
            ):
                return self._observability_cache

            c2h1 = self.net.get('c2h1')
            ofc1 = self.net.get('ofc1')
            ping_raw = self._run_cmd(
                c2h1,
                f'ping -4 -c 3 -i 0.2 -W 1 {ofc1.IP()} 2>&1',
            )
            ping_metrics = self._parse_ping_metrics(ping_raw)
            ping_metrics['success'] = ping_metrics['received'] > 0
            ping_metrics['source'] = 'active-ping:c2h1->ofc1'

            security = self.security_metrics()
            drop_hits = sum(
                row['packets'] for row in security['flows']
                if 'drop' in row.get('action', '').lower()
            )
            result = {
                'success': True,
                'source': 'mininet-live',
                'measured_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'intercampus': {
                    'probe': ping_metrics,
                    'link': self._intercampus_link_sample(),
                    'configured_sla': None,
                    'note': 'No fixed delay/loss/bandwidth is injected.',
                },
                'dmz': {
                    'external_to_portal': self._http_probe('ext_web', '10.0.110.20'),
                    'external_to_internal': self._http_probe(
                        'ext_web', '10.0.100.2', timeout_s=1
                    ),
                    'whitelist_hr_to_portal': self._http_probe('hr1', '10.0.110.20'),
                    'vpn_ready': bool(self.campus.vpn_ready),
                },
                'security': {
                    'ovs_acl_packets': security['total_hits'],
                    'ovs_drop_packets': drop_hits,
                    'edge_firewall': security['edge_firewall'],
                },
            }
            self._observability_cache = result
            self._observability_cache_at = now
            return result

    def status(self):
        return {
            'online': True,
            'mode': 'mininet',
            'version': BUILD_VERSION,
            'vpn_ready': bool(self.campus.vpn_ready),
            'vpn_backend': getattr(self.campus, 'vpn_mode', 'off'),
            'hosts': len(self.host_names),
            'dmz': {
                'network': '10.0.110.0/24',
                'access_switch': 'sw15',
                'vpn_gateway': '10.0.110.10',
                'public_portal': '10.0.110.20',
            },
            'internet': {
                'network': '203.0.113.0/24',
                'edge_switch': 'sw18',
                'external_website': '203.0.113.10',
                'firewall': 'conntrack-stateful',
            },
        }


def api_log(msg):
    if API_VERBOSE:
        sys.stderr.write(f'[API] {msg}\n')
        sys.stderr.flush()


def make_handler(api):
    class APIHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            api_log(fmt % args)

        def _send_json(self, data, status=200):
            try:
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                origin = self.headers.get('Origin')
                if origin in ALLOWED_ORIGINS:
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Campus-Token')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except _CLIENT_GONE:
                pass

        def handle(self):
            try:
                super().handle()
            except _CLIENT_GONE:
                pass

        def do_OPTIONS(self):
            self.send_response(204)
            origin = self.headers.get('Origin')
            if origin in ALLOWED_ORIGINS:
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Campus-Token')
            self.end_headers()

        def _authorized_control_request(self):
            origin = self.headers.get('Origin')
            if origin and origin not in ALLOWED_ORIGINS:
                return False
            return self.headers.get('X-Campus-Token') == API_TOKEN

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != '/api/vpn-sync':
                self._send_json({'error': 'not found'}, 404)
                return
            if not self._authorized_control_request():
                self._send_json({'success': False, 'error': 'unauthorized control request'}, 403)
                return
            try:
                length = min(int(self.headers.get('Content-Length', '0')), 4096)
                payload = json.loads(self.rfile.read(length) or b'{}')
            except (ValueError, json.JSONDecodeError):
                self._send_json({'success': False, 'error': 'invalid JSON'}, 400)
                return
            enabled = api._parse_vpn_flag(payload.get('enabled', False))
            result = api.vpn_sync(enabled)
            self._send_json(result, 200 if result.get('success') else 503)

        def do_GET(self):
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            api_log(f'GET {parsed.path} {params}')

            if parsed.path == '/api/status':
                self._send_json(api.status())
                return

            if parsed.path == '/api/vpn-sync':
                self._send_json({'error': 'use authenticated POST'}, 405)
                return

            if parsed.path == '/api/security-metrics':
                self._send_json(api.security_metrics())
                return

            if parsed.path == '/api/observability':
                force = params.get('force', '').lower() in ('1', 'true', 'yes', 'on')
                self._send_json(api.observability(force=force))
                return

            # VPN state is controlled only by authenticated POST /api/vpn-sync.
            vpn_enabled = api.vpn_enabled()

            if parsed.path == '/api/ping':
                src = params.get('src', '')
                dst = params.get('dst', '')
                count = params.get('count', '1')
                if not src or not dst:
                    self._send_json({'success': False, 'error': '缺少 src 或 dst'}, 400)
                    return
                result = api.ping(src, dst, count, vpn_enabled)
                self._send_json(result)
                return

            if parsed.path == '/api/http':
                src = params.get('src', '')
                dst = params.get('dst', 'web')
                if not src:
                    self._send_json({'success': False, 'error': '缺少 src'}, 400)
                    return
                result = api.http_get(src, dst, vpn_enabled)
                api_log(f'http {src} -> {dst}: success={result.get("success")}')
                self._send_json(result)
                return

            if parsed.path == '/api/ftp':
                src = params.get('src', '')
                dst = params.get('dst', 'ftp')
                if not src:
                    self._send_json({'success': False, 'error': '缺少 src'}, 400)
                    return
                result = api.ftp_get(src, dst, vpn_enabled)
                api_log(f'ftp {src} -> {dst}: success={result.get("success")}')
                self._send_json(result)
                return

            self._send_json({'error': 'not found'}, 404)

    return APIHandler


class QuietHTTPServer(HTTPServer):
    """客户端提前断开时不打印整段 traceback"""

    def handle_error(self, request, client_address):
        import sys
        if isinstance(sys.exc_info()[1], _CLIENT_GONE):
            return
        super().handle_error(request, client_address)


def start_api_server(campus_network, host_names, port=5000):
    api = CampusNetworkAPI(campus_network, host_names)
    server = QuietHTTPServer(('0.0.0.0', port), make_handler(api))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, api
