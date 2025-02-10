#!/bin/bash

# 定义日志文件和Python脚本的名称
LOG_FILE="simulation.log"  # 需要监控的日志文件
PYTHON_SCRIPT="alpha_simulator.py"  # 需要运行的Python脚本
MONITOR_LOG="monitor.log"  # 监控日志文件

# 超时时间（单位：秒），如果日志文件超过此时间未更新，则重启脚本
LOG_TIMEOUT=600

# 先清空 monitor.log
> "$MONITOR_LOG"

# 日志函数，支持终端和日志文件
log_message() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")  # 统一时间格式
    echo "$timestamp - $level - $message" | tee -a "$MONITOR_LOG"
}

log_message "INFO" "Monitor script started. Log timeout set to $LOG_TIMEOUT seconds."

# 进入无限循环，定期检查日志文件的更新时间
while true; do
    # 记录当前检测时间
    log_message "INFO" "Checking log file status..."

    # 如果日志文件不存在，重新启动 Python 脚本
    if [ ! -f "$LOG_FILE" ]; then
        log_message "WARNING" "Log file is missing. Restarting script..."
        nohup python3 "$PYTHON_SCRIPT" > /dev/null 2>&1 &
        NEW_PID=$!  # 获取刚启动的 Python 进程号
        log_message "INFO" "$PYTHON_SCRIPT script started with PID: $NEW_PID"
        sleep 5  # 等待脚本启动
        continue  # 直接跳过本轮检查，进入下一轮循环
    fi

    # 获取日志文件的最后修改时间（以时间戳表示，单位为秒）
    LAST_MODIFIED=$(stat -c %Y "$LOG_FILE")
    # 获取当前时间（以时间戳表示，单位为秒）
    CURRENT_TIME=$(date +%s)
    # 计算当前时间与日志文件最后修改时间的时间差
    TIME_DIFF=$((CURRENT_TIME - LAST_MODIFIED))

    log_message "INFO" "Log last modified $TIME_DIFF seconds ago."

    # 如果日志文件超过 LOG_TIMEOUT 秒未更新，则认为脚本可能已经挂起，需要重启
    if [ "$TIME_DIFF" -gt "$LOG_TIMEOUT" ]; then
        log_message "ERROR" "Log file stale for more than $LOG_TIMEOUT seconds. Restarting script..."

        # 获取正在运行的 Python 脚本的进程 ID
        PYTHON_PID=$(pgrep -f "$PYTHON_SCRIPT")

        # 如果找到该进程，则进行终止处理
        if [ -n "$PYTHON_PID" ]; then
            log_message "INFO" "Sending SIGINT to process $PYTHON_PID"
            kill -SIGINT "$PYTHON_PID"  # 发送 SIGINT 信号，尝试优雅终止进程

            TIMEOUT=300  # 设定最大等待时间 5 分钟（300 秒）
            ELAPSED=0

            while ps -p "$PYTHON_PID" > /dev/null; do
                if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
                    log_message "CRITICAL" "Process did not exit after 5 minutes. Forcibly killing it..."
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
        NEW_PID=$!  # 获取新启动的 Python 进程号
        log_message "INFO" "$PYTHON_SCRIPT restarted with PID: $NEW_PID"
    fi

    sleep 300
done
