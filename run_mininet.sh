#!/bin/bash
# 启动脚本 - 启动Ryu控制器和Mininet

# 在后台启动Ryu控制器
ryu-manager ryu.app.simple_switch_13 --ofp-tcp-listen-port 6653 &
RYU_PID=$!

# 等待控制器启动
sleep 3

# 运行Mininet脚本
python3 campus_network.py

# 清理
kill $RYU_PID 2>/dev/null
