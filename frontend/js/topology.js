/**
 * Topology Visualization - 主校区复现原始 D3 四层布局
 */

let svg = null;
let nodeMap = {};
let linkMap = {};
let topologyPage = 'main';
let lastPathHighlight = null;

const LAYOUT_PADDING = 60;
const MAIN_HOST_GAP_MIN = 43;   // 主校区底层平铺最小间距
const CAMPUS2_HOST_GAP = 46;    // 分校区仅 2 台主机，固定间距（略大于原先 40）
const TOPO_HEIGHT = 660;

// ===== 拓扑手动位置调整入口 =====
// 1) as1/as2/as3 坐标覆盖入口：null 表示使用自动布局。
const MAIN_AGG_POSITION_OVERRIDES = {
    as1: { x: 270, y: null },
    as2: { x: 520, y: null },
    as3: { x: 680, y: null },
};

// 2) sw1~sw14 整体平移入口：x 正数向右，y 正数向下。
const MAIN_ACCESS_SW_OFFSET = { x: 20, y: 0 };

// 3) sw1~sw14 下挂节点整体平移入口：x 正数向右，y 正数向下。
const MAIN_ACCESS_HOST_OFFSET = { x: 10, y: 0 };

// 4) 主校区里“点击分校区”按钮平移入口：x 正数向右，y 正数向下。
const MAIN_CAMPUS2_BUTTON_OFFSET = { x: -320, y: 0 };

// 5) 分校区页面整体平移入口：x 正数向右，y 正数向下。
const CAMPUS2_LAYOUT_OFFSET = { x: 0, y: 0 };

// 6) Internet 外部区蓝色边框大小入口：数值越大，边框向对应方向扩得越多。
const INTERNET_ZONE_PADDING = { left: 52, right: 52, top: 54, bottom: 54 };

// 7) Internet 外部区整体平移入口：包含 gst3、sw18、外部网站及其连线。
const INTERNET_ZONE_OFFSET = { x: 293, y: 0 };

// 主校区：保持原四层布局；DMZ(sw15)下挂校园公网资源
const ORIGINAL_MAIN_SW = new Set([
    'cs1', 'fw1', 'as1', 'as2', 'as3',
    'sw1', 'sw2', 'sw3', 'sw4', 'sw5', 'sw6', 'sw7',
    'sw8', 'sw9', 'sw10', 'sw11', 'sw12', 'sw13', 'sw14', 'sw15',
    'sw18',
]);
const ORIGINAL_MAIN_HOSTS = new Set([
    'ofc1', 'ofc2', 'ofc3', 'acd1', 'acd2', 'acd3',
    'dA1', 'dA2', 'dA3', 'dB1', 'dB2', 'dB3',
    'hr1', 'hr2', 'fin1', 'fin2', 'gst1', 'gst2', 'gst3',
    'web', 'ftp', 'dns', 'vpn_srv', 'dmz_web', 'ext_web',
]);
// WIFI_GUEST_IDS 由 topology_data.js 提供，勿重复声明
const VPN_CAMPUS_CLIENT = 'gst3';

const nodeColors = {
    'core': '#2563eb',
    'agg': '#9333ea',
    'access': '#64748b',
    'host': '#16a34a',
    'server': '#ea580c',
    'bridge': '#06b6d4',
    'firewall': '#dc2626',
};

const nodeRadius = {
    'core': 42,
    'agg': 36,
    'access': 28,
    'host': 22,
    'server': 28,
    'bridge': 30,
    'firewall': 32,
};

function getNodeNameCN(nodeId) {
    if (window.NODE_NAMES_CN && window.NODE_NAMES_CN[nodeId]) {
        return window.NODE_NAMES_CN[nodeId];
    }
    return nodeId;
}

function isCampus2Node(node) {
    if (!node) return false;
    if (node.campus === 2) return true;
    if (window.CAMPUS2_IDS && window.CAMPUS2_IDS.has(node.id)) return true;
    return ['cs2', 'as4', 'sw17'].includes(node.id);
}

function sortAccessSwitches(access) {
    return access.slice().sort((a, b) => {
        const na = parseInt(String(a.id).replace('sw', ''), 10) || 0;
        const nb = parseInt(String(b.id).replace('sw', ''), 10) || 0;
        return na - nb;
    });
}

function sortHostsOriginal(hosts) {
    // 人事/财务在接入层位于宿舍左侧，底层顺序与之对齐以减少交叉线
    const order = [
        'ofc1', 'ofc2', 'ofc3', 'acd1', 'acd2', 'acd3',
        'hr1', 'hr2', 'fin1', 'fin2',
        'dA1', 'dA2', 'dA3', 'dB1', 'dB2', 'dB3',
        'gst1', 'gst2',
        'web', 'ftp', 'dns',
    ];
    const rank = Object.fromEntries(order.map((id, i) => [id, i]));
    return hosts.slice().sort((a, b) => (rank[a.id] ?? 999) - (rank[b.id] ?? 999));
}

function buildPageData(fullData, page) {
    const nodes = [];
    const links = [];

    if (page === 'main') {
        fullData.nodes.forEach(n => {
            if (ORIGINAL_MAIN_SW.has(n.id)) nodes.push({ ...n });
            else if (ORIGINAL_MAIN_HOSTS.has(n.id)) nodes.push({ ...n });
        });
        fullData.links.forEach(l => {
            if (l.type === 'intercampus' && l.source === 'cs1' && l.target === 'cs2') {
                links.push({ source: 'cs1', target: '_to_campus2', type: 'intercampus' });
                return;
            }
            // sw16 is intentionally hidden. Do not invent a gst3-cs1 cable.
            if (l.source === 'sw16' || l.target === 'sw16') {
                return;
            }
            const ok = (ORIGINAL_MAIN_SW.has(l.source) || ORIGINAL_MAIN_HOSTS.has(l.source)) &&
                       (ORIGINAL_MAIN_SW.has(l.target) || ORIGINAL_MAIN_HOSTS.has(l.target));
            if (ok) links.push({ ...l });
        });
        nodes.push({ id: '_to_campus2', type: 'bridge', subtype: 'bridge', campus: 2 });
    } else {
        fullData.nodes.forEach(n => {
            if (isCampus2Node(n)) nodes.push({ ...n });
        });
        fullData.links.forEach(l => {
            if (l.type === 'intercampus' && l.source === 'cs1' && l.target === 'cs2') {
                links.push({ source: '_to_main', target: 'cs2', type: 'intercampus' });
                return;
            }
            const src = fullData.nodes.find(n => n.id === l.source);
            const tgt = fullData.nodes.find(n => n.id === l.target);
            if (src && tgt && isCampus2Node(src) && isCampus2Node(tgt)) {
                links.push({ ...l });
            }
        });
        nodes.push({ id: '_to_main', type: 'bridge', subtype: 'bridge', campus: 1 });
    }

    return { nodes, links };
}

function renderTopology(data) {
    const container = document.getElementById('topologyContainer');
    const width = container.clientWidth || 1000;
    const height = TOPO_HEIGHT;
    const pageData = buildPageData(data, topologyPage);

    d3.select('#topologySvg').selectAll('*').remove();

    svg = d3.select('#topologySvg')
        .attr('viewBox', `0 0 ${width} ${height}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');

    const defs = svg.append('defs');

    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow').attr('dx', '0').attr('dy', '3').attr('stdDeviation', '4').attr('flood-opacity', '0.2');

    const glow = defs.append('filter').attr('id', 'glow');
    glow.append('feGaussianBlur').attr('stdDeviation', '5').attr('result', 'coloredBlur');
    const feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    [
        { id: 'dmz-arrow-in', color: '#94a3b8' },
        { id: 'dmz-arrow-out', color: '#94a3b8' },
    ].forEach(({ id, color }) => {
        const marker = defs.append('marker')
            .attr('id', id)
            .attr('viewBox', '0 0 10 10')
            .attr('refX', 8)
            .attr('refY', 5)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto-start-reverse');
        marker.append('path')
            .attr('d', 'M 0 0 L 10 5 L 0 10 z')
            .attr('fill', 'context-stroke');
    });

    Object.entries(nodeColors).forEach(([type, color]) => {
        const gradient = defs.append('radialGradient').attr('id', `grad-${type}`).attr('cx', '35%').attr('cy', '35%');
        gradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(color).brighter(0.4));
        gradient.append('stop').attr('offset', '100%').attr('stop-color', color);
    });

    nodeMap = {};
    data.nodes.forEach(node => { nodeMap[node.id] = node; });
    pageData.nodes.forEach(node => { nodeMap[node.id] = node; });

    linkMap = {};
    data.links.forEach(link => {
        linkMap[`${link.source}-${link.target}`] = link;
        linkMap[`${link.target}-${link.source}`] = link;
    });
    pageData.links.forEach(link => {
        linkMap[`${link.source}-${link.target}`] = link;
        linkMap[`${link.target}-${link.source}`] = link;
    });

    const layers = computeHierarchy(pageData);
    if (topologyPage === 'main') {
        createOriginalLayout(layers, width, height);
    } else {
        createCampus2Layout(layers, width, height);
    }

    if (topologyPage === 'main') {
        drawDmzZone(svg);
        drawInternetZone(svg);
    }

    svg.append('g').attr('class', 'links').selectAll('line')
        .data(pageData.links.filter(link =>
            link.type !== 'dmz-vpn-access' &&
            !([link.source, link.target].includes('fw1') &&
              [link.source, link.target].includes('sw15'))
        )).enter().append('line')
        .attr('class', d => `link ${d.type || 'trunk'}`)
        .attr('x1', d => (nodeMap[d.source] || {}).x || 0)
        .attr('y1', d => (nodeMap[d.source] || {}).y || 0)
        .attr('x2', d => (nodeMap[d.target] || {}).x || 0)
        .attr('y2', d => (nodeMap[d.target] || {}).y || 0)
        .attr('stroke', d => {
            if (d.type === 'guest-peer') return '#a78bfa';
            if (d.type === 'direct-core') return '#38bdf8';
            if (d.type === 'guest-edge-ingress') return '#94a3b8';
            if (d.type === 'intercampus') return '#06b6d4';
            if (d.type === 'access') return '#cbd5e1';
            return '#94a3b8';
        })
        .attr('stroke-width', d => {
            if (d.type === 'guest-peer') return 2.5;
            if (d.type === 'guest-edge-ingress') return 2.5;
            if (d.type === 'access') return 1.5;
            return 2.5;
        })
        .attr('stroke-dasharray', d => {
            if (d.type === 'guest-peer') return '7,5';
            if (d.type === 'direct-core') return '6,4';
            if (d.type === 'guest-edge-ingress') return '0';
            if (d.type === 'intercampus') return '8,6';
            if (d.type === 'access') return '4,4';
            return '10,5';
        })
        .attr('marker-end', d => d.type === 'guest-edge-ingress' ? 'url(#dmz-arrow-in)' : null)
        .attr('opacity', d => d.type === 'guest-peer' ? 0.95 : 1);

    if (topologyPage === 'main') {
        drawFirewallDmzFlowArrows(svg);
        drawDmzVpnFlowArrows(svg);
    }

    const nodes = svg.append('g').attr('class', 'nodes').selectAll('g')
        .data(pageData.nodes).enter().append('g')
        .attr('class', 'node cursor-pointer')
        .attr('transform', d => `translate(${d.x || 0}, ${d.y || 0})`)
        .on('click', function(event, d) {
            if (d.type === 'bridge') {
                event.stopPropagation();
                switchTopologyPage(d.id === '_to_campus2' ? 'campus2' : 'main');
            }
        });

    nodes.append('circle')
        .attr('r', d => (nodeRadius[d.subtype] || nodeRadius[d.type] || 15) + 8)
        .attr('fill', 'none')
        .attr('stroke', d => nodeColors[d.subtype || d.type] || '#999')
        .attr('stroke-width', 2)
        .attr('opacity', 0.2);

    nodes.append('circle')
        .attr('class', 'node-circle')
        .attr('r', d => nodeRadius[d.subtype] || nodeRadius[d.type] || 15)
        .attr('fill', d => `url(#grad-${d.subtype || d.type})`)
        .attr('stroke', d => d.secure ? '#dc2626' : '#ffffff')
        .attr('stroke-width', d => d.secure ? 4 : 3)
        .attr('filter', 'url(#shadow)');

    nodes.append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .attr('fill', 'white')
        .attr('font-size', d => {
            const r = nodeRadius[d.subtype] || nodeRadius[d.type] || 15;
            return r < 24 ? '10px' : '12px';
        })
        .attr('font-weight', 'bold')
        .attr('pointer-events', 'none')
        .text(d => {
            const name = getNodeNameCN(d.id);
            return name.length > 5 ? name.substring(0, 4) + '..' : name;
        });

    nodes.filter(d => d.type === 'switch')
        .append('text')
        .attr('class', 'vlan-label')
        .attr('text-anchor', 'middle')
        .attr('dy', d => (nodeRadius[d.subtype] || nodeRadius[d.type] || 15) + 18)
        .attr('font-size', '11px')
        .attr('fill', '#64748b')
        .attr('font-weight', '500')
        .text(d => d.vlanName || '');

    nodes.filter(d => d.type === 'bridge')
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', d => (nodeRadius.bridge) + 16)
        .attr('font-size', '10px')
        .attr('fill', '#0891b2')
        .text('点击切换');

    nodes.filter(d => d.type !== 'bridge')
        .on('mouseenter', function(event, d) { showTooltip(event, d); })
        .on('mouseleave', function() { hideTooltip(); });

    updateCampusPageButtons();

    if (lastPathHighlight) {
        applyPathHighlight();
    }
}

/** 主校区底层终端：整行平铺居中 */
function layoutFlatHosts(hosts, width, y, gapMin) {
    const usableWidth = width - 2 * LAYOUT_PADDING;
    const hostCount = hosts.length;
    if (hostCount === 0) return;
    const gap = hostCount > 1
        ? Math.max(gapMin, (usableWidth - 20) / (hostCount - 1))
        : 0;
    const rowWidth = gap * Math.max(hostCount - 1, 0);
    const startX = (width - rowWidth) / 2;
    hosts.forEach((node, i) => {
        node.x = hostCount === 1 ? width / 2 : startX + gap * i;
        node.y = y;
    });
}

/** 分校区底层：少量主机固定间距，居中于接入交换机下方 */
function layoutCampus2Hosts(hosts, centerX, y, gap) {
    const hostCount = hosts.length;
    if (hostCount === 0) return;
    hosts.forEach((node, i) => {
        node.x = centerX + (i - (hostCount - 1) / 2) * gap;
        node.y = y;
    });
}

/** 四层布局：底层终端平铺（与接入交换机不必对齐） */
function createOriginalLayout(layers, width, height) {
    const usableWidth = width - 2 * LAYOUT_PADDING;
    const usableHeight = height - 2 * LAYOUT_PADDING;
    const layerSpacing = usableHeight / 4;

    const cs1 = layers.core.find(n => n.id === 'cs1');
    if (cs1) {
        cs1.x = width / 2 - 50;
        cs1.y = LAYOUT_PADDING + layerSpacing * 0.5;
    }

    const bridge = nodeMap['_to_campus2'];
    if (bridge && cs1) {
        bridge.x = cs1.x + 158 + MAIN_CAMPUS2_BUTTON_OFFSET.x;
        bridge.y = cs1.y + MAIN_CAMPUS2_BUTTON_OFFSET.y;
    }

    const aggSpacing = usableWidth / (layers.agg.length + 1);
    layers.agg.forEach((node, i) => {
        node.x = LAYOUT_PADDING + aggSpacing * (i + 1);
        node.y = LAYOUT_PADDING + layerSpacing * 1.5;
        const override = MAIN_AGG_POSITION_OVERRIDES[node.id];
        if (override) {
            if (override.x !== null) node.x = override.x;
            if (override.y !== null) node.y = override.y;
        }
    });

    const sortedAccess = sortAccessSwitches(layers.access)
        .filter(n => n.id !== 'sw15' && n.id !== 'sw18');
    const mainWidth = Math.max(760, width - 400);
    const accSpacing = (mainWidth - 2 * LAYOUT_PADDING) / (sortedAccess.length + 1);
    sortedAccess.forEach((node, i) => {
        node.x = LAYOUT_PADDING + accSpacing * (i + 1) + MAIN_ACCESS_SW_OFFSET.x;
        node.y = LAYOUT_PADDING + layerSpacing * 2.5 + MAIN_ACCESS_SW_OFFSET.y;
    });

    const flatHosts = sortHostsOriginal(
        layers.hosts.filter(h =>
            h.id !== VPN_CAMPUS_CLIENT && h.id !== 'vpn_srv' &&
            h.id !== 'dmz_web' && h.id !== 'ext_web'
        )
    );
    layoutFlatHosts(flatHosts, mainWidth, LAYOUT_PADDING + layerSpacing * 3.5, MAIN_HOST_GAP_MIN);
    flatHosts.forEach(node => {
        node.x += MAIN_ACCESS_HOST_OFFSET.x;
        node.y += MAIN_ACCESS_HOST_OFFSET.y;
    });

    // Security zones occupy the reserved right side of the canvas.
    const g3 = layers.hosts.find(n => n.id === 'gst3');
    const vpn = layers.hosts.find(n => n.id === 'vpn_srv');
    const dmzWeb = layers.hosts.find(n => n.id === 'dmz_web');
    const extWeb = layers.hosts.find(n => n.id === 'ext_web');
    const dmzSw = layers.access.find(n => n.id === 'sw15');
    const internetSw = layers.access.find(n => n.id === 'sw18');
    const edgeFw = layers.firewall.find(n => n.id === 'fw1');
    if (edgeFw) {
        edgeFw.x = width - 370;
        edgeFw.y = LAYOUT_PADDING + layerSpacing * 1.3;
    }
    if (dmzSw) {
        dmzSw.x = width - 255;
        dmzSw.y = LAYOUT_PADDING + layerSpacing * 2.3;
    }
    if (dmzSw && vpn) {
        vpn.x = dmzSw.x + 130;
        vpn.y = dmzSw.y;
    }
    if (dmzSw && dmzWeb) {
        dmzWeb.x = dmzSw.x;
        dmzWeb.y = LAYOUT_PADDING + layerSpacing * 3.55;
    }
    if (internetSw) {
        internetSw.x = width - 560 + INTERNET_ZONE_OFFSET.x;
        internetSw.y = LAYOUT_PADDING + layerSpacing * 0.55 + INTERNET_ZONE_OFFSET.y;
    }
    if (internetSw && g3) {
        g3.x = internetSw.x;
        g3.y = internetSw.y - 85;
    }
    if (internetSw && extWeb) {
        extWeb.x = internetSw.x + 150;
        extWeb.y = internetSw.y;
    }
}

function drawDmzZone(rootSvg) {
    const dmzSw = nodeMap.sw15;
    const vpn = nodeMap.vpn_srv;
    const portal = nodeMap.dmz_web;
    if (!dmzSw || !vpn || !portal) return;

    const minX = Math.min(dmzSw.x, vpn.x, portal.x) - 58;
    const maxX = Math.max(dmzSw.x, vpn.x, portal.x) + 58;
    const minY = dmzSw.y - 48;
    const maxY = Math.max(vpn.y, portal.y) + 48;
    const zone = rootSvg.append('g').attr('class', 'dmz-zone');
    zone.append('rect')
        .attr('x', minX)
        .attr('y', minY)
        .attr('width', maxX - minX)
        .attr('height', maxY - minY)
        .attr('rx', 18)
        .attr('fill', '#fff7ed')
        .attr('stroke', '#f97316')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '8,5')
        .attr('opacity', 0.72);
    zone.append('text')
        .attr('x', minX + 12)
        .attr('y', minY + 18)
        .attr('fill', '#c2410c')
        .attr('font-size', '12px')
        .attr('font-weight', '700')
        .text('DMZ \u5b89\u5168\u7f13\u51b2\u533a - VLAN 110');
}

function drawInternetZone(rootSvg) {
    const edge = nodeMap.sw18;
    const website = nodeMap.ext_web;
    const guest = nodeMap.gst3;
    if (!edge || !website) return;

    const zoneNodes = guest ? [edge, website, guest] : [edge, website];
    const minX = Math.min(...zoneNodes.map(n => n.x)) - INTERNET_ZONE_PADDING.left;
    const maxX = Math.max(...zoneNodes.map(n => n.x)) + INTERNET_ZONE_PADDING.right;
    const minY = Math.min(...zoneNodes.map(n => n.y)) - INTERNET_ZONE_PADDING.top;
    const maxY = Math.max(...zoneNodes.map(n => n.y)) + INTERNET_ZONE_PADDING.bottom;
    const zone = rootSvg.append('g').attr('class', 'internet-zone');
    zone.append('rect')
        .attr('x', minX)
        .attr('y', minY)
        .attr('width', maxX - minX)
        .attr('height', maxY - minY)
        .attr('rx', 18)
        .attr('fill', '#eff6ff')
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '8,5')
        .attr('opacity', 0.72);
    zone.append('text')
        .attr('x', minX + 12)
        .attr('y', minY + 18)
        .attr('fill', '#1d4ed8')
        .attr('font-size', '12px')
        .attr('font-weight', '700')
        .text('Internet \u5916\u90e8\u533a - VLAN 250');
}

function drawDmzVpnFlowArrows(rootSvg) {
    const dmzSw = nodeMap.sw15;
    const vpn = nodeMap.vpn_srv;
    if (!dmzSw || !vpn) return;

    const flows = rootSvg.append('g')
        .attr('class', 'dmz-vpn-flow')
        .attr('pointer-events', 'none');

    flows.append('path')
        .attr('class', 'dmz-flow-arrow')
        .attr('d', `M ${dmzSw.x + 29} ${dmzSw.y - 8} L ${vpn.x - 30} ${vpn.y - 8}`)
        .attr('fill', 'none')
        .attr('stroke', '#94a3b8')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '7,5')
        .attr('marker-end', 'url(#dmz-arrow-in)');

    flows.append('path')
        .attr('class', 'dmz-flow-arrow')
        .attr('d', `M ${vpn.x - 30} ${vpn.y + 8} L ${dmzSw.x + 29} ${dmzSw.y + 8}`)
        .attr('fill', 'none')
        .attr('stroke', '#94a3b8')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '7,5')
        .attr('marker-end', 'url(#dmz-arrow-out)');

    flows.append('text')
        .attr('x', (dmzSw.x + vpn.x) / 2)
        .attr('y', dmzSw.y - 17)
        .attr('text-anchor', 'middle')
        .attr('fill', '#64748b')
        .attr('font-size', '10px')
        .text('\u5916\u5c42\u63a5\u5165');
    flows.append('text')
        .attr('x', (dmzSw.x + vpn.x) / 2)
        .attr('y', dmzSw.y + 25)
        .attr('text-anchor', 'middle')
        .attr('fill', '#64748b')
        .attr('font-size', '10px')
        .text('\u89e3\u5c01\u88c5\u5165\u7f51');

}

function drawFirewallDmzFlowArrows(rootSvg) {
    const firewall = nodeMap.fw1;
    const dmzSw = nodeMap.sw15;
    if (!firewall || !dmzSw) return;

    const dx = dmzSw.x - firewall.x;
    const dy = dmzSw.y - firewall.y;
    const length = Math.max(Math.hypot(dx, dy), 1);
    const nx = -dy / length * 7;
    const ny = dx / length * 7;
    const startRatio = 34 / length;
    const endRatio = 30 / length;
    const fx = firewall.x + dx * startRatio;
    const fy = firewall.y + dy * startRatio;
    const dxEnd = dmzSw.x - dx * endRatio;
    const dyEnd = dmzSw.y - dy * endRatio;

    const flows = rootSvg.append('g')
        .attr('class', 'firewall-dmz-flow')
        .attr('pointer-events', 'none');

    flows.append('path')
        .attr('class', 'firewall-dmz-arrow firewall-to-dmz')
        .attr('d', `M ${fx + nx} ${fy + ny} L ${dxEnd + nx} ${dyEnd + ny}`)
        .attr('fill', 'none')
        .attr('stroke', '#94a3b8')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '7,5')
        .attr('marker-end', 'url(#dmz-arrow-in)');

    flows.append('path')
        .attr('class', 'firewall-dmz-arrow dmz-to-firewall')
        .attr('d', `M ${dxEnd - nx} ${dyEnd - ny} L ${fx - nx} ${fy - ny}`)
        .attr('fill', 'none')
        .attr('stroke', '#94a3b8')
        .attr('stroke-width', 2.5)
        .attr('stroke-dasharray', '7,5')
        .attr('marker-end', 'url(#dmz-arrow-out)');
}

/** 分校区：与主校区相同的四层排布 */
function createCampus2Layout(layers, width, height) {
    const usableWidth = width - 2 * LAYOUT_PADDING;
    const usableHeight = height - 2 * LAYOUT_PADDING;
    const layerSpacing = usableHeight / 4;
    const yOffset = -28;

    const cs2 = layers.core.find(n => n.id === 'cs2');
    if (cs2) {
        cs2.x = width / 2 + 50;
        cs2.y = LAYOUT_PADDING + layerSpacing * 0.5 + yOffset;
    }

    const bridge = nodeMap['_to_main'];
    if (bridge && cs2) {
        bridge.x = cs2.x - 130;
        bridge.y = cs2.y;
    }

    const as4 = layers.agg.find(n => n.id === 'as4');
    if (as4) {
        as4.x = width / 2;
        as4.y = LAYOUT_PADDING + layerSpacing * 1.5 + yOffset;
    }

    const sw17 = layers.access.find(n => n.id === 'sw17');
    if (sw17) {
        sw17.x = width / 2;
        sw17.y = LAYOUT_PADDING + layerSpacing * 2.5 + yOffset;
    }

    const c2hosts = layers.hosts
        .filter(n => n.id.startsWith('c2h'))
        .sort((a, b) => a.id.localeCompare(b.id));
    layoutCampus2Hosts(
        c2hosts,
        sw17 ? sw17.x : width / 2,
        LAYOUT_PADDING + layerSpacing * 3.5 + yOffset,
        CAMPUS2_HOST_GAP
    );

    [...layers.core, ...layers.agg, ...layers.access, ...layers.hosts].forEach(node => {
        node.x += CAMPUS2_LAYOUT_OFFSET.x;
        node.y += CAMPUS2_LAYOUT_OFFSET.y;
    });
}

function switchTopologyPage(page) {
    topologyPage = page;
    if (window.topologyFullData) {
        renderTopology(window.topologyFullData);
    }
}

function updateCampusPageButtons() {
    const btnMain = document.getElementById('btnMainCampus');
    const btnC2 = document.getElementById('btnCampus2');
    if (!btnMain || !btnC2) return;
    const active = 'bg-blue-600 text-white';
    const inactive = 'bg-gray-100 text-gray-600 hover:bg-gray-200';
    btnMain.className = `px-3 py-1.5 rounded-lg text-xs font-medium transition ${topologyPage === 'main' ? active : inactive}`;
    btnC2.className = `px-3 py-1.5 rounded-lg text-xs font-medium transition ${topologyPage === 'campus2' ? active : inactive}`;
}

function computeHierarchy(data) {
    const layers = { core: [], agg: [], firewall: [], access: [], hosts: [] };
    data.nodes.forEach(node => {
        if (node.type === 'switch') {
            if (node.subtype === 'core') layers.core.push(node);
            else if (node.subtype === 'agg') layers.agg.push(node);
            else if (node.subtype === 'firewall') layers.firewall.push(node);
            else if (node.subtype === 'access') layers.access.push(node);
        } else if (node.type === 'host' || node.type === 'server' || node.type === 'bridge') {
            if (node.type !== 'bridge') layers.hosts.push(node);
        }
    });
    return layers;
}

function showTooltip(event, node) {
    hideTooltip();
    const tooltip = document.createElement('div');
    tooltip.id = 'nodeTooltip';
    tooltip.className = 'fixed z-50 bg-gray-900 text-white px-4 py-3 rounded-xl shadow-2xl min-w-52 text-sm';
    const nameCN = getNodeNameCN(node.id);
    tooltip.innerHTML = `
        <div class="font-bold text-base mb-2 border-b border-gray-700 pb-2">${nameCN}</div>
        <div class="space-y-1">
            <div class="flex justify-between gap-4"><span class="text-gray-400">ID:</span><span class="font-medium">${node.id}</span></div>
            <div class="flex justify-between gap-4"><span class="text-gray-400">类型:</span><span>${node.type}${node.subtype ? ' - ' + node.subtype : ''}</span></div>
            ${node.ip ? `<div class="flex justify-between gap-4"><span class="text-gray-400">IP:</span><span>${node.ip}</span></div>` : ''}
            ${node.vlan ? `<div class="flex justify-between gap-4"><span class="text-gray-400">VLAN:</span><span>${node.vlan}</span></div>` : ''}
            ${node.secure ? '<div class="text-red-400 mt-2 font-medium">🔒 安全区域</div>' : ''}
        </div>`;
    document.body.appendChild(tooltip);
    const rect = tooltip.getBoundingClientRect();
    let left = event.pageX + 15;
    let top = event.pageY - rect.height - 10;
    if (left + rect.width > window.innerWidth) left = event.pageX - rect.width - 15;
    if (top < 0) top = event.pageY + 15;
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
    d3.select(event.currentTarget).select('.node-circle')
        .transition().duration(200).attr('stroke', '#f59e0b').attr('stroke-width', 4);
}

function hideTooltip() {
    const t = document.getElementById('nodeTooltip');
    if (t) t.remove();
    d3.selectAll('.node-circle').transition().duration(200)
        .attr('stroke', d => d.secure ? '#dc2626' : '#ffffff')
        .attr('stroke-width', d => d.secure ? 4 : 3);
}

function getLinkBetween(idA, idB) {
    return linkMap[`${idA}-${idB}`] || linkMap[`${idB}-${idA}`];
}

function defaultLinkStyle(selection) {
    return selection
        .attr('stroke', d => {
            if (d.type === 'guest-peer') return '#a78bfa';
            if (d.type === 'direct-core') return '#38bdf8';
            if (d.type === 'guest-edge-ingress') return '#94a3b8';
            if (d.type === 'intercampus') return '#06b6d4';
            if (d.type === 'access') return '#cbd5e1';
            return '#94a3b8';
        })
        .attr('stroke-width', d => {
            if (d.type === 'guest-peer') return 2.5;
            if (d.type === 'guest-edge-ingress') return 2.5;
            if (d.type === 'access') return 1.5;
            return 2.5;
        })
        .attr('stroke-dasharray', d => {
            if (d.type === 'guest-peer') return '7,5';
            if (d.type === 'direct-core') return '6,4';
            if (d.type === 'guest-edge-ingress') return '0';
            if (d.type === 'intercampus') return '8,6';
            if (d.type === 'access') return '4,4';
            return '10,5';
        })
        .attr('opacity', d => d.type === 'guest-peer' ? 0.95 : 1);
}

function mapNodeForPage(nodeId, page) {
    if (page === 'main' && nodeId === 'cs2') return '_to_campus2';
    if (page === 'campus2' && nodeId === 'cs1') return '_to_main';
    return nodeId;
}

/** 将逻辑路径映射为当前页面可绘制的链路 */
function getDisplaySegments(logicalPath, page) {
    const segments = [];
    for (let i = 0; i < logicalPath.length - 1; i++) {
        const a = mapNodeForPage(logicalPath[i], page);
        const b = mapNodeForPage(logicalPath[i + 1], page);
        if (a === b) continue;
        if (!nodeMap[a] || !nodeMap[b] || !getLinkBetween(a, b)) continue;
        if (!Number.isFinite(nodeMap[a].x) || !Number.isFinite(nodeMap[b].x)) continue;
        segments.push({ a, b, logicalIdx: i });
    }
    return segments;
}

/** 查主机/服务器挂接的汇聚交换机 */
function getAggForNode(node, data) {
    if (!node || !data) return null;
    if (node.parentSw) {
        const sw = data.nodes.find(n => n.id === node.parentSw);
        if (sw && sw.parentAgg) return sw.parentAgg;
    }
    if (node.type === 'switch' && node.subtype === 'access' && node.parentAgg) {
        return node.parentAgg;
    }
    return null;
}

const HR_FINANCE_VLANS = new Set([50, 60]);

/** 目标是否人事/财务安全区 */
function isHrFinanceDest(node) {
    if (!node) return false;
    return node.secure === true || HR_FINANCE_VLANS.has(node.vlan)
        || node.vlanName === 'hr' || node.vlanName === 'finance';
}

/** 源是否人事/财务安全区 */
function isHrFinanceSrc(node) {
    if (!node) return false;
    return HR_FINANCE_VLANS.has(node.vlan)
        || node.vlanName === 'hr' || node.vlanName === 'finance';
}

/** 保密区禁止外出：DMZ/VPN/外网 */
function isSecureZoneEgressBlocked(srcNode, dstNode) {
    if (!isHrFinanceSrc(srcNode) || !dstNode) return false;
    if (dstNode.vlan === 110 || dstNode.id === 'vpn_srv') return true;
    if (dstNode.vlan === 250 || dstNode.vlanName === 'internet') return true;
    return false;
}

function isDmzLateralBlocked(srcNode, dstNode, srcId) {
    if (srcId !== 'dmz_web' || !dstNode) return false;
    return dstNode.vlan !== 110 && dstNode.vlan !== 250;
}

function isInternetIngressBlocked(srcNode, dstNode, dstId) {
    if (!srcNode || srcNode.vlan !== 250 || !dstNode) return false;
    if (dstNode.vlan === 250) return false;
    return dstId !== 'dmz_web';
}

/** 访客 WiFi 隔离岛：不得越过 sw13 上联 */
function isWifiIslandBlocked(srcNode, dstNode, srcId, dstId) {
    if (!WIFI_GUEST_IDS.has(srcId)) return false;
    if (WIFI_GUEST_IDS.has(dstId)) return false;
    return !!(srcNode && dstNode && needsL3Routing(srcNode, dstNode));
}

/** gst3 未连 VPN 直连内网：在 cs1 拒绝 */
function isGst3DirectBlocked(srcNode, dstNode, srcId) {
    if (srcId !== VPN_CAMPUS_CLIENT) return false;
    if (typeof isVPNEnabled === 'function' && isVPNEnabled()) return false;
    if (!srcNode || !dstNode || !needsL3Routing(srcNode, dstNode)) return false;
    if (!isInternalIp(dstNode.ip || '')) return false;
    if (dstNode.id === 'vpn_srv' || dstNode.id === 'dmz_web') return false;
    return true;
}

/**
 * 阻断点：
 * - 访客 WiFi 出岛：sw13
 * - gst3 未连 VPN：cs1 直连拒绝
 * - 宿舍等访人事/财务：as1
 * - 人事/财务外出 DMZ/外网：cs1
 */
function pickBlockNode(srcNode, dstNode, data, logicalPath, srcId, dstId) {
    if (!logicalPath.length) return null;

    if (isWifiIslandBlocked(srcNode, dstNode, srcId, dstId) && logicalPath.includes('sw13')) {
        return 'sw13';
    }

    if (isGst3DirectBlocked(srcNode, dstNode, srcId) && logicalPath.includes('fw1')) {
        return 'fw1';
    }

    if (isDmzLateralBlocked(srcNode, dstNode, srcId) && logicalPath.includes('fw1')) {
        return 'fw1';
    }

    if (isInternetIngressBlocked(srcNode, dstNode, dstId) && logicalPath.includes('fw1')) {
        return 'fw1';
    }

    if (isSecureZoneEgressBlocked(srcNode, dstNode) && logicalPath.includes('fw1')) {
        return 'fw1';
    }

    if (isHrFinanceDest(dstNode) && logicalPath.includes('as1')) {
        return 'as1';
    }

    if (logicalPath.includes('cs2')) return 'cs2';
    if (logicalPath.includes('cs1')) return 'cs1';

    const srcAgg = getAggForNode(srcNode, data);
    if (srcAgg && logicalPath.includes(srcAgg)) return srcAgg;
    return logicalPath[logicalPath.length - 2] || 'cs1';
}

function findBlockLinkIndex(logicalPath, srcId, dstId) {
    const data = window.topologyFullData;
    if (!data || !logicalPath.length) return -1;
    const srcNode = data.nodes.find(n => n.id === srcId);
    const dstNode = data.nodes.find(n => n.id === dstId);
    if (!srcNode || !dstNode) return logicalPath.length - 2;

    const blockNode = pickBlockNode(srcNode, dstNode, data, logicalPath, srcId, dstId);
    if (!blockNode) return logicalPath.length - 2;

    if (isWifiIslandBlocked(srcNode, dstNode, srcId, dstId) && blockNode === 'sw13') {
        for (let i = 0; i < logicalPath.length - 1; i++) {
            if (logicalPath[i] === 'sw13') return i;
        }
    }

    // ACL 在 cs1 执行：✕ 标在「进入 cs1」或「离开 cs1 去外网/DMZ」的链路上
    if (blockNode === 'cs1' && logicalPath.includes('cs1')) {
        if (isGst3DirectBlocked(srcNode, dstNode, srcId)) {
            for (let i = 0; i < logicalPath.length - 1; i++) {
                if (logicalPath[i + 1] === 'cs1') return i;
            }
        }
        if (isSecureZoneEgressBlocked(srcNode, dstNode)) {
            for (let i = 0; i < logicalPath.length - 1; i++) {
                if (logicalPath[i] === 'cs1') return i;
            }
        }
    }

    if (blockNode === 'fw1' && logicalPath.includes('fw1')) {
        for (let i = 0; i < logicalPath.length - 1; i++) {
            if (logicalPath[i + 1] === 'fw1') return i;
        }
    }

    // 人事/财务：叉画在 as1 通往目标接入交换机出口
    if (isHrFinanceDest(dstNode) && dstNode.parentSw && blockNode === 'as1') {
        const sw = dstNode.parentSw;
        for (let i = 0; i < logicalPath.length - 1; i++) {
            if (logicalPath[i] === 'as1' && logicalPath[i + 1] === sw) return i;
        }
    }

    for (let i = 0; i < logicalPath.length - 1; i++) {
        if (logicalPath[i + 1] === blockNode) return i;
    }

    const idx = logicalPath.indexOf(blockNode);
    if (idx >= 0 && idx < logicalPath.length - 1) return idx;
    return logicalPath.length - 2;
}

function removeBlockMarkers() {
    if (svg) svg.selectAll('g.block-markers').remove();
}

function drawBlockMarker(segA, segB) {
    const nA = nodeMap[segA];
    const nB = nodeMap[segB];
    if (!nA || !nB) return;
    const mx = (nA.x + nB.x) / 2;
    const my = (nA.y + nB.y) / 2;
    if (!svg) return;
    const g = svg.append('g').attr('class', 'block-markers');
    g.append('circle')
        .attr('cx', mx).attr('cy', my).attr('r', 14)
        .attr('fill', '#fff').attr('stroke', '#dc2626').attr('stroke-width', 3);
    g.append('text')
        .attr('x', mx).attr('y', my + 1)
        .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
        .attr('fill', '#dc2626').attr('font-size', '18px').attr('font-weight', 'bold')
        .attr('pointer-events', 'none')
        .text('✕');
}

function drawNodeBlockMarker(nodeId) {
    const node = nodeMap[nodeId];
    if (!node || !svg) return;
    const x = node.x - 34;
    const y = node.y + 30;
    const g = svg.append('g').attr('class', 'block-markers');
    g.append('circle')
        .attr('cx', x).attr('cy', y).attr('r', 14)
        .attr('fill', '#fff').attr('stroke', '#dc2626').attr('stroke-width', 3);
    g.append('text')
        .attr('x', x).attr('y', y + 1)
        .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
        .attr('fill', '#dc2626').attr('font-size', '18px').attr('font-weight', 'bold')
        .attr('pointer-events', 'none')
        .text('\u00d7');
}

function setDmzFlowStyle(color = '#94a3b8', dash = '7,5', opacity = 1) {
    if (!svg) return;
    svg.selectAll('.dmz-flow-arrow')
        .attr('stroke', color)
        .attr('stroke-width', color === '#94a3b8' ? 2.5 : 4)
        .attr('stroke-dasharray', dash)
        .attr('opacity', opacity);
}

function setFirewallDmzFlowStyle(direction, color = '#94a3b8', dash = '7,5', opacity = 1) {
    if (!svg) return;
    const selector = direction === 'in'
        ? '.firewall-to-dmz'
        : (direction === 'out' ? '.dmz-to-firewall' : '.firewall-dmz-arrow');
    svg.selectAll(selector)
        .attr('stroke', color)
        .attr('stroke-width', color === '#94a3b8' ? 2.5 : 4)
        .attr('stroke-dasharray', dash)
        .attr('opacity', opacity);
}

function highlightPathOnTopology(src, dst, success) {
    lastPathHighlight = { src, dst, success };
    applyPathHighlight();
}

function applyPathHighlight() {
    if (!lastPathHighlight) return;

    const { src, dst, success } = lastPathHighlight;
    const logicalPath = findPathIds(src, dst);

    if (!svg || !logicalPath.length) return;

    const data = window.topologyFullData;
    const srcNode = data && data.nodes.find(n => n.id === src);
    const dstNode = data && data.nodes.find(n => n.id === dst);

    removeBlockMarkers();
    defaultLinkStyle(d3.selectAll('.link').transition().duration(300));
    setDmzFlowStyle();
    setFirewallDmzFlowStyle();

    const segments = getDisplaySegments(logicalPath, topologyPage);
    if (!segments.length) return;

    const color = success ? '#16a34a' : '#dc2626';
    const visibleNodes = new Set();
    segments.forEach(s => { visibleNodes.add(s.a); visibleNodes.add(s.b); });
    visibleNodes.add(src);
    visibleNodes.add(dst);

    const usesDmzVpnLeg = logicalPath.some((id, i) =>
        i < logicalPath.length - 1 &&
        ((id === 'vpn_srv' && logicalPath[i + 1] === 'sw15') ||
         (id === 'sw15' && logicalPath[i + 1] === 'vpn_srv'))
    );
    if (usesDmzVpnLeg) {
        setDmzFlowStyle(color, success ? '0' : '6,4', success ? 1 : 0.8);
    }

    const usesFirewallToDmz = logicalPath.some((id, i) =>
        id === 'fw1' && logicalPath[i + 1] === 'sw15'
    );
    const usesDmzToFirewall = logicalPath.some((id, i) =>
        id === 'sw15' && logicalPath[i + 1] === 'fw1'
    );
    if (usesFirewallToDmz) {
        setFirewallDmzFlowStyle('in', color, success ? '0' : '6,4', success ? 1 : 0.8);
    }
    if (usesDmzToFirewall) {
        setFirewallDmzFlowStyle('out', color, success ? '0' : '6,4', success ? 1 : 0.8);
    }

    const blockIdx = success ? -1 : findBlockLinkIndex(logicalPath, src, dst);

    segments.forEach(seg => {
        const link = getLinkBetween(seg.a, seg.b);
        if (!link) return;
        const isBlockLink = !success && seg.logicalIdx === blockIdx;
        const isAfterBlock = !success && blockIdx >= 0 && seg.logicalIdx > blockIdx;
        const dash = (isBlockLink || isAfterBlock) ? '6,4' : '0';
        d3.selectAll('.link')
            .filter(d => (d.source === link.source && d.target === link.target) ||
                         (d.source === link.target && d.target === link.source))
            .transition().duration(300)
            .attr('stroke', isAfterBlock ? '#f87171' : color)
            .attr('stroke-width', isBlockLink ? 5 : (isAfterBlock ? 3 : 4))
            .attr('stroke-dasharray', dash)
            .attr('opacity', isAfterBlock ? 0.75 : 1);
        if (isBlockLink) {
            drawBlockMarker(seg.a, seg.b);
        }
    });

    d3.selectAll('.nodes > g.node')
        .transition().duration(300)
        .attr('opacity', d => visibleNodes.has(d.id) ? 1 : 0.2);
}

function buildAdjacency(data) {
    const adj = {};
    data.nodes.forEach(n => { adj[n.id] = []; });
    data.links.forEach(l => {
        if (!adj[l.source]) adj[l.source] = [];
        if (!adj[l.target]) adj[l.target] = [];
        adj[l.source].push(l.target);
        adj[l.target].push(l.source);
    });
    return adj;
}

/** BFS 最短路径 */
function bfsPath(adj, srcId, dstId) {
    if (!srcId || !dstId) return [];
    if (srcId === dstId) return [srcId];

    const queue = [[srcId]];
    const visited = new Set([srcId]);

    while (queue.length) {
        const path = queue.shift();
        const cur = path[path.length - 1];
        for (const next of adj[cur] || []) {
            if (visited.has(next)) continue;
            visited.add(next);
            const newPath = path.concat(next);
            if (next === dstId) return newPath;
            queue.push(newPath);
        }
    }
    return [];
}

/** 同 VLAN 可二层直达 */
function needsL3Routing(srcNode, dstNode) {
    if (!srcNode || !dstNode) return false;
    if (srcNode.campus !== dstNode.campus) return true;
    if (srcNode.vlan != null && dstNode.vlan != null && srcNode.vlan !== dstNode.vlan) {
        return true;
    }
    return false;
}

/**
 * 三层路径是否经核心 cs1：
 * - 同汇聚（访客↔宿舍、宿舍 A↔B）→ 汇聚交换机直接路由，不上核心
 * - 跨汇聚 / 跨校区 → 经 cs1
 */
function needsCoreInPath(srcNode, dstNode, data) {
    if (!needsL3Routing(srcNode, dstNode)) return false;
    if (srcNode.campus === 2 || dstNode.campus === 2) return true;

    const srcAgg = getAggForNode(srcNode, data);
    const dstAgg = getAggForNode(dstNode, data);
    if (srcAgg && dstAgg && srcAgg === dstAgg) return false;

    return true;
}

function getLinkType(data, a, b) {
    const link = data.links.find(l =>
        (l.source === a && l.target === b) || (l.source === b && l.target === a)
    );
    return link ? link.type : null;
}

/** Condensed security-flow edges may be displayed without exposing hidden hops. */
function isLayer2Shortcut(data, path) {
    if (!path || path.length < 2) return false;
    if (path.length === 2) {
        const t = getLinkType(data, path[0], path[1]);
        return t === 'guest-edge-ingress';
    }
    return false;
}

/** gst3 security flow: edge -> DMZ -> VPN -> DMZ -> internal network. */
function findGst3CrossVlanPath(adj, srcId, dstId, srcNode, dstNode) {
    if (srcId !== VPN_CAMPUS_CLIENT || !srcNode || !dstNode) return null;
    if (!needsL3Routing(srcNode, dstNode)) {
        const direct = bfsPath(adj, srcId, dstId);
        return direct.length ? direct : null;
    }
    if (!isInternalIp(dstNode.ip || '')) return null;
    if (dstNode.id === 'vpn_srv') {
        return ['gst3', 'sw18', 'fw1', 'sw15', 'vpn_srv'];
    }
    if (dstNode.id === 'dmz_web') {
        return ['gst3', 'sw18', 'fw1', 'sw15', 'dmz_web'];
    }
    const cs1ToDst = bfsPath(adj, 'cs1', dstId);
    if (!cs1ToDst.length) return null;

    const vpnOn = typeof isVPNEnabled === 'function' && isVPNEnabled();
    if (vpnOn) {
        return ['gst3', 'sw18', 'fw1', 'sw15', 'vpn_srv', 'sw15', 'fw1', 'cs1']
            .concat(cs1ToDst.slice(1));
    } else {
        return ['gst3', 'sw18', 'fw1'];
    }
}

function findPathIds(srcId, dstId) {
    const data = window.topologyFullData;
    if (!data || !srcId || !dstId) return [];
    if (srcId === dstId) return [srcId];

    const adj = buildAdjacency(data);
    const srcNode = data.nodes.find(n => n.id === srcId);
    const dstNode = data.nodes.find(n => n.id === dstId);

    // 访客 WiFi 出岛：路径止于 sw13
    if (isWifiIslandBlocked(srcNode, dstNode, srcId, dstId)) {
        const toSw = bfsPath(adj, srcId, 'sw13');
        if (toSw.length) return toSw;
    }

    const gst3Path = findGst3CrossVlanPath(adj, srcId, dstId, srcNode, dstNode);
    if (gst3Path) return gst3Path;

    // 同 VLAN / 同校区二层可达（gst1↔gst2 经 sw13 交换机转发）
    if (!needsL3Routing(srcNode, dstNode)) {
        const direct = bfsPath(adj, srcId, dstId);
        return direct.length ? direct : [srcId, dstId];
    }

    // Condensed security-flow edges are allowed to bypass hidden display hops.
    const tunnelTry = bfsPath(adj, srcId, dstId);
    if (isLayer2Shortcut(data, tunnelTry)) {
        return tunnelTry;
    }

    // 跨 VLAN 三层：必经汇聚或核心（禁止 as3 直连 sw14 绕过 cs1）
    if (srcNode.campus === 2 || dstNode.campus === 2) {
        const up = bfsPath(adj, srcId, 'cs1');
        const mid = bfsPath(adj, 'cs1', 'cs2');
        const down = bfsPath(adj, 'cs2', dstId);
        if (up.length && mid.length && down.length) {
            return up.concat(mid.slice(1), down.slice(1));
        }
    }

    if (!needsCoreInPath(srcNode, dstNode, data)) {
        const agg = getAggForNode(srcNode, data);
        const up = bfsPath(adj, srcId, agg);
        const down = bfsPath(adj, agg, dstId);
        if (up.length && down.length) {
            return up.concat(down.slice(1));
        }
    }

    const up = bfsPath(adj, srcId, 'cs1');
    const down = bfsPath(adj, 'cs1', dstId);
    if (up.length && down.length) {
        return up.concat(down.slice(1));
    }

    return [srcId, dstId];
}

function highlightACLOnTopology() {
    d3.selectAll('.link').transition().duration(500)
        .attr('stroke', '#f59e0b').attr('stroke-width', 3);
}

function clearTopology() {
    lastPathHighlight = null;
    removeBlockMarkers();
    if (svg) {
        defaultLinkStyle(d3.selectAll('.link').transition().duration(300));
        setDmzFlowStyle();
        setFirewallDmzFlowStyle();
        d3.selectAll('.nodes > g.node').transition().duration(300).attr('opacity', 1);
    }
}

window.renderTopology = renderTopology;
window.topologyPage = topologyPage;
window.switchTopologyPage = switchTopologyPage;
window.highlightPathOnTopology = highlightPathOnTopology;
window.highlightACLOnTopology = highlightACLOnTopology;
window.clearTopology = clearTopology;
