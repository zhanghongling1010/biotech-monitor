#!/bin/bash
# Biotech Monitor - 每日自动更新脚本
# 由crontab调用，每天早上7:00执行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/auto_update_$(date +%Y%m%d).log"

echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始自动更新" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 1. 抓取PubMed论文
echo "[$(date '+%H:%M:%S')] 抓取PubMed论文..." >> "$LOG_FILE"
python3 scripts/collect_pubmed.py >> "$LOG_FILE" 2>&1
PUBMED_EXIT=$?
echo "[$(date '+%H:%M:%S')] PubMed抓取完成, 退出码: $PUBMED_EXIT" >> "$LOG_FILE"

# 2. 抓取BD新闻
echo "[$(date '+%H:%M:%S')] 抓取BD新闻..." >> "$LOG_FILE"
python3 scripts/collect_bd_news.py >> "$LOG_FILE" 2>&1
BD_EXIT=$?
echo "[$(date '+%H:%M:%S')] BD新闻抓取完成, 退出码: $BD_EXIT" >> "$LOG_FILE"

# 3. 合并数据
echo "[$(date '+%H:%M:%S')] 合并数据..." >> "$LOG_FILE"
python3 scripts/daily_update.py >> "$LOG_FILE" 2>&1
MERGE_EXIT=$?
echo "[$(date '+%H:%M:%S')] 数据合并完成, 退出码: $MERGE_EXIT" >> "$LOG_FILE"

# 3.5 预生成 AI 分析（让所有人都能看 AI 解读）
if [ $MERGE_EXIT -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] 预生成 AI 分析..." >> "$LOG_FILE"
    # 先确保代理在运行
    if ! curl -s --connect-timeout 2 http://localhost:3000/health > /dev/null 2>&1; then
        nohup /usr/bin/python3 -u proxy.py < /dev/null > "$LOG_DIR/proxy.log" 2>&1 &
        disown
        sleep 12  # Flask 启动需要时间
    fi

    if curl -s --connect-timeout 2 http://localhost:3000/health > /dev/null 2>&1; then
        # macOS 没有 timeout，用 bash 内置
        python3 scripts/precompute_analysis.py >> "$LOG_FILE" 2>&1 &
        PRE_PID=$!
        # 最多等10分钟
        for i in $(seq 1 60); do
            sleep 10
            if ! ps -p $PRE_PID > /dev/null 2>&1; then
                break
            fi
            if [ $i -eq 60 ]; then
                kill -9 $PRE_PID 2>/dev/null
                echo "[$(date '+%H:%M:%S')] AI 预生成超时,已终止" >> "$LOG_FILE"
            fi
        done
        PRE_EXIT=0
        echo "[$(date '+%H:%M:%S')] AI 预生成完成" >> "$LOG_FILE"
    else
        echo "[$(date '+%H:%M:%S')] 代理不可用,跳过 AI 预生成" >> "$LOG_FILE"
    fi
fi

# 4. 提交并推送到GitHub
if [ $PUBMED_EXIT -eq 0 ] || [ $BD_EXIT -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] 提交到Git..." >> "$LOG_FILE"
    git add data/daily/*.json 2>> "$LOG_FILE"
    git commit -m "Auto update: $(date '+%Y-%m-%d %H:%M')" >> "$LOG_FILE" 2>&1

    echo "[$(date '+%H:%M:%S')] 推送到GitHub..." >> "$LOG_FILE"
    if git push origin main >> "$LOG_FILE" 2>&1; then
        echo "[$(date '+%H:%M:%S')] 推送成功!" >> "$LOG_FILE"
    else
        echo "[$(date '+%H:%M:%S')] 推送失败,将稍后重试" >> "$LOG_FILE"
    fi
else
    echo "[$(date '+%H:%M:%S')] 抓取失败,跳过推送" >> "$LOG_FILE"
fi

echo "[$(date '+%H:%M:%S')] 自动更新完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
