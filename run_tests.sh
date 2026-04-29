#!/bin/bash
# 完整测试脚本

echo "========================================"
echo "多Agent协作系统 - 完整测试"
echo "========================================"

# 检查 PostgreSQL
echo ""
echo "[检查] PostgreSQL 服务..."
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL 运行中"
else
    echo "⚠️ PostgreSQL 未运行，尝试启动..."
    pg_ctl -D /usr/local/var/postgres start 2>/dev/null || \
    pg_ctl -D /var/lib/postgresql/data start 2>/dev/null || \
    brew services start postgresql 2>/dev/null || \
    echo "⚠️ 无法自动启动 PostgreSQL，请手动启动"
fi

# 检查数据库
echo ""
echo "[检查] 数据库 multiagent..."
if psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw "multiagent"; then
    echo "✅ 数据库 multiagent 存在"
else
    echo "⚠️ 创建数据库 multiagent..."
    createdb multiagent 2>/dev/null || \
    psql -h localhost -U postgres -c "CREATE DATABASE multiagent;" 2>/dev/null || \
    echo "⚠️ 无法创建数据库，请手动创建: createdb multiagent"
fi

# 1. 数据库测试
echo ""
echo "========================================"
echo "[1/3] 运行数据库测试..."
echo "========================================"
python3 test_database.py
if [ $? -ne 0 ]; then
    echo "❌ 数据库测试失败"
    exit 1
fi
echo "✅ 数据库测试通过"

# 2. 工程构建测试
echo ""
echo "========================================"
echo "[2/3] 运行工程构建测试..."
echo "========================================"
python3 test_project_builder.py
if [ $? -ne 0 ]; then
    echo "❌ 工程构建测试失败"
    exit 1
fi
echo "✅ 工程构建测试通过"

# 3. 启动服务
echo ""
echo "========================================"
echo "[3/3] 启动服务并运行API测试..."
echo "========================================"

# 杀掉旧进程
pkill -f "python3 web_server.py" 2>/dev/null
sleep 1

# 启动服务
python3 web_server.py > /tmp/web_server.log 2>&1 &
SERVER_PID=$!
echo "服务 PID: $SERVER_PID"

# 等待服务启动
echo "等待服务启动..."
for i in {1..10}; do
    if curl -s http://localhost:8080/api/status > /dev/null 2>&1; then
        echo "✅ 服务已启动"
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        echo "❌ 服务启动超时"
        cat /tmp/web_server.log
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
done

# API测试
python3 test_api.py
API_RESULT=$?

# 清理
echo ""
echo "清理..."
kill $SERVER_PID 2>/dev/null

if [ $API_RESULT -ne 0 ]; then
    echo "❌ API测试失败"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ 所有测试通过!"
echo "========================================"
echo ""
echo "测试文件已创建:"
echo "  - test_database.py      # 数据库模块测试"
echo "  - test_project_builder.py  # 工程构建测试"
echo "  - test_api.py           # API测试"
echo ""
echo "运行测试:"
echo "  python3 test_database.py"
echo "  python3 test_project_builder.py"
echo "  python3 test_api.py  # 需要先启动 web_server.py"