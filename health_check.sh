#!/bin/bash
# Biotech Monitor - 健康检查脚本
# 检查项：1) 代理服务器 2) 数据文件 3) 自动更新日志 4) GitHub 同步状态

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/health_$(date +%Y%m%d).log"

echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 健康检查开始" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

ISSUES=0

# 1. 检查代理服务器
echo "[1/4] 检查 AI 代理服务器..." >> "$LOG_FILE"
if curl -s --connect-timeout 3 http://localhost:3000/health > /dev/null 2>&1; then
    echo "  ✓ 代理服务器运行中" >> "$LOG_FILE"
else
    echo "  ✗ 代理服务器未运行,尝试启动..." >> "$LOG_FILE"
    lsof -ti :3000 | xargs kill -9 2>/dev/null
    nohup python3 proxy.py >> "$LOG_DIR/proxy.log" 2>&1 &
    sleep 2
    if curl -s --connect-timeout 3 http://localhost:3000/health > /dev/null 2>&1; then
        echo "  ✓ 代理服务器已启动" >> "$LOG_FILE"
    else
        echo "  ✗ 代理服务器启动失败" >> "$LOG_FILE"
        ISSUES=$((ISSUES+1))
    fi
fi

# 2. 检查数据文件
echo "[2/4] 检查数据文件..." >> "$LOG_FILE"
if [ -f "data/daily/latest.json" ]; then
    LAST_UPDATE=$(python3 -c "import json; d=json.load(open('data/daily/latest.json')); print(d.get('timestamp','N/A'))" 2>/dev/null)
    PAPER_COUNT=$(python3 -c "import json; d=json.load(open('data/daily/latest.json')); print(sum(len(v) for v in d.get('papers',{}).values()))" 2>/dev/null)
    echo "  ✓ latest.json 存在" >> "$LOG_FILE"
    echo "    最后更新: $LAST_UPDATE" >> "$LOG_FILE"
    echo "    论文总数: $PAPER_COUNT" >> "$LOG_FILE"
else
    echo "  ✗ latest.json 不存在" >> "$LOG_FILE"
    ISSUES=$((ISSUES+1))
fi

# 3. 检查自动更新日志
echo "[3/4] 检查自动更新日志..." >> "$LOG_FILE"
LATEST_UPDATE_LOG=$(ls -t $LOG_DIR/auto_update_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_UPDATE_LOG" ]; then
    LAST_RUN=$(grep "自动更新完成" "$LATEST_UPDATE_LOG" | tail -1)
    if [ -n "$LAST_RUN" ]; then
        echo "  ✓ 最近成功更新: $LAST_RUN" >> "$LOG_FILE"
    else
        echo "  ⚠ 最近更新可能失败" >> "$LOG_FILE"
        ISSUES=$((ISSUES+1))
    fi
else
    echo "  ⚠ 未找到更新日志" >> "$LOG_FILE"
fi

# 4. 检查 GitHub 同步状态
echo "[4/4] 检查 GitHub 同步状态..." >> "$LOG_FILE"
git fetch origin 2>/dev/null
LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git rev-parse origin/main 2>/dev/null)
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "  ✓ 本地与远程同步" >> "$LOG_FILE"
else
    BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null)
    AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null)
    echo "  ⚠ 不同步: 本地领先 $AHEAD, 落后 $BEHIND" >> "$LOG_FILE"
    if [ "$AHEAD" -gt 0 ]; then
        ISSUES=$((ISSUES+1))
    fi
fi

# 总结
echo "" >> "$LOG_FILE"
if [ $ISSUES -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] ✓ 全部检查通过" >> "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] ⚠ 发现 $ISSUES 个问题,请查看日志" >> "$LOG_FILE"
fi
echo "" >> "$LOG_FILE"

# 输出到控制台（如果直接运行）
if [ -t 1 ]; then
    cat "$LOG_FILE" | tail -20
fi
