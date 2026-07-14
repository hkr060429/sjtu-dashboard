#!/bin/bash
# update_dashboard.sh - 定时更新 SJTU Dashboard
set -e

DASHBOARD_DIR="$HOME/.openclaw/workspace/sjtu-dashboard"
CANVAS_ROOT=$(python3 -c "
import json, os
c = json.load(open(os.path.expanduser('~/.openclaw/openclaw.json')))
r = c.get('plugins',{}).get('entries',{}).get('canvas',{}).get('config',{}).get('host',{}).get('root','~/.openclaw/canvas')
print(os.path.expanduser(r))
")

cd "$DASHBOARD_DIR"

# 抓取数据
python3 fetch_all.py 2>&1 || echo "fetch_all FAILED"

# 生成 HTML
python3 generate_html.py 2>&1 || echo "generate_html FAILED"

# 复制到 canvas 目录供外网访问
mkdir -p "$CANVAS_ROOT/sjtu-dashboard"
cp index.html "$CANVAS_ROOT/sjtu-dashboard/index.html"

echo "✅ Dashboard 更新完成: $(date)"
