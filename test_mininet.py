#!/usr/bin/env python
"""最小化测试版本"""
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.node import Controller, Switch
from mininet.topo import Topo

class SimpleTopo(Topo):
    def __init__(self):
        super(SimpleTopo, self).__init__()
        # 1个交换机，4个主机
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s1)
        self.addLink(h4, s1)

setLogLevel('info')
net = Mininet(topo=SimpleTopo(), controller=Controller, switch=Switch)
net.start()
CLI(net)
net.stop()
