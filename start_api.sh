#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
sudo mn -c 2>/dev/null || true
exec sudo python3 campus_network.py --api
