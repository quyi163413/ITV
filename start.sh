#!/bin/bash
set -e

echo "=========================================="
echo "IPTV 智能整理平台 Docker 容器启动"
echo "=========================================="

mkdir -p /app/data /app/output
cd /app

# 只启动 Flask，不启动 http.server
echo "启动 Web 管理界面，端口 ${WEB_SERVER_PORT:-8080}"
python -m src.server &
WEB_PID=$!

sleep 3

RUN_MODE=${RUN_MODE:-once}
INTERVAL=${SCHEDULE_INTERVAL:-21600}

run_collector() {
    while true; do
        echo "$(date): 开始采集任务..."
        cd /app
        python -m src.run
        echo "$(date): 任务完成"
        if [ "$RUN_MODE" = "once" ]; then
            break
        fi
        echo "等待 ${INTERVAL} 秒后继续..."
        sleep $INTERVAL
    done
}

run_collector

if [ "$RUN_MODE" = "once" ]; then
    echo "✅ 任务完成，Web 服务继续运行"
    echo "📺 访问: http://localhost:${WEB_SERVER_PORT:-8080}"
    wait $WEB_PID
fi
