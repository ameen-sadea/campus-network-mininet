const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const context = { window: {}, console };
vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/js/topology_data.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/js/topology.js', 'utf8'), context);

const result = vm.runInContext(`(() => {
    const full = generateTopology();
    window.topologyFullData = full;
    const page = buildPageData(full, 'main');

    nodeMap = {};
    full.nodes.forEach(node => { nodeMap[node.id] = node; });
    page.nodes.forEach(node => { nodeMap[node.id] = node; });
    createOriginalLayout(computeHierarchy(page), 1600, 660);

    setVPNEnabled(false);
    const offPath = findPathIds('gst3', 'dB1');
    const portalOff = checkACLBlock(
        full.nodes.find(node => node.id === 'gst3'),
        full.nodes.find(node => node.id === 'dmz_web'),
        'gst3',
        'dmz_web'
    );

    setVPNEnabled(true);
    const onPath = findPathIds('gst3', 'dB1');
    const hrToInternet = checkACLBlock(
        full.nodes.find(node => node.id === 'hr1'),
        full.nodes.find(node => node.id === 'ext_web'),
        'hr1',
        'ext_web'
    );
    const hrToPortal = checkACLBlock(
        full.nodes.find(node => node.id === 'hr1'),
        full.nodes.find(node => node.id === 'dmz_web'),
        'hr1',
        'dmz_web'
    );
    const dormToInternet = checkACLBlock(
        full.nodes.find(node => node.id === 'dA1'),
        full.nodes.find(node => node.id === 'ext_web'),
        'dA1',
        'ext_web'
    );
    const internetToDorm = checkACLBlock(
        full.nodes.find(node => node.id === 'ext_web'),
        full.nodes.find(node => node.id === 'dA1'),
        'ext_web',
        'dA1'
    );
    const portalToGuest = checkACLBlock(
        full.nodes.find(node => node.id === 'dmz_web'),
        full.nodes.find(node => node.id === 'gst3'),
        'dmz_web',
        'gst3'
    );
    const internetToPortal = checkACLBlock(
        full.nodes.find(node => node.id === 'ext_web'),
        full.nodes.find(node => node.id === 'dmz_web'),
        'ext_web',
        'dmz_web'
    );
    const internetToInternalWeb = checkACLBlock(
        full.nodes.find(node => node.id === 'ext_web'),
        full.nodes.find(node => node.id === 'web'),
        'ext_web',
        'web'
    );
    const internetPath = findPathIds('ext_web', 'web');

    return {
        page,
        offPath,
        onPath,
        portalOff,
        hrToInternet,
        hrToPortal,
        dormToInternet,
        internetToDorm,
        portalToGuest,
        internetToPortal,
        internetToInternalWeb,
        internetPath,
        positions: Object.fromEntries(
            ['ftp', 'gst3', 'sw15', 'dmz_web', 'vpn_srv', 'fw1', 'sw18', 'ext_web'].map(id => [
                id,
                { x: nodeMap[id].x, y: nodeMap[id].y },
            ])
        ),
    };
})()`, context);

assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('gst3') &&
        [link.source, link.target].includes('cs1')
    ),
    false,
    'The main page must not invent a gst3-cs1 cable.'
);
assert.deepEqual(result.offPath, ['gst3', 'sw18', 'fw1']);
assert.deepEqual(
    result.onPath,
    ['gst3', 'sw18', 'fw1', 'sw15', 'vpn_srv', 'sw15', 'fw1', 'cs1', 'as2', 'sw9', 'dB1']
);
assert.equal(result.portalOff.blocked, false);
assert.ok(result.positions.sw15.x - result.positions.ftp.x >= 180);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('gst3') &&
        [link.source, link.target].includes('vpn_srv')
    ),
    false,
    'gst3 must enter through the DMZ boundary rather than connect to VPN directly.'
);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('gst3') &&
        [link.source, link.target].includes('sw18') &&
        link.type === 'guest-edge-ingress'
    ),
    true
);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('ext_web') &&
        [link.source, link.target].includes('sw15')
    ),
    false,
    'The external website must not be attached to the DMZ.'
);
assert.equal(result.hrToInternet.blocked, true);
assert.equal(result.hrToPortal.blocked, false);
assert.equal(result.hrToPortal.whitelist, true);
assert.equal(result.dormToInternet.blocked, false);
assert.equal(result.internetToDorm.blocked, true);
assert.equal(result.portalToGuest.blocked, true);
assert.equal(result.internetToPortal.blocked, false);
assert.equal(result.internetToPortal.whitelist, true);
assert.equal(result.internetToInternalWeb.blocked, true);
assert.ok(result.internetPath.includes('fw1'));
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('cs1') &&
        [link.source, link.target].includes('sw18')
    ),
    false,
    'The Internet zone must not connect directly to cs1.'
);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('as3') &&
        [link.source, link.target].includes('sw15')
    ),
    false,
    'The DMZ must terminate on the edge firewall rather than an internal aggregation switch.'
);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('fw1') &&
        [link.source, link.target].includes('sw15')
    ),
    true
);
assert.equal(
    result.page.links.some(link =>
        [link.source, link.target].includes('fw1') &&
        [link.source, link.target].includes('sw18')
    ),
    true
);
assert.equal(result.positions.gst3.x, result.positions.sw18.x);
assert.ok(result.positions.gst3.y < result.positions.sw18.y);
assert.equal(result.positions.vpn_srv.y, result.positions.sw15.y);
assert.ok(result.positions.sw18.y < result.positions.sw15.y);

console.log('topology logic regression checks passed');
