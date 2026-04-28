#!/usr/bin/env python3
"""
Multi-Agent System - 主入口

用法:
    python main.py "你的任务描述"
"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制输出无缓冲
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from workflow_engine import WorkflowEngine
from config import get_config


def main():
    print("="*60, flush=True)
    print("多智能体系统启动中...", flush=True)
    print("="*60, flush=True)

    # 检查 API Key
    config = get_config()
    print(f"API Key: {'已设置' if config.anthropic_api_key else '未设置'}", flush=True)
    print(f"Base URL: {config.base_url}", flush=True)
    print(f"Model: {config.default_model}", flush=True)

    if not config.anthropic_api_key:
        print("错误: 请设置 ANTHROPIC_API_KEY 环境变量")
        print("export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)

    # 获取用户请求
    if len(sys.argv) < 2:
        print("用法: python main.py \"任务描述\"")
        print("\n示例:")
        print('  python main.py "实现一个计算器类，包含加减乘除功能"')
        print('  python main.py "创建一个用户登录系统"')
        sys.exit(1)

    user_request = " ".join(sys.argv[1:])
    print(f"\n任务: {user_request}", flush=True)

    # 运行工作流
    print("\n初始化工作流引擎...", flush=True)
    engine = WorkflowEngine(config.anthropic_api_key)
    print("工作流引擎已初始化\n", flush=True)

    result = engine.run(user_request)

    # 输出结果
    print("\n" + "=" * 60, flush=True)
    print("最终结果:", flush=True)
    print("=" * 60, flush=True)
    print(f"状态: {result.get('status')}", flush=True)
    print(f"子任务数: {result.get('subtasks')}", flush=True)
    print(f"总结: {result.get('final', {}).get('summary')}", flush=True)

    # 返回退出码
    if result.get("status") == "completed":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
