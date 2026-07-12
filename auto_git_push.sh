#!/bin/bash
# GitHub 推送自愈 - 重试 + 错误恢复

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/git_push_$(date +%Y%m%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] GitHub 推送" >> "$LOG_FILE"

# 最多重试 3 次
for i in 1 2 3; do
    git add data/daily/*.json 2>> "$LOG_FILE"
    git commit -m "Auto push attempt $i: $(date '+%Y-%m-%d %H:%M')" >> "$LOG_FILE" 2>&1

    if git push origin main >> "$LOG_FILE" 2>&1; then
        echo "[$(date '+%H:%M:%S')] 推送成功 (尝试 $i)" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        exit 0
    else
        echo "[$(date '+%H:%M:%S')] 推送失败 (尝试 $i/3)" >> "$LOG_FILE"
        sleep 10
    fi
done

# 3次都失败 - 飞书告警
echo "[$(date '+%H:%M:%S')] ✗ 推送失败,需要手动处理" >> "$LOG_FILE"

# 飞书通知
/usr/bin/python3 /Users/nnn_nice/scripts/feishu_push.py "⚠️ Biotech Monitor GitHub 推送失败 3 次，请手动检查网络或认证" "GitHub推送失败"

echo "" >> "$LOG_FILE"
exit 1