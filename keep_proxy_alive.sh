#!/bin/bash
# Biotech Monitor - 代理保活脚本
# 每5分钟执行一次：检查代理是否运行，未运行则启动

PROXY_LOG="/Users/nnn_nice/scripts/biotech-monitor/logs/keepalive.log"
PROXY_SCRIPT="/Users/nnn_nice/scripts/biotech-monitor/start_proxy.sh"

# 检查代理是否响应
if curl -s --connect-timeout 3 http://localhost:3000/health > /dev/null 2>&1; then
    # 健康检查通过，无需操作
    :
else
    # 代理未响应，等待端口释放
    sleep 5
    # 检查是否真的有进程在监听
    if lsof -i :3000 -sTCP:LISTEN > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 端口3000有进程但无响应,跳过" >> "$PROXY_LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 代理未运行,正在启动..." >> "$PROXY_LOG"
        nohup /bin/bash "$PROXY_SCRIPT" >> /Users/nnn_nice/scripts/biotech-monitor/logs/proxy.log 2>&1 &
        disown
        sleep 5
        if curl -s --connect-timeout 3 http://localhost:3000/health > /dev/null 2>&1; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 代理已重新启动" >> "$PROXY_LOG"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 代理启动失败" >> "$PROXY_LOG"
        fi
    fi
fi
