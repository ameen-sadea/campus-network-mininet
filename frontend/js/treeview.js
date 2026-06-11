/**
 * Tree View - 树状结构展示
 */

function renderTreeView(data) {
    const container = document.getElementById('treeView');
    container.innerHTML = '';

    const tree = { label: '校园网络', expanded: true, children: [] };

    // 核心层
    const coreNode = { label: '核心层', icon: 'fa-server', expanded: false, children: [] };
    data.nodes.filter(n => n.type === 'switch' && n.subtype === 'core').forEach(node => {
        coreNode.children.push({ label: node.id, icon: 'fa-circle', type: 'core', detail: node.vlans ? `VLANs: ${node.vlans.join(', ')}` : '' });
    });
    if (coreNode.children.length > 0) tree.children.push(coreNode);

    // 汇聚层
    const aggNode = { label: '汇聚层', icon: 'fa-project-diagram', expanded: true, children: [] };
    data.nodes.filter(n => n.type === 'switch' && n.subtype === 'agg').forEach(node => {
        const aggItem = { label: node.id, icon: 'fa-circle', type: 'agg', detail: node.vlans ? `VLANs: ${node.vlans.join(', ')}` : '', children: [] };
        const accSwitches = data.nodes.filter(n => n.type === 'switch' && n.subtype === 'access' &&
            data.links.some(l => (l.source === node.id || l.target === node.id) && (l.source === n.id || l.target === n.id)));
        accSwitches.forEach(acc => {
            const vlanNames = acc.vlans ? acc.vlans.join(', ') : '';
            aggItem.children.push({ label: acc.id, icon: 'fa-circle', type: 'access', detail: vlanNames ? `VLAN: ${vlanNames}` : '' });
        });
        aggNode.children.push(aggItem);
    });
    if (aggNode.children.length > 0) tree.children.push(aggNode);

    // 主机层
    const hostNode = { label: '终端设备', icon: 'fa-desktop', expanded: true, children: [] };
    const hostsByVlan = {};
    data.nodes.filter(n => n.type === 'host' || n.type === 'server').forEach(h => {
        const vlanId = h.vlan || h.vlans?.[0];
        if (!hostsByVlan[vlanId]) hostsByVlan[vlanId] = [];
        hostsByVlan[vlanId].push(h);
    });
    Object.entries(hostsByVlan).forEach(([vlanId, hosts]) => {
        const vlanGroup = { label: `VLAN ${vlanId}`, icon: 'fa-layer-group', children: [] };
        hosts.forEach(h => {
            const cnName = window.NODE_NAMES_CN ? window.NODE_NAMES_CN[h.id] || h.id : h.id;
            vlanGroup.children.push({ label: cnName, icon: h.type === 'server' ? 'fa-hdd' : 'fa-laptop', type: h.type === 'server' ? 'server' : 'host', detail: h.ip, secure: h.secure });
        });
        hostNode.children.push(vlanGroup);
    });
    if (hostNode.children.length > 0) tree.children.push(hostNode);

    container.innerHTML = renderTreeNode(tree, 0);
}

function renderTreeNode(node, level) {
    let html = '';
    const hasChildren = node.children && node.children.length > 0;
    const typeClass = node.type || '';

    const typeColors = { core: 'text-blue-600', agg: 'text-purple-600', access: 'text-gray-600', host: 'text-green-600', server: 'text-orange-600' };
    const typeBg = { core: 'bg-blue-50', agg: 'bg-purple-50', access: 'bg-gray-50', host: 'bg-green-50', server: 'bg-orange-50' };

    html += `<div class="tree-node level-${level} py-1">`;
    const clickHandler = hasChildren ? `onclick="toggleTree(this)"` : '';
    const icon = node.icon ? `<i class="fas ${node.icon} ${typeColors[typeClass] || 'text-gray-500'}"></i>` : '';

    html += `<div class="tree-item ${typeBg[typeClass] || ''} rounded-lg px-2 py-1.5 cursor-pointer hover:bg-gray-100 transition" ${clickHandler}>`;

    if (hasChildren) {
        html += `<span class="tree-toggle inline-block w-5 text-center text-gray-400">`;
        html += node.expanded ? '<i class="fas fa-chevron-down text-xs"></i>' : '<i class="fas fa-chevron-right text-xs"></i>';
        html += `</span>`;
    } else {
        html += `<span class="tree-toggle inline-block w-5"></span>`;
    }

    html += `<span class="tree-label ${typeColors[typeClass] || ''} font-medium text-sm">${icon} <span class="ml-1">${node.label}</span></span>`;

    if (node.detail) {
        html += `<span class="tree-detail text-xs text-gray-400 ml-2">${node.detail}</span>`;
    }
    if (node.secure) {
        html += `<span class="ml-2 text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded">🔒</span>`;
    }

    html += `</div>`;

    if (hasChildren) {
        const childDisplay = node.expanded ? 'block' : 'none';
        html += `<div class="tree-content pl-4 ml-2 border-l-2 border-gray-200" style="display: ${childDisplay};">`;
        node.children.forEach(child => { html += renderTreeNode(child, level + 1); });
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

function toggleTree(element) {
    const treeItem = element.closest('.tree-item');
    const treeContent = treeItem.nextElementSibling;
    if (treeContent && treeContent.classList.contains('tree-content')) {
        const isExpanded = treeItem.classList.contains('expanded');
        if (isExpanded) {
            treeItem.classList.remove('expanded');
            treeContent.style.display = 'none';
            treeItem.querySelector('.tree-toggle i').className = 'fas fa-chevron-right text-xs';
        } else {
            treeItem.classList.add('expanded');
            treeContent.style.display = 'block';
            treeItem.querySelector('.tree-toggle i').className = 'fas fa-chevron-down text-xs';
        }
    }
}

window.renderTreeView = renderTreeView;
window.toggleTree = toggleTree;