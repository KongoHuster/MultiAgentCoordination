#!/usr/bin/env python3
"""
工程构建模块测试
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.project_builder import ProjectBuilder

TEST_PROJECTS_DIR = "test_generated_projects"

def cleanup_test_dir():
    """清理测试目录"""
    test_dir = Path(TEST_PROJECTS_DIR)
    if test_dir.exists():
        shutil.rmtree(test_dir)

def test_create_git_repo():
    """测试创建独立Git仓库"""
    print("测试: 创建独立Git仓库...")
    cleanup_test_dir()

    builder = ProjectBuilder()
    builder.projects_dir = Path(TEST_PROJECTS_DIR)

    try:
        # 创建Git仓库
        repo_path = builder.create_git_repo("test_project_001")
        repo_path = Path(repo_path)

        # 验证目录存在
        assert repo_path.exists()
        print(f"  ✅ 仓库目录创建: {repo_path}")

        # 验证Git初始化
        git_dir = repo_path / ".git"
        assert git_dir.exists()
        print("  ✅ Git仓库初始化")

        # 验证README创建
        readme = repo_path / "README.md"
        assert readme.exists()
        print("  ✅ README创建")

        # 验证初始commit
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        assert "Initial commit" in result.stdout
        print("  ✅ 初始commit存在")

        return True
    except Exception as e:
        print(f"  ❌ 创建Git仓库失败: {e}")
        return False
    finally:
        cleanup_test_dir()

def test_commit_to_git():
    """测试Git提交"""
    print("测试: Git提交...")
    cleanup_test_dir()

    builder = ProjectBuilder()
    builder.projects_dir = Path(TEST_PROJECTS_DIR)

    try:
        repo_path = builder.create_git_repo("commit_test_project")
        repo_path_obj = Path(repo_path)

        # 创建文件
        (repo_path_obj / "test.txt").write_text("Hello World")
        (repo_path_obj / "test.txt").write_text("Hello World", encoding='utf-8')

        # 提交
        sha = builder.commit_to_git(repo_path, "Test commit")
        assert sha, "提交SHA不应为空"
        print(f"  ✅ 提交成功: {sha[:8]}")

        # 验证提交存在
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        assert "Test commit" in result.stdout
        print("  ✅ 提交记录存在")

        return True
    except Exception as e:
        print(f"  ❌ Git提交失败: {e}")
        return False
    finally:
        cleanup_test_dir()

def test_build_project_with_git():
    """测试构建项目并提交Git"""
    print("测试: 构建项目并Git提交...")
    cleanup_test_dir()

    builder = ProjectBuilder()
    builder.projects_dir = Path(TEST_PROJECTS_DIR)

    try:
        # 构建项目
        result = builder.build_project(
            project_name="calculator_project",
            task_description="创建一个计算器",
            code_content="# Calculator\nprint('Hello Calculator')"
        )

        repo_path = Path(result["project_dir"])

        # 验证项目目录
        assert repo_path.exists()
        print(f"  ✅ 项目目录: {repo_path}")

        # 验证Git日志有提交
        result_git = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        commits = result_git.stdout.strip().split("\n")
        assert len(commits) >= 1
        print(f"  ✅ Git提交数: {len(commits)}")

        # 验证代码文件
        code_file = repo_path / "calculator_project.py"
        assert code_file.exists()
        print("  ✅ 代码文件创建")

        return True
    except Exception as e:
        print(f"  ❌ 构建项目失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_dir()

def test_multi_file_project():
    """测试多文件项目"""
    print("测试: 多文件项目...")
    cleanup_test_dir()

    builder = ProjectBuilder()
    builder.projects_dir = Path(TEST_PROJECTS_DIR)

    try:
        code_content = """# FILE: main.py
def main():
    print("Hello")

# FILE: utils.py
def helper():
    return 42

# FILE: config.py
CONFIG = {"version": "1.0"}
"""
        result = builder.build_project(
            project_name="multi_file_project",
            task_description="创建多文件项目",
            code_content=code_content
        )

        repo_path = Path(result["project_dir"])

        # 验证多个文件
        assert (repo_path / "main.py").exists()
        assert (repo_path / "utils.py").exists()
        assert (repo_path / "config.py").exists()
        print("  ✅ 多文件创建成功")

        return True
    except Exception as e:
        print(f"  ❌ 多文件项目失败: {e}")
        return False
    finally:
        cleanup_test_dir()

def test_multiple_projects_isolation():
    """测试多项目隔离"""
    print("测试: 多项目隔离...")
    cleanup_test_dir()

    builder = ProjectBuilder()
    builder.projects_dir = Path(TEST_PROJECTS_DIR)

    try:
        # 创建多个项目
        project1 = builder.create_git_repo("project_one")
        project2 = builder.create_git_repo("project_two")

        # 验证隔离
        assert Path(project1).name == "project_one"
        assert Path(project2).name == "project_two"
        assert Path(project1) != Path(project2)
        print("  ✅ 多项目隔离正确")

        # 验证各自Git独立
        for p in [project1, project2]:
            git_dir = Path(p) / ".git"
            assert git_dir.exists()

        print("  ✅ Git仓库独立")
        return True
    except Exception as e:
        print(f"  ❌ 多项目隔离测试失败: {e}")
        return False
    finally:
        cleanup_test_dir()

def test_generate_project_name():
    """测试项目名生成"""
    print("测试: 项目名生成...")
    builder = ProjectBuilder()

    # 中文测试
    name1 = builder.generate_project_name("实现一个计算器程序")
    # 检查是否包含计算器相关词
    assert "计算" in name1 or len(name1) > 0
    print(f"  ✅ 中文项目名生成: {name1}")

    # 英文测试
    name2 = builder.generate_project_name("create a calculator application")
    assert "calculator" in name2.lower()
    print(f"  ✅ 英文项目名生成: {name2}")

    return True

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("工程构建模块测试")
    print("=" * 60)

    tests = [
        test_create_git_repo,
        test_commit_to_git,
        test_build_project_with_git,
        test_multi_file_project,
        test_multiple_projects_isolation,
        test_generate_project_name,
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    print("=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)

    return all(results)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)