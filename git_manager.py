"""
Git Manager - 自动 Git 提交管理
"""
import subprocess
import os
from datetime import datetime
from typing import Optional


class GitManager:
    """Git 操作管理器"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._verify_git_repo()

    def _verify_git_repo(self) -> bool:
        """验证是否是 Git 仓库"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_dirty(self) -> bool:
        """检查是否有未提交的更改"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def get_status(self) -> dict:
        """获取 Git 状态"""
        try:
            result = subprocess.run(
                ["git", "status"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "success": True,
                "output": result.stdout,
                "dirty": self.is_dirty()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stage_all(self) -> bool:
        """暂存所有更改"""
        try:
            result = subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def commit(self, message: str, author: str = "Multi-Agent System") -> Optional[str]:
        """提交更改"""
        try:
            # 配置提交者
            subprocess.run(
                ["git", "config", "user.name", author],
                cwd=self.repo_path,
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ["git", "config", "user.email", f"{author}@multi-agent.local"],
                cwd=self.repo_path,
                capture_output=True,
                timeout=5
            )

            # 提交
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 获取 commit SHA
                sha_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return sha_result.stdout.strip() if sha_result.returncode == 0 else None

            return None
        except Exception:
            return None

    def commit_task(self, task_id: str, description: str,
                   files: list[str] = None) -> Optional[str]:
        """提交任务相关代码"""
        try:
            if files:
                # 只暂存指定文件
                for f in files:
                    subprocess.run(
                        ["git", "add", f],
                        cwd=self.repo_path,
                        capture_output=True,
                        timeout=5
                    )
            else:
                self.stage_all()

            # 生成提交信息
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"[Task-{task_id}] {description}\n\nTimestamp: {timestamp}\nAgent: multi-agent-system"

            return self.commit(commit_msg)
        except Exception:
            return None

    def get_last_commit(self) -> Optional[dict]:
        """获取最后一次提交"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%H|%s|%an|%ad|%cd"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                parts = result.stdout.split("|")
                if len(parts) >= 4:
                    return {
                        "sha": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3]
                    }
            return None
        except Exception:
            return None

    def get_recent_commits(self, count: int = 10) -> list[dict]:
        """获取最近的提交"""
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%H|%s|%an|%ad"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout:
                commits = []
                for line in result.stdout.strip().split("\n"):
                    parts = line.split("|")
                    if len(parts) >= 4:
                        commits.append({
                            "sha": parts[0][:8],
                            "message": parts[1],
                            "author": parts[2],
                            "date": parts[3]
                        })
                return commits
            return []
        except Exception:
            return []

    def branch(self, name: str, checkout: bool = False) -> bool:
        """创建分支"""
        try:
            result = subprocess.run(
                ["git", "branch", name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and checkout:
                subprocess.run(
                    ["git", "checkout", name],
                    cwd=self.repo_path,
                    capture_output=True,
                    timeout=5
                )
            return result.returncode == 0
        except Exception:
            return False

    def checkout(self, ref: str) -> bool:
        """切换分支/提交"""
        try:
            result = subprocess.run(
                ["git", "checkout", ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def diff(self, ref: str = None) -> str:
        """获取差异"""
        try:
            cmd = ["git", "diff"]
            if ref:
                cmd.append(ref)
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
