#!/bin/bash

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=5173

echo "=================================================="
echo "          🚀 金融系统服务一键启动脚本 🚀          "
echo "=================================================="
echo ""

# 释放占用端口的函数
kill_port() {
  local port=$1
  local pid=$(lsof -t -i :$port)
  if [ -n "$pid" ]; then
    echo "⚠️ 发现端口 $port 被进程 $pid 占用，正在强制释放..."
    kill -9 $pid 2>/dev/null
    sleep 0.5
  else
    echo "✅ 端口 $port 当前空闲。"
  fi
}

# 1. 重启前清理端口
echo "【步骤 1/3】清理旧服务端口..."
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT
echo ""

# 获取脚本所在目录，确保路径绝对正确（非常关键，Finder 双击启动默认会在用户家目录运行）
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 优雅关闭的清理函数 (Ctrl+C 触发)
cleanup() {
  echo ""
  echo "⚠️ 正在停止服务..."
  if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
    echo "  - 已关闭后端服务 (PID: $BACKEND_PID)"
  fi
  echo "✅ 所有后台服务均已安全停止。"
  exit 0
}
# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 2. 启动 FastAPI 后端服务
echo "【步骤 2/3】启动后端 API 服务 (FastAPI)..."
if [ -f "./venv/bin/python" ]; then
  # 后台启动并重定向日志
  ./venv/bin/python backend/main.py > backend.log 2>&1 &
  BACKEND_PID=$!
  echo "  - 后端进程 PID: $BACKEND_PID"
  echo "  - 日志已重定向输出到: backend.log"
else
  echo "❌ 错误: 未能在根目录下找到 ./venv/bin/python，请确认已安装 python 虚拟环境。"
  exit 1
fi
echo ""

# 等待 1.5 秒保证后端启动完毕
sleep 1.5

# 3. 启动前端 Vite 服务
echo "【步骤 3/3】启动前端网页服务 (Vite)..."
echo "  - 提示: 退出程序请在当前终端窗口按 Ctrl+C"
echo "--------------------------------------------------"

cd "$DIR/frontend"
if command -v pnpm &> /dev/null; then
  pnpm dev
else
  npm run dev
fi
