#!/bin/bash
# 验证 LNP/递送专题每日是否更新

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/delivery_check_$(date +%Y%m%d).log"
TODAY=$(date +%Y%m%d)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 递送系统检查" >> "$LOG_FILE"

# 检查今日数据
DELIVERY_FILE="data/daily/delivery_papers_${TODAY}.json"
if [ ! -f "$DELIVERY_FILE" ]; then
    echo "  ⚠️ ${DELIVERY_FILE} 不存在,触发扫描..." >> "$LOG_FILE"
    python3 scripts/delivery_scanner.py >> "$LOG_FILE" 2>&1
fi

# 检查 latest.json 中 delivery_systems
LATEST_FILE="data/daily/latest.json"
if [ -f "$LATEST_FILE" ]; then
    COUNT=$(python3 -c "
import json
with open('$LATEST_FILE') as f:
    d = json.load(f)
print(len(d.get('papers', {}).get('delivery_systems', [])))
" 2>/dev/null || echo "0")
    echo "  delivery_systems: $COUNT 篇" >> "$LOG_FILE"

    if [ "$COUNT" -lt 5 ]; then
        echo "  ⚠️ 数量过少,触发重新合并..." >> "$LOG_FILE"
        python3 scripts/daily_update.py >> "$LOG_FILE" 2>&1
    fi
fi

echo "[$(date '+%H:%M:%S')] 完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"