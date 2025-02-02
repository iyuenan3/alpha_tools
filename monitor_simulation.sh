#!/bin/bash

# 定义日志文件和Python脚本的名称
LOG_FILE="simulation.log"  # 需要监控的日志文件
PYTHON_SCRIPT="alpha_simulator.py"  # 需要运行的Python脚本
# 进入无限循环，定期检查日志文件的更新时间
while true; do
    # 如果日志文件仍然不存在，重新启动 Python 脚本
    if [ ! -f "$LOG_FILE" ]; then
        echo "$(date) - Log file is missing. Restarting script..." >> monitor.log
        nohup python3 "$PYTHON_SCRIPT" > /dev/null 2>&1 &
        sleep 5  # 等待脚本启动
        continue  # 直接跳过本轮检查，进入下一轮循环
    fi

    # 获取日志文件的最后修改时间（以时间戳表示，单位为秒）
    LAST_MODIFIED=$(stat -c %Y "$LOG_FILE")
    # 获取当前时间（以时间戳表示，单位为秒）
    CURRENT_TIME=$(date +%s)
    # 计算当前时间与日志文件最后修改时间的时间差
    TIME_DIFF=$((CURRENT_TIME - LAST_MODIFIED))
    # 如果日志文件超过 10 分钟（600 秒）未更新，则认为脚本可能已经挂起，需要重启
    if [ "$TIME_DIFF" -gt 600 ]; then
        echo "$(date) - Log file stale for more than 10 minutes. Restarting script..." >> monitor.log
        # 获取正在运行的 Python 脚本的进程 ID
        PYTHON_PID=$(pgrep -f "$PYTHON_SCRIPT")
        # 如果找到该进程，则进行终止处理
        if [ -n "$PYTHON_PID" ]; then
            echo "$(date) - Sending SIGINT to process $PYTHON_PID" >> monitor.log
            kill -SIGINT "$PYTHON_PID"  # 发送 SIGINT 信号，尝试优雅终止进程

            TIMEOUT=300  # 设定最大等待时间 5 分钟（300 秒）
            ELAPSED=0

            while ps -p "$PYTHON_PID" > /dev/null; do
                if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
                    echo "$(date) - Process did not exit after 5 minutes. Forcibly killing it..." >> monitor.log
                    kill -9 "$PYTHON_PID"  # 强制终止进程
                    break
                fi
                sleep 10  # 每 10 秒检查一次进程状态
                ELAPSED=$((ELAPSED + 10))
            done
        fi
        sleep 5  # 稍作等待，确保资源释放
        # 重新启动 Python 脚本，并将输出重定向到 /dev/null 避免干扰
        nohup python3 "$PYTHON_SCRIPT" > /dev/null 2>&1 &
        echo "$(date) - Script restarted." >> monitor.log
    fi
    sleep 60  # 每 60 秒检查一次日志文件的更新时间
done
