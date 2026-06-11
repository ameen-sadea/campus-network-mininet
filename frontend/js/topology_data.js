/**
 * 拓扑数据 - 与 campus_network.py 保持一致
 * DMZ(sw15) 在 as3 服务器区旁；校园公网资源下挂 DMZ
 * VPN flow: gst3 -> DMZ -> vpn_srv -> DMZ -> internal network
 * 访客WiFi(gst1/gst2) 仅经 sw13 二层互访，无主机间直连线
 */

const VLAN_CONFIG = {
    'mgmt':      { 'id': 1,   'network': '10.0.1.0/24',   'gateway': '10.0.1.1' },
    'dormA':     { 'id': 10,  'network': '10.0.10.0/24', 'gateway': '10.0.10.1' },
    'dormB':     { 'id': 11,  'network': '10.0.11.0/24', 'gateway': '10.0.11.1' },
    'dormC':     { 'id': 12,  'network': '10.0.12.0/24', 'gateway': '10.0.12.1' },
    'canteen':   { 'id': 13,  'network': '10.0.13.0/24', 'gateway': '10.0.13.1' },
    'office':    { 'id': 20,  'network': '10.0.20.0/24', 'gateway': '10.0.20.1' },
    'lab':       { 'id': 21,  'network': '10.0.21.0/24', 'gateway': '10.0.21.1' },
    'library':   { 'id': 30,  'network': '10.0.30.0/24', 'gateway': '10.0.30.1' },
    'academic':  { 'id': 40,  'network': '10.0.40.0/24', 'gateway': '10.0.40.1' },
    'hr':         { 'id': 50,  'network': '10.0.50.0/24', 'gateway': '10.0.50.1', 'secure': true },
    'finance':   { 'id': 60,  'network': '10.0.60.0/24', 'gateway': '10.0.60.1', 'secure': true },
    'logistics': { 'id': 70,  'network': '10.0.70.0/24', 'gateway': '10.0.70.1' },
    'wifiOfc':   { 'id': 80,  'network': '10.0.80.0/24', 'gateway': '10.0.80.1' },
    'wifiGst':   { 'id': 90,  'network': '10.0.90.0/24', 'gateway': '10.0.90.1' },
    'guestCampus': { 'id': 91, 'network': '10.0.91.0/24', 'gateway': '10.0.91.1' },
    'server':    { 'id': 100, 'network': '10.0.100.0/24', 'gateway': '10.0.100.1' },
    'dmz':       { 'id': 110, 'network': '10.0.110.0/24', 'gateway': '10.0.110.1' },
    'campus2':   { 'id': 200, 'network': '10.1.0.0/24',   'gateway': '10.1.0.1',  'campus': 2 },
    'internet':  { 'id': 250, 'network': '203.0.113.0/24', 'gateway': '203.0.113.1', 'external': true },
};

const VPN_CONFIG = {
    'server': { 'host': 'vpn_srv', 'ip': '10.0.110.10' },
    'client': { 'host': 'gst3', 'ip': '10.0.91.3', 'tunnel_dev': 'gre1', 'tunnel_ip': '172.16.0.2', 'server_tun_ip': '172.16.0.1' },
    'tunnel_net': '172.16.0.0/30',
    'mode': 'gre',
    'routes': ['10.0.0.0/8'],
};

const GUEST_WIFI_VLAN = 90;
const GUEST_CAMPUS_VLAN = 91;
const WIFI_GUEST_IDS = new Set(['gst1', 'gst2']);
const VPN_AS_DORM_VLAN = 10;

let vpnEnabled = false;

const SERVICE_CONFIG = {
    'web': { 'host': 'web', 'port': 80,  'protocol': 'http', 'url': 'http://10.0.100.2/' },
    'ftp': { 'host': 'ftp', 'port': 21,  'protocol': 'ftp',  'url': 'ftp://10.0.100.3/share.txt' },
    'dmz_web': { 'host': 'dmz_web', 'port': 80, 'protocol': 'http', 'url': 'http://10.0.110.20/' },
    'ext_web': { 'host': 'ext_web', 'port': 80, 'protocol': 'http', 'url': 'http://203.0.113.10/' },
};

const SWITCHES = {
    'cs1': { 'type': 'core', 'campus': 1, 'vlans': Object.keys(VLAN_CONFIG).filter(k => k !== 'campus2') },
    'cs2': { 'type': 'core', 'campus': 2, 'vlans': ['campus2'] },
    'fw1': { 'type': 'firewall', 'campus': 1, 'vlans': ['internet', 'dmz'] },
    'as1': { 'type': 'agg', 'campus': 1, 'vlans': ['office', 'lab', 'library', 'academic', 'hr', 'finance', 'logistics'] },
    'as2': { 'type': 'agg', 'campus': 1, 'vlans': ['dormA', 'dormB', 'dormC', 'canteen', 'wifiOfc'] },
    'as3': { 'type': 'agg', 'campus': 1, 'vlans': ['server', 'mgmt'] },
    'as4': { 'type': 'agg', 'campus': 2, 'vlans': ['campus2'] },
};

const ACCESS_SW = {
    'sw1': { 'vlan': 'office', 'agg': 'as1' },
    'sw2': { 'vlan': 'lab', 'agg': 'as1' },
    'sw3': { 'vlan': 'library', 'agg': 'as1' },
    'sw4': { 'vlan': 'academic', 'agg': 'as1' },
    'sw5': { 'vlan': 'hr', 'agg': 'as1', 'secure': true },
    'sw6': { 'vlan': 'finance', 'agg': 'as1', 'secure': true },
    'sw7': { 'vlan': 'logistics', 'agg': 'as1' },
    'sw8': { 'vlan': 'dormA', 'agg': 'as2' },
    'sw9': { 'vlan': 'dormB', 'agg': 'as2' },
    'sw10': { 'vlan': 'dormC', 'agg': 'as2' },
    'sw11': { 'vlan': 'canteen', 'agg': 'as2' },
    'sw12': { 'vlan': 'wifiOfc', 'agg': 'as2' },
    'sw13': { 'vlan': 'wifiGst', 'isolated': true },
    'sw14': { 'vlan': 'server', 'agg': 'as3' },
    'sw15': { 'vlan': 'dmz', 'agg': 'fw1' },
    'sw16': { 'vlan': 'guestCampus', 'isolated': true },
    'sw17': { 'vlan': 'campus2', 'agg': 'as4' },
    'sw18': { 'vlan': 'internet', 'agg': 'fw1' },
};

const VLAN_TO_ACCESS = {};
Object.entries(ACCESS_SW).forEach(([sw, cfg]) => { VLAN_TO_ACCESS[cfg.vlan] = sw; });

const CAMPUS2_IDS = new Set(['cs2', 'as4', 'sw17', 'c2h1', 'c2h2']);

const HOSTS_CONFIG = [
    { 'name': 'ofc1', 'ip': '10.0.20.3/24', 'vlan': 20, 'vlanName': 'office' },
    { 'name': 'ofc2', 'ip': '10.0.20.4/24', 'vlan': 20, 'vlanName': 'office' },
    { 'name': 'ofc3', 'ip': '10.0.20.5/24', 'vlan': 20, 'vlanName': 'office' },
    { 'name': 'acd1', 'ip': '10.0.40.3/24', 'vlan': 40, 'vlanName': 'academic' },
    { 'name': 'acd2', 'ip': '10.0.40.4/24', 'vlan': 40, 'vlanName': 'academic' },
    { 'name': 'acd3', 'ip': '10.0.40.5/24', 'vlan': 40, 'vlanName': 'academic' },
    { 'name': 'dA1', 'ip': '10.0.10.3/24', 'vlan': 10, 'vlanName': 'dormA' },
    { 'name': 'dA2', 'ip': '10.0.10.4/24', 'vlan': 10, 'vlanName': 'dormA' },
    { 'name': 'dA3', 'ip': '10.0.10.5/24', 'vlan': 10, 'vlanName': 'dormA' },
    { 'name': 'dB1', 'ip': '10.0.11.3/24', 'vlan': 11, 'vlanName': 'dormB' },
    { 'name': 'dB2', 'ip': '10.0.11.4/24', 'vlan': 11, 'vlanName': 'dormB' },
    { 'name': 'dB3', 'ip': '10.0.11.5/24', 'vlan': 11, 'vlanName': 'dormB' },
    { 'name': 'hr1', 'ip': '10.0.50.3/24', 'vlan': 50, 'vlanName': 'hr', 'secure': true },
    { 'name': 'hr2', 'ip': '10.0.50.4/24', 'vlan': 50, 'vlanName': 'hr', 'secure': true },
    { 'name': 'fin1', 'ip': '10.0.60.3/24', 'vlan': 60, 'vlanName': 'finance', 'secure': true },
    { 'name': 'fin2', 'ip': '10.0.60.4/24', 'vlan': 60, 'vlanName': 'finance', 'secure': true },
    { 'name': 'gst1', 'ip': '10.0.90.3/24', 'vlan': 90, 'vlanName': 'wifiGst', 'wifiIsland': true },
    { 'name': 'gst2', 'ip': '10.0.90.4/24', 'vlan': 90, 'vlanName': 'wifiGst', 'wifiIsland': true },
    { 'name': 'gst3', 'ip': '10.0.91.3/24', 'vlan': 91, 'vlanName': 'guestCampus', 'vpnClient': true },
    { 'name': 'c2h1', 'ip': '10.1.0.3/24', 'vlan': 200, 'vlanName': 'campus2', 'campus': 2 },
    { 'name': 'c2h2', 'ip': '10.1.0.4/24', 'vlan': 200, 'vlanName': 'campus2', 'campus': 2 },
];

const NODE_NAMES_CN = {
    'cs1': '核心交换机', 'cs2': '分校区核心', 'fw1': '边界防火墙',
    'as1': '汇聚交换机', 'as2': '汇聚交换机', 'as3': '汇聚交换机', 'as4': '汇聚交换机-4',
    'sw1': '办公楼交换机', 'sw2': '实验室交换机', 'sw3': '图书馆交换机',
    'sw4': '科研楼交换机', 'sw5': '人事处交换机', 'sw6': '财务处交换机',
    'sw7': '后勤处交换机', 'sw8': '宿舍A交换机', 'sw9': '宿舍B交换机',
    'sw10': '宿舍C交换机', 'sw11': '食堂交换机', 'sw12': '办公WiFi交换机',
    'sw13': '访客WiFi交换机', 'sw14': '服务器区交换机', 'sw15': 'DMZ交换机',
    'sw16': '校园访客交换机', 'sw17': '校区2交换机',
    '_to_campus2': '分校区', '_to_main': '主校区',
    'ofc1': '办公楼-1', 'ofc2': '办公楼-2', 'ofc3': '办公楼-3',
    'acd1': '科研楼-1', 'acd2': '科研楼-2', 'acd3': '科研楼-3',
    'dA1': '宿舍A-1', 'dA2': '宿舍A-2', 'dA3': '宿舍A-3',
    'dB1': '宿舍B-1', 'dB2': '宿舍B-2', 'dB3': '宿舍B-3',
    'hr1': '人事处-1', 'hr2': '人事处-2',
    'fin1': '财务处-1', 'fin2': '财务处-2',
    'gst1': '访客-1', 'gst2': '访客-2', 'gst3': '访客-3',
    'c2h1': '校区2-1', 'c2h2': '校区2-2',
    'web': 'Web服务器', 'ftp': 'FTP服务器', 'dns': 'DNS服务器',
    'vpn_srv': 'VPN服务器', 'dmz_web': '校园公网门户',
    'sw18': '公网边界', 'ext_web': '外部网站',
};

const SRV_HOSTS_CONFIG = [
    { 'name': 'web', 'ip': '10.0.100.2/24', 'vlan': 100, 'vlanName': 'server', 'service': 'http' },
    { 'name': 'ftp', 'ip': '10.0.100.3/24', 'vlan': 100, 'vlanName': 'server', 'service': 'ftp' },
    { 'name': 'dns', 'ip': '10.0.100.4/24', 'vlan': 100, 'vlanName': 'server' },
    { 'name': 'vpn_srv', 'ip': '10.0.110.10/24', 'vlan': 110, 'vlanName': 'dmz', 'vpn': true, 'parentSw': 'sw15' },
    { 'name': 'dmz_web', 'ip': '10.0.110.20/24', 'vlan': 110, 'vlanName': 'dmz', 'service': 'dmz_http', 'parentSw': 'sw15' },
    { 'name': 'ext_web', 'ip': '203.0.113.10/24', 'vlan': 250, 'vlanName': 'internet', 'service': 'external_http', 'parentSw': 'sw18', 'external': true },
];

const ACL_RULES = [
    { 'srcVlan': 10, 'dstVlan': 50, 'action': 'drop', 'desc': '宿舍A → 人事处' },
    { 'srcVlan': 11, 'dstVlan': 50, 'action': 'drop', 'desc': '宿舍B → 人事处' },
    { 'srcVlan': 10, 'dstVlan': 60, 'action': 'drop', 'desc': '宿舍A → 财务处' },
    { 'srcVlan': 11, 'dstVlan': 60, 'action': 'drop', 'desc': '宿舍B → 财务处' },
    { 'srcVlan': 91, 'dstVlan': '*', 'action': 'drop', 'desc': '校园访客 gst3 未连VPN → 内网', 'except': ['vpn_srv', 'dmz_web', '10.0.110.10', '10.0.110.20'] },
    { 'srcVlan': 50, 'dstHost': 'dmz_web', 'action': 'allow', 'desc': '人事处 → 校园官网白名单' },
    { 'srcVlan': 60, 'dstHost': 'dmz_web', 'action': 'allow', 'desc': '财务处 → 校园官网白名单' },
    { 'srcVlan': 50, 'dstVlan': 110, 'action': 'drop', 'desc': '人事处 → DMZ/VPN（保密区禁止外出）' },
    { 'srcVlan': 60, 'dstVlan': 110, 'action': 'drop', 'desc': '财务处 → DMZ/VPN（保密区禁止外出）' },
    { 'srcVlan': 50, 'dstVlan': 250, 'action': 'drop', 'desc': '人事处 → 外网' },
    { 'srcVlan': 60, 'dstVlan': 250, 'action': 'drop', 'desc': '财务处 → 外网' },
    { 'srcVlan': 250, 'dstHost': 'dmz_web', 'action': 'allow', 'desc': 'Internet → DMZ 校园门户（仅发布服务）' },
    { 'srcVlan': 250, 'dstVlan': '*', 'action': 'drop', 'desc': 'Internet → 其他校园区域（默认拒绝）', 'exceptVlans': [250] },
    { 'srcHost': 'dmz_web', 'dstVlan': '*', 'action': 'drop', 'desc': 'DMZ 门户 → 校园内网（阻止横向移动）', 'exceptVlans': [110, 250] },
];

function isVpnClient(hostId) {
    return hostId === VPN_CONFIG.client.host;
}

function isInternalIp(ipCidr) {
    const ip = ipCidr.split('/')[0];
    return ip.startsWith('10.') || ip.startsWith('172.16.');
}

function generateTopology() {
    const nodes = [];
    const links = [];

    for (const [swName, swConfig] of Object.entries(SWITCHES)) {
        nodes.push({
            'id': swName, 'type': 'switch', 'subtype': swConfig.type,
            'vlans': swConfig.vlans, 'campus': swConfig.campus || 1,
        });
    }

    for (const [swName, swConfig] of Object.entries(ACCESS_SW)) {
        nodes.push({
            'id': swName, 'type': 'switch', 'subtype': 'access',
            'vlans': [swConfig.vlan], 'vlanName': swConfig.vlan,
            'secure': swConfig.secure || false,
            'parentAgg': swConfig.directCore ? 'cs1' : swConfig.agg,
            'isolated': !!swConfig.isolated,
            'directCore': !!swConfig.directCore,
            'campus': swConfig.agg === 'as4' ? 2 : 1,
        });
    }

    for (const h of HOSTS_CONFIG) {
        nodes.push({
            'id': h.name, 'type': 'host', 'ip': h.ip, 'vlan': h.vlan,
            'vlanName': h.vlanName, 'secure': h.secure || false,
            'wifiIsland': !!h.wifiIsland, 'vpnClient': !!h.vpnClient,
            'campus': h.campus || 1,
            'parentSw': h.vpnClient ? 'sw18' : VLAN_TO_ACCESS[h.vlanName],
        });
    }

    for (const s of SRV_HOSTS_CONFIG) {
        nodes.push({
            'id': s.name, 'type': 'server', 'ip': s.ip, 'vlan': s.vlan,
            'vlanName': s.vlanName, 'service': s.service || null,
            'parentSw': s.parentSw || VLAN_TO_ACCESS[s.vlanName], 'campus': 1,
        });
    }

    links.push({ 'source': 'cs1', 'target': 'as1', 'type': 'trunk' });
    links.push({ 'source': 'cs1', 'target': 'as2', 'type': 'trunk' });
    links.push({ 'source': 'cs1', 'target': 'as3', 'type': 'trunk' });
    links.push({ 'source': 'cs1', 'target': 'fw1', 'type': 'firewall-inside' });
    links.push({ 'source': 'cs1', 'target': 'cs2', 'type': 'intercampus' });
    links.push({ 'source': 'cs2', 'target': 'as4', 'type': 'trunk' });

    for (const [swName, swConfig] of Object.entries(ACCESS_SW)) {
        if (swConfig.isolated) continue;
        if (swConfig.directCore) {
            links.push({ 'source': 'cs1', 'target': swName, 'type': 'direct-core' });
        } else {
            links.push({
                'source': swConfig.agg,
                'target': swName,
                'type': swConfig.agg === 'fw1' ? 'firewall-zone' : 'trunk',
            });
        }
    }

    HOSTS_CONFIG.forEach(h => {
        const sw = VLAN_TO_ACCESS[h.vlanName];
        if (sw) links.push({ 'source': sw, 'target': h.name, 'type': 'access' });
    });
    SRV_HOSTS_CONFIG.forEach(s => {
        const sw = VLAN_TO_ACCESS[s.vlanName];
        if (sw) {
            links.push({
                'source': sw,
                'target': s.name,
                'type': s.name === 'vpn_srv' ? 'dmz-vpn-access' : 'access',
            });
        }
    });

    // VPN 为展示妥协：客户端、服务端固定在核心旁，真实数据面仍使用 GRE
    links.push({ 'source': 'gst3', 'target': 'sw18', 'type': 'guest-edge-ingress' });

    return {
        'nodes': nodes, 'links': links,
        'vlans': VLAN_CONFIG, 'aclRules': ACL_RULES,
        'vpn': VPN_CONFIG, 'services': SERVICE_CONFIG,
    };
}

function isWifiGuest(id) {
    return WIFI_GUEST_IDS.has(id);
}

function checkACLBlock(srcNode, dstNode, srcId, dstId) {
    if (!srcNode || !dstNode) {
        return { 'blocked': true, 'reason': '节点不存在' };
    }

    if (srcNode.vlan && srcNode.vlan === dstNode.vlan) {
        return { 'blocked': false };
    }

    if (isWifiGuest(srcId)) {
        if (isWifiGuest(dstId)) {
            return { 'blocked': false };
        }
        return { 'blocked': true, 'reason': '访客WiFi隔离网（不可越 sw13）' };
    }

    const dstIp = dstNode.ip ? dstNode.ip.split('/')[0] : '';
    let effectiveVlan = srcNode.vlan;
    let viaVpn = false;

    if (isVpnClient(srcId)) {
        if (!vpnEnabled) {
            if (dstId === 'vpn_srv' || dstId === 'dmz_web'
                || dstIp === '10.0.110.10' || dstIp === '10.0.110.20') {
                return { 'blocked': false };
            }
            if (isInternalIp(dstNode.ip)) {
                return { 'blocked': true, 'reason': '校园访客未连VPN（直连被拒）' };
            }
            return { 'blocked': false };
        }
        if (!isInternalIp(dstNode.ip)) {
            return { 'blocked': false };
        }
        effectiveVlan = VPN_AS_DORM_VLAN;
        viaVpn = true;
    }

    for (const rule of ACL_RULES) {
        if (isVpnClient(srcId) && vpnEnabled && rule.srcVlan === GUEST_CAMPUS_VLAN) continue;
        const srcMatch = rule.srcHost === srcId || rule.srcVlan === effectiveVlan || rule.srcVlan === '*';
        const dstMatch = rule.dstHost === dstId || rule.dstVlan === dstNode.vlan || rule.dstVlan === '*';
        if (srcMatch && dstMatch) {
            if (rule.except && (rule.except.includes(srcId) || rule.except.includes(dstId) || rule.except.includes(dstIp))) {
                continue;
            }
            if (rule.exceptVlans && rule.exceptVlans.includes(dstNode.vlan)) continue;
            if (rule.action === 'allow') {
                return { 'blocked': false, 'whitelist': true };
            }
            if (rule.action !== 'drop') continue;
            return { 'blocked': true, 'reason': rule.desc || 'ACL blocked' };
        }
    }

    return { 'blocked': false, 'via': viaVpn ? 'VPN' : undefined };
}

function simulatePing(src, dst, topologyData) {
    const srcNode = topologyData.nodes.find(n => n.id === src);
    const dstNode = topologyData.nodes.find(n => n.id === dst);
    const acl = checkACLBlock(srcNode, dstNode, src, dst);
    if (acl.blocked) {
        return {
            'success': false,
            'output': `PING ${dst} (${dstNode.ip}) 56(84) bytes of data.\nFrom ${src} icmp_seq=1 Packet filtered\n--- ${dst} ping statistics ---\n1 packets transmitted, 0 received, 100% packet loss`,
            'error': acl.reason || 'ACL blocked', 'rtt': null,
        };
    }
    const via = acl.via ? ` via ${acl.via}` : '';
    const avgRtt = (Math.random() * 0.5 + 0.3).toFixed(2);
    return {
        'success': true,
        'output': `PING ${dst} (${dstNode.ip}) 56(84) bytes of data.\n64 bytes from ${dst}: icmp_seq=1 ttl=64 time=${avgRtt} ms${via}\n--- ${dst} ping statistics ---\n1 packets transmitted, 1 received, 0% packet loss`,
        'rtt': { 'min': (avgRtt * 0.8).toFixed(2), 'avg': avgRtt, 'max': (avgRtt * 1.2).toFixed(2) },
    };
}

function simulateHTTP(src, dstHost) {
    const topologyData = generateTopology();
    const srcNode = topologyData.nodes.find(n => n.id === src);
    const dstNode = topologyData.nodes.find(n => n.id === dstHost);
    if (!dstNode || !['web', 'dmz_web', 'ext_web'].includes(dstHost)) {
        return { 'success': false, 'error': '目标不是 Web 服务器' };
    }
    const acl = checkACLBlock(srcNode, dstNode, src, dstHost);
    if (acl.blocked) {
        return { 'success': false, 'output': `curl: (7) Failed to connect to ${dstNode.ip}: Connection refused (ACL)`, 'error': acl.reason };
    }
    const via = acl.via ? ` [${acl.via}]` : '';
    const title = dstHost === 'dmz_web'
        ? 'Campus Public Portal (DMZ)'
        : (dstHost === 'ext_web' ? 'External Website (Internet)' : 'Campus Web Server');
    return { 'success': true, 'output': `HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h1>${title}</h1></body></html>${via}`, 'status': 200 };
}

function simulateFTP(src, dstHost) {
    const topologyData = generateTopology();
    const srcNode = topologyData.nodes.find(n => n.id === src);
    const dstNode = topologyData.nodes.find(n => n.id === dstHost);
    if (!dstNode || (dstHost !== 'ftp' && dstNode.service !== 'ftp')) {
        return { 'success': false, 'error': '目标不是 FTP 服务器' };
    }
    const acl = checkACLBlock(srcNode, dstNode, src, dstHost);
    if (acl.blocked) {
        return { 'success': false, 'output': `curl: (7) Failed to connect to ftp://10.0.100.3/share.txt: ACL blocked`, 'error': acl.reason };
    }
    const via = acl.via ? ` [${acl.via}]` : '';
    return { 'success': true, 'output': `220 Campus FTP Ready\r\n230 Login OK\r\n150 Opening BINARY mode data connection\r\nCampus shared file - FTP resource\r\n226 Transfer complete${via}`, 'file': 'share.txt' };
}

function isVPNEnabled() { return vpnEnabled; }
function setVPNEnabled(enabled) { vpnEnabled = !!enabled; }

function getVPNStatus() {
    const on = vpnEnabled;
    return {
        'ready': on, 'enabled': on, 'mode': VPN_CONFIG.mode,
        'server': VPN_CONFIG.server, 'client': VPN_CONFIG.client,
        'tunnel_net': VPN_CONFIG.tunnel_net, 'routes': VPN_CONFIG.routes,
        'status': on ? 'VPN 已连接' : 'VPN 未连接',
    };
}

window.VLAN_CONFIG = VLAN_CONFIG;
window.SWITCHES = SWITCHES;
window.ACCESS_SW = ACCESS_SW;
window.HOSTS_CONFIG = HOSTS_CONFIG;
window.SRV_HOSTS_CONFIG = SRV_HOSTS_CONFIG;
window.ACL_RULES = ACL_RULES;
window.VPN_CONFIG = VPN_CONFIG;
window.SERVICE_CONFIG = SERVICE_CONFIG;
window.NODE_NAMES_CN = NODE_NAMES_CN;
window.CAMPUS2_IDS = CAMPUS2_IDS;
window.generateTopology = generateTopology;
window.simulatePing = simulatePing;
window.simulateHTTP = simulateHTTP;
window.simulateFTP = simulateFTP;
window.getVPNStatus = getVPNStatus;
window.isVPNEnabled = isVPNEnabled;
window.setVPNEnabled = setVPNEnabled;
window.checkACLBlock = checkACLBlock;
