"""
Git 操作管理器
"""

import os
import subprocess
import re
from typing import Optional, Optional
from datetime import datetime
from dataclasses import dataclass
import uuid


@dataclass
class GitCommit:
    """Git 提交"""
    hash: str
    short_hash: str
    message: str
    author: str
    date: datetime
    files: list[str]


@dataclass
class GitStatus:
    """Git 状态"""
    branch: str
    is_clean: bool
    staged: list[str]
    modified: list[str]
    untracked: list[str]


class GitManager:
    """Git 操作管理器"""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self._ensure_repo()

    def _ensure_repo(self):
        """确保是 Git 仓库"""
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            self.init()

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        """运行 git 命令"""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git error: {result.stderr}")
        return result

    def init(self, message: str = "Initial commit") -> str:
        """初始化仓库并创建初始提交"""
        if not os.path.exists(self.repo_path):
            os.makedirs(self.repo_path)

        self._run(["init"])
        self._run(["config", "user.email", "agent@agency.visual"])
        self._run(["config", "user.name", "Agency Visual"])

        # 创建初始文件
        readme_path = os.path.join(self.repo_path, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Project\n\nCreated by Agency Visual\n")

        self._run(["add", "."])
        self._run(["commit", "-m", message])

        return self.get_current_commit()

    def add_file(self, file_path: str, content: str, encoding: str = "utf-8"):
        """添加或更新文件"""
        full_path = os.path.join(self.repo_path, file_path)

        # 确保目录存在
        dir_path = os.path.dirname(full_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(full_path, "w", encoding=encoding) as f:
            f.write(content)

        self._run(["add", file_path])

    def add_files(self, files: dict[str, str]):
        """批量添加文件"""
        for file_path, content in files.items():
            self.add_file(file_path, content)

    def delete_file(self, file_path: str):
        """删除文件"""
        full_path = os.path.join(self.repo_path, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            self._run(["rm", "--cached", file_path])
            self._run(["rm", file_path])

    def commit(self, message: str) -> str:
        """提交更改"""
        # 检查是否有更改
        status = self.status()
        if status.staged or status.modified or status.untracked:
            self._run(["add", "."])

        if not self._has_staged():
            self._run(["add", "."])

        result = self._run(["commit", "-m", message])
        return self.get_current_commit()

    def _has_staged(self) -> bool:
        """检查是否有暂存的更改"""
        result = self._run(["diff", "--cached", "--name-only"])
        return bool(result.stdout.strip())

    def get_current_commit(self) -> str:
        """获取当前提交哈希"""
        try:
            result = self._run(["rev-parse", "HEAD"])
            return result.stdout.strip()
        except Exception:
            return ""

    def status(self) -> GitStatus:
        """获取仓库状态"""
        try:
            result = self._run(["status", "--porcelain"])
        except RuntimeError:
            return GitStatus(
                branch="main",
                is_clean=True,
                staged=[],
                modified=[],
                untracked=[]
            )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        staged = []
        modified = []
        untracked = []

        for line in lines:
            if not line:
                continue
            status_code = line[:2]
            file_path = line[3:]

            if status_code[0] == "?":
                untracked.append(file_path)
            elif status_code[0] == "A" or status_code[0] == "M" or status_code[0] == "R":
                staged.append(file_path)
            elif status_code[0] == " " or status_code[0] == "!":
                modified.append(file_path)
            elif status_code[1] == "M":
                modified.append(file_path)

        # 获取分支名
        branch = "main"
        try:
            result = self._run(["branch", "--show-current"])
            branch = result.stdout.strip() or "main"
        except Exception:
            pass

        is_clean = not (staged or modified or untracked)

        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            staged=staged,
            modified=modified,
            untracked=untracked
        )

    def get_log(self, max_count: int = 50) -> list[GitCommit]:
        """获取提交历史"""
        result = self._run([
            "log",
            f"--max-count={max_count}",
            "--pretty=format:%H|%h|%s|%an|%ad",
            "--date=iso"
        ])

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 5:
                commits.append(GitCommit(
                    hash=parts[0],
                    short_hash=parts[1],
                    message=parts[2],
                    author=parts[3],
                    date=datetime.fromisoformat(parts[4]),
                    files=[]
                ))

        # 获取每个提交的文件列表
        for commit in commits:
            result = self._run(["show", "--name-only", "--pretty=format:", commit.hash])
            commit.files = [f for f in result.stdout.strip().split("\n") if f]

        return commits

    def get_diff(self, ref: Optional[str] = None) -> str:
        """获取 diff"""
        if ref:
            result = self._run(["diff", ref])
        else:
            result = self._run(["diff", "HEAD"])
        return result.stdout

    def get_file_content(self, file_path: str, ref: Optional[str] = None) -> str:
        """获取文件内容"""
        if ref:
            result = self._run(["show", f"{ref}:{file_path}"])
        else:
            result = self._run(["show", f"HEAD:{file_path}"])
        return result.stdout

    def list_files(self, ref: Optional[str] = None) -> list[str]:
        """列出仓库中的文件"""
        if ref:
            result = self._run(["ls-tree", "-r", "--name-only", ref])
        else:
            result = self._run(["ls-tree", "-r", "--name-only", "HEAD"])
        return [f for f in result.stdout.strip().split("\n") if f]

    def create_branch(self, branch_name: str):
        """创建分支"""
        self._run(["checkout", "-b", branch_name])

    def checkout_branch(self, branch_name: str):
        """切换分支"""
        self._run(["checkout", branch_name])

    def get_branches(self) -> list[str]:
        """获取所有分支"""
        result = self._run(["branch", "-a"])
        return [b.strip().replace("* ", "") for b in result.stdout.strip().split("\n") if b]


def create_git_manager(conversation_id: str, projects_dir: str = "generated_projects") -> GitManager:
    """创建 Git 管理器实例"""
    repo_path = os.path.join(projects_dir, conversation_id)
    return GitManager(repo_path)