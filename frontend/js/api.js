/**
 * API Client - 优先连接 Mininet 后端，离线时回退本地模拟
 */

const API_BASE = (() => {
    if (window.MININET_API_BASE) return String(window.MININET_API_BASE).replace(/\/$/, '');
    const q = new URLSearchParams(window.location.search);
    const fromQuery = q.get('api');
    if (fromQuery) return fromQuery.replace(/\/$/, '');
    return 'http://localhost:5000';
})();
const CONTROL_TOKEN = window.CAMPUS_API_TOKEN || 'campus-demo-control-v2';
const STATUS_TIMEOUT_MS = 1200;  // 探测后端，宜短，避免单独开前端时卡顿
const TEST_TIMEOUT_MS = 20000;   // Mininet 真测可能较慢

// 默认 false：单独开前端即可用；探测成功后才切到 Mininet
let backendOnline = false;
let backendProbeDone = false;

const API_PROBE_ENABLED = (() => {
    if (window.ENABLE_MININET_API === false) return false;
    const q = new URLSearchParams(window.location.search);
    if (q.get('simulate') === '1') return false;
    return true;
})();

function apiDebug(msg, type = 'info') {
    console.log('[API] ' + msg);
    if (typeof window.appendApiLog === 'function') {
        window.appendApiLog(msg, type);
    }
}

async function fetchBackend(path, timeoutMs = TEST_TIMEOUT_MS, options = {}) {
    const url = `${API_BASE}${path}`;
    const method = String(options.method || 'GET').toUpperCase();
    apiDebug(`→ ${method} ${path}`, 'request');
    const t0 = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        const ms = Math.round(performance.now() - t0);
        const raw = await res.text();
        let data = null;
        try {
            data = raw ? JSON.parse(raw) : {};
        } catch (_) {
            data = null;
        }
        if (!res.ok) {
            apiDebug(`← HTTP ${res.status} ${path} (${ms}ms)`, 'error');
            throw new Error(data?.error || `HTTP ${res.status}`);
        }
        if (!data) throw new Error('Invalid JSON response');
        apiDebug(`← 200 ${path} (${ms}ms) [Mininet]`, 'success');
        return data;
    } catch (e) {
        const ms = Math.round(performance.now() - t0);
        const reason = e.name === 'AbortError' ? '超时' : e.message;
        apiDebug(`✗ ${path} (${ms}ms): ${reason}`, 'error');
        throw e;
    } finally {
        clearTimeout(timer);
    }
}

/**
 * 探测 Mininet API（支持重试，等待 WSL 中 Mininet 建网完成）
 */
async function checkBackend(maxRetries = 1, retryIntervalMs = 0) {
    backendProbeDone = false;
    if (!API_PROBE_ENABLED) {
        backendOnline = false;
        backendProbeDone = true;
        apiDebug('已禁用 Mininet 探测 (?simulate=1)，纯前端模拟', 'simulate');
        return null;
    }
    apiDebug(`探测 Mininet API (${API_BASE})…`, 'info');
    let lastErr = null;
    try {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            if (attempt > 1) {
                apiDebug(`等待 API… 第 ${attempt}/${maxRetries} 次`, 'info');
                await new Promise(r => setTimeout(r, retryIntervalMs));
            }
            try {
                const data = await fetchBackend('/api/status', STATUS_TIMEOUT_MS);
                backendOnline = !!data.online;
                if (backendOnline) {
                    apiDebug(`后端在线 ${data.version ? `v${data.version}` : ''} — ${data.message || 'campus_network.py --api'}`, 'success');
                } else {
                    apiDebug('后端响应 online=false，使用本地模拟', 'warn');
                }
                return data;
            } catch (e) {
                lastErr = e;
            }
        }
        backendOnline = false;
        apiDebug(`后端不可达 (${lastErr?.message || 'timeout'})，回退本地模拟`, 'simulate');
        return null;
    } finally {
        backendProbeDone = true;
    }
}

function isBackendOnline() {
    return backendOnline;
}

function isBackendProbeDone() {
    return backendProbeDone;
}

function isVpnOn() {
    return typeof isVPNEnabled === 'function' && isVPNEnabled();
}

function vpnQueryParam() {
    return `&vpn=${isVpnOn() ? '1' : '0'}`;
}

async function syncVpnClient() {
    if (!backendOnline) {
        apiDebug('vpn-sync 跳过（后端离线）', 'simulate');
        return;
    }
    try {
        const path = '/api/vpn-sync';
        const result = await fetchBackend(path, TEST_TIMEOUT_MS, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Campus-Token': CONTROL_TOKEN,
            },
            body: JSON.stringify({ enabled: isVpnOn() }),
        });
        if (!result.success) throw new Error(result.error || 'VPN policy apply failed');
        apiDebug(`vpn-sync 已同步 gst3 VPN=${isVpnOn() ? '开' : '关'}`, 'success');
        return result;
    } catch (e) {
        apiDebug('vpn-sync 失败: ' + e.message, 'error');
        throw e;
    }
}

/**
 * 获取网络拓扑（始终从本地 topology_data.js 生成，用于绘图）
 */
async function getTopology() {
    try {
        const topologyData = generateTopology();
        apiDebug(`拓扑数据已生成 (${topologyData.nodes.length} 节点, 本地)`, 'info');
        return topologyData;
    } catch (e) {
        apiDebug('getTopology 失败: ' + e.message, 'error');
        throw e;
    }
}

/**
 * Ping：后端在线时走 Mininet，否则本地模拟
 */
async function ping(src, dst, count = 1) {
    const topologyData = generateTopology();
    const path = `/api/ping?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}&count=${count}${vpnQueryParam()}`;

    if (backendOnline) {
        try {
            const result = await fetchBackend(path);
            apiDebug(`ping ${src}→${dst} 结果: ${result.success ? '成功' : '阻断'} [Mininet]`, result.success ? 'success' : 'warn');
            return result;
        } catch (e) {
            backendOnline = false;
            apiDebug('ping 后端失败，回退模拟', 'simulate');
        }
    }
    const result = simulatePing(src, dst, topologyData);
    result.source = 'simulate';
    apiDebug(`ping ${src}→${dst} 结果: ${result.success ? '成功' : '阻断'} [模拟]`, result.success ? 'success' : 'warn');
    return result;
}

/**
 * HTTP：后端在线时走 Mininet curl，否则本地模拟
 */
async function httpGet(src, dstHost = 'web') {
    const path = `/api/http?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dstHost)}${vpnQueryParam()}`;

    if (backendOnline) {
        try {
            const result = await fetchBackend(path);
            apiDebug(`http ${src}→${dstHost}: ${result.success ? '200' : '失败'} [Mininet]`, result.success ? 'success' : 'warn');
            return result;
        } catch (e) {
            backendOnline = false;
            apiDebug('http 后端失败，回退模拟', 'simulate');
        }
    }
    const result = simulateHTTP(src, dstHost);
    result.source = 'simulate';
    apiDebug(`http ${src}→${dstHost}: ${result.success ? '200' : '失败'} [模拟]`, result.success ? 'success' : 'warn');
    return result;
}

/**
 * FTP：后端在线时走 Mininet curl，否则本地模拟
 */
async function ftpGet(src, dstHost = 'ftp') {
    const path = `/api/ftp?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dstHost)}${vpnQueryParam()}`;

    if (backendOnline) {
        try {
            const result = await fetchBackend(path);
            apiDebug(`ftp ${src}→${dstHost}: ${result.success ? 'OK' : '失败'} [Mininet]`, result.success ? 'success' : 'warn');
            return result;
        } catch (e) {
            backendOnline = false;
            apiDebug('ftp 后端失败，回退模拟', 'simulate');
        }
    }
    const result = simulateFTP(src, dstHost);
    result.source = 'simulate';
    apiDebug(`ftp ${src}→${dstHost}: ${result.success ? 'OK' : '失败'} [模拟]`, result.success ? 'success' : 'warn');
    return result;
}

/**
 * VPN 状态由前端维护；gst3 策略通过 /api/vpn-sync 同步到 Mininet
 */
async function fetchVPNStatus() {
    return getVPNStatus();
}

async function setVPNTunnelEnabled(enabled) {
    const previous = isVpnOn();
    setVPNEnabled(enabled);
    apiDebug(`VPN 开关 → ${enabled ? '开' : '关'}`, 'info');
    if (backendOnline) {
        try {
            const result = await syncVpnClient();
            setVPNEnabled(!!result.enabled);
        } catch (error) {
            setVPNEnabled(previous);
            throw error;
        }
    }
    return getVPNStatus();
}

async function getSecurityMetrics() {
    if (backendOnline) {
        return fetchBackend('/api/security-metrics');
    }
    return {
        success: true,
        source: 'simulate',
        total_hits: 0,
        flows: [],
        note: '离线模拟不提供内核流表计数',
    };
}

async function getObservability(force = false) {
    if (!backendOnline) {
        return {
            success: false,
            source: 'unavailable',
            error: 'Mininet backend offline; live metrics are not simulated.',
        };
    }
    const path = force ? '/api/observability?force=1' : '/api/observability';
    return fetchBackend(path, TEST_TIMEOUT_MS);
}

/**
 * ACL 规则展示（本地数据）
 */
async function getACLStatus() {
    return {
        'switch': 'cs1',
        'flows': [
            'priority=615,ip,nw_src=172.16.0.0/30,nw_dst=10.0.50.0/24,actions=drop',
            'priority=614,ip,nw_src=172.16.0.0/30,nw_dst=10.0.60.0/24,actions=drop',
            'priority=608,ip,nw_src=172.16.0.0/30,nw_dst=10.0.0.0/8,actions=normal',
            'priority=623,ip,nw_src=10.0.91.0/24,nw_dst=10.0.110.10/32,actions=normal',
            'priority=629,ip,nw_src=10.0.50.0/24,nw_dst=10.0.110.20/32,actions=normal',
            'priority=629,ip,nw_src=10.0.60.0/24,nw_dst=10.0.110.20/32,actions=normal',
            'iptables/FORWARD conntrack ESTABLISHED,RELATED -> ACCEPT',
            'iptables/FORWARD NEW Internet/DMZ -> campus internal -> DROP',
            'priority=607,ip,nw_src=10.0.10.0/24,nw_dst=10.0.50.0/24,actions=drop',
            'priority=606,ip,nw_src=10.0.11.0/24,nw_dst=10.0.50.0/24,actions=drop',
            'priority=605,ip,nw_src=10.0.10.0/24,nw_dst=10.0.60.0/24,actions=drop',
            'priority=604,ip,nw_src=10.0.11.0/24,nw_dst=10.0.60.0/24,actions=drop',
            'priority=603,ip,nw_src=10.0.91.0/24,nw_dst=10.0.0.0/8,actions=drop',
            'priority=612,ip,nw_src=10.0.50.0/24,nw_dst=10.0.110.0/24,actions=drop',
            'priority=613,ip,nw_src=10.0.60.0/24,nw_dst=10.0.110.0/24,actions=drop',
            'priority=616,ip,nw_src=10.0.50.0/24,nw_dst=203.0.113.0/24,actions=drop',
            'priority=617,ip,nw_src=10.0.60.0/24,nw_dst=203.0.113.0/24,actions=drop',
            'priority=618,ip,nw_src=10.0.50.0/24,nw_dst=172.16.0.0/30,actions=drop',
            'priority=619,ip,nw_src=10.0.60.0/24,nw_dst=172.16.0.0/30,actions=drop',
            'priority=602,ip,nw_src=10.0.10.0/24,nw_dst=10.0.100.0/24,actions=normal',
            'priority=602,ip,nw_src=10.0.11.0/24,nw_dst=10.0.100.0/24,actions=normal',
            'priority=1,ip,nw_src=0.0.0.0/0,nw_dst=0.0.0.0/0,actions=normal',
        ],
        'aclRules': ACL_RULES,
    };
}

async function exec(node, command) {
    if (backendOnline) {
        return {
            'node': node,
            'command': command,
            'output': '请使用 /api/ping、/api/http、/api/ftp 接口',
            'note': 'Mininet API 模式',
        };
    }
    return {
        'node': node,
        'command': command,
        'output': '演示模式下不支持远程命令执行',
        'note': '如需真实测试，请在 Linux/WSL 中运行: sudo python3 campus_network.py --api',
    };
}

window.api = {
    API_BASE,
    checkBackend,
    isBackendOnline,
    isBackendProbeDone,
    syncVpnClient,
    getTopology,
    ping,
    httpGet,
    ftpGet,
    getVPNStatus: fetchVPNStatus,
    setVPNTunnelEnabled,
    getSecurityMetrics,
    getObservability,
    getACLStatus,
    exec,
};
