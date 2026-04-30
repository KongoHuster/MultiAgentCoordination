#!/usr/bin/env python3
"""
MultiAgent协作系统 - 一键测试运行器
运行所有自动化测试用例
"""

import subprocess
import sys
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text):
    """打印成功信息"""
    print(f"  ✅ {text}")


def print_error(text):
    """打印错误信息"""
    print(f"  ❌ {text}")


def run_command(cmd, description, capture=True, timeout=60):
    """运行命令"""
    print(f"\n执行: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=timeout
        )

        if capture:
            if result.stdout:
                print(result.stdout)
            if result.stderr and 'warning' not in result.stderr.lower():
                print("STDERR:", result.stderr)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  命令超时（{timeout}秒）")
        return False
    except Exception as e:
        print(f"  ❌ 执行失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "🎯 " * 20)
    print("  MultiAgent协作系统 - 全自动测试套件")
    print("🎯 " * 20)

    results = []

    # 1. 检查依赖
    print_header("检查测试依赖")
    deps_ok = True
    try:
        import flask
        print_success(f"Flask {flask.__version__}")
    except ImportError:
        print_error("Flask 未安装")
        deps_ok = False

    try:
        import pytest
        print_success(f"pytest {pytest.__version__}")
    except ImportError:
        print_error("pytest 未安装")
        deps_ok = False

    try:
        import sqlalchemy
        print_success(f"SQLAlchemy {sqlalchemy.__version__}")
    except ImportError:
        print_error("SQLAlchemy 未安装")
        deps_ok = False

    if not deps_ok:
        print("\n请运行以下命令安装依赖:")
        print("  source venv/bin/activate")
        print("  pip install flask flask-cors pytest sqlalchemy")
        return 1

    # 2. 前端文件测试
    print_header("运行前端文件测试")
    test1 = run_command(
        ['python', '-m', 'pytest', 'tests/test_frontend.py', '-v', '--tb=short'],
        "前端文件测试",
        timeout=30
    )
    results.append(("前端文件测试", test1))

    # 3. API项目管理测试
    print_header("运行项目管理测试")
    test2 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestProjectManagement', '-v', '--tb=short'],
        "项目管理测试",
        timeout=30
    )
    results.append(("项目管理测试", test2))

    # 4. 多角色协作测试
    print_header("运行多角色协作测试")
    test3 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestMultiAgentCollaboration', '-v', '--tb=short'],
        "多角色协作测试",
        timeout=30
    )
    results.append(("多角色协作测试", test3))

    # 5. 实时进度测试
    print_header("运行实时进度测试")
    test4 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestRealTimeProgress', '-v', '--tb=short'],
        "实时进度测试",
        timeout=30
    )
    results.append(("实时进度测试", test4))

    # 6. 打断功能测试
    print_header("运行打断功能测试")
    test5 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestInterruptFunctionality', '-v', '--tb=short'],
        "打断功能测试",
        timeout=30
    )
    results.append(("打断功能测试", test5))

    # 7. UI验证测试
    print_header("运行UI验证测试")
    test6 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestUIValidation', '-v', '--tb=short'],
        "UI验证测试",
        timeout=30
    )
    results.append(("UI验证测试", test6))

    # 8. 集成测试
    print_header("运行集成测试")
    test7 = run_command(
        ['python', '-m', 'pytest', 'tests/test_all.py::TestIntegration', '-v', '--tb=short'],
        "集成测试",
        timeout=30
    )
    results.append(("集成测试", test7))

    # 汇总结果
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n测试覆盖:")
        print("  ✅ 项目管理 (创建/删除/切换)")
        print("  ✅ 多角色协作 (消息归属)")
        print("  ✅ 实时进度显示")
        print("  ✅ 用户打断功能")
        print("  ✅ UI界面验证")
        print("  ✅ 前端文件完整性")
        print("  ✅ 完整工作流集成")
    else:
        print("\n⚠️  部分测试失败，请检查上述输出")

    print("\n" + "=" * 60)
    print(f"测试报告位置: {PROJECT_ROOT / 'tests'}")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
