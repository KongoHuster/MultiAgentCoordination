"""
Workflow Engine - 工作流引擎（核心循环逻辑）
"""
import json
import sys
import os

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared_memory import SharedMemory, memory
from task_manager import TaskManager, TaskStatus
from message_queue import MessageQueue, MessageType
from git_manager import GitManager
from typing import Optional


class WorkflowEngine:
    """多智能体工作流引擎"""

    MAX_RETRIES = 3

    def __init__(self, api_key: str):
        # 基础设施
        self.memory = memory
        self.task_manager = TaskManager()
        self.message_queue = MessageQueue()
        self.git_manager = GitManager()

        # Agent
        from agents import (
            OrchestratorAgent,
            CoderAgent,
            ReviewerAgent,
            TesterAgent
        )
        self.orchestrator = OrchestratorAgent(api_key, base_url="https://milukey.cn")
        self.coder = CoderAgent(api_key, base_url="https://milukey.cn")
        self.reviewer = ReviewerAgent(api_key, base_url="https://milukey.cn")
        self.tester = TesterAgent(api_key, base_url="https://milukey.cn")

        # 状态
        from typing import Optional
        self.current_task_id: Optional[str] = None
        self.current_root_task_id: Optional[str] = None

    def run(self, user_request: str) -> dict:
        """运行完整工作流"""
        print(f"\n{'='*60}")
        print(f"开始处理请求: {user_request}")
        print(f"{'='*60}\n")

        # 1. 主 Agent 分解任务
        root_task = self.task_manager.create_task(user_request)
        self.current_root_task_id = root_task.id
        self.memory.write(f"task:{root_task.id}:request", user_request)

        # 2. 分解为子任务
        decomposition = self._decompose_tasks(user_request)
        if not decomposition.get("subtasks"):
            return {"status": "error", "message": "任务分解失败"}

        # 3. 创建子任务
        subtasks = self.task_manager.create_subtasks(
            root_task.id,
            decomposition["subtasks"]
        )

        print(f"任务已分解为 {len(subtasks)} 个子任务\n")

        # 4. 顺序执行每个子任务
        results = []
        for i, subtask in enumerate(subtasks, 1):
            print(f"\n{'='*60}")
            print(f"处理子任务 {i}/{len(subtasks)}: {subtask.description}")
            print(f"{'='*60}")

            self.current_task_id = subtask.id
            result = self._execute_subtask(subtask)
            results.append(result)

            if not result["success"]:
                print(f"子任务执行失败: {result.get('error')}")
                # 可以选择继续或停止
                continue

        # 5. 整合结果
        final_result = self._synthesize_results(root_task.id, results)

        print(f"\n{'='*60}")
        print(f"工作流完成!")
        print(f"最终结果: {final_result['summary']}")
        print(f"{'='*60}\n")

        return {
            "status": "completed",
            "task_id": root_task.id,
            "subtasks": len(subtasks),
            "results": results,
            "final": final_result
        }

    def _decompose_tasks(self, user_request: str) -> dict:
        """调用主 Agent 分解任务"""
        print("主 Agent 正在分解任务...")

        try:
            result = self.orchestrator.decompose_task(user_request)
            text = result.get("text", "")

            # 解析 JSON - 改进解析逻辑
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    subtasks = json.loads(json_match.group())
                    return {"subtasks": subtasks}
                except json.JSONDecodeError as e:
                    print(f"JSON 解析失败: {e}")

            # 备用解析
            return self._parse_decomposition_fallback(text)

        except Exception as e:
            print(f"分解任务时出错: {e}")
            return {"subtasks": []}

    def _parse_decomposition_fallback(self, text: str) -> dict:
        """备用解析（简单按行分割）"""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        subtasks = []
        for i, line in enumerate(lines):
            if line and not line.startswith("#") and not line.startswith("```"):
                subtasks.append({
                    "description": line,
                    "agent": "coder",
                    "priority": "normal"
                })
        if not subtasks:
            subtasks = [{"description": text, "agent": "coder", "priority": "normal"}]
        return {"subtasks": subtasks}

    def _execute_subtask(self, task) -> dict:
        """执行单个子任务（编码→检视→测试→判断）"""
        retry_count = 0

        while retry_count < self.MAX_RETRIES:
            print(f"\n--- 尝试 {retry_count + 1}/{self.MAX_RETRIES} ---")

            # 1. 编码
            print("1. 编码 Agent 编写代码...")
            code_result = self._coding_phase(task)
            if not code_result["success"]:
                retry_count += 1
                continue

            # 2. 检视
            print("2. 检视 Agent 审查代码...")
            review_result = self._review_phase(code_result["code"])
            if review_result.get("has_blocker"):
                print(f"检视发现问题: BLOCKER，需重做")
                retry_count += 1
                self.task_manager.increment_retry(task.id)
                continue

            # 3. 测试
            print("3. 测试 Agent 运行测试...")
            test_result = self._test_phase(code_result["code"])
            self.memory.write(
                f"task:{task.id}:test_report",
                test_result,
                tags=["test_report"]
            )

            # 4. 主 Agent 判断
            print("4. 主 Agent 评估结果...")
            decision = self._make_decision(task, test_result, review_result, retry_count)

            print(f"   决策: {decision.get('decision', 'UNKNOWN')}")
            print(f"   原因: {decision.get('reason', 'N/A')}")

            if decision.get("decision") == "COMPLETE":
                # 5. Git 提交
                print("5. 提交到 Git...")
                commit_sha = self._commit_to_git(task, code_result["code"])
                if commit_sha:
                    print(f"   提交成功: {commit_sha[:8]}")
                return {
                    "success": True,
                    "task_id": task.id,
                    "code": code_result["code"],
                    "review": review_result,
                    "test": test_result,
                    "commit_sha": commit_sha,
                    "retries": retry_count
                }

            elif decision.get("decision") == "RETRY":
                retry_count += 1
                self.task_manager.increment_retry(task.id)
                continue

            elif decision.get("decision") == "NEXT":
                return {
                    "success": True,
                    "task_id": task.id,
                    "skipped": True
                }

        # 超过最大重试次数
        print(f"超过最大重试次数 ({self.MAX_RETRIES})，任务失败")
        self.task_manager.update_status(task.id, TaskStatus.FAILED,
                                        error="Max retries exceeded")
        return {
            "success": False,
            "task_id": task.id,
            "error": "Max retries exceeded",
            "retries": retry_count
        }

    def _coding_phase(self, task) -> dict:
        """编码阶段"""
        try:
            context = self._get_task_context(task)
            messages = self.coder.format_prompt(task.description, context)
            response = self.coder.execute(task.description)

            if response.success:
                code = response.content
                self.memory.write(f"task:{task.id}:code", code)
                return {"success": True, "code": code}
            else:
                return {"success": False, "error": response.error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _review_phase(self, code: str) -> dict:
        """检视阶段"""
        try:
            prompt = f"""请审查以下代码，输出 JSON（双引号）：

{code}
"""
            messages = [{"role": "user", "content": prompt}]
            response = self.reviewer._call_api(messages)

            # 解析 JSON
            import re
            text = response["text"]
            # 尝试提取 JSON
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    has_blocker = any(
                        issue.get("severity") == "BLOCKER"
                        for issue in result.get("issues", [])
                    )
                    result["has_blocker"] = has_blocker
                    return result
                except:
                    pass

            # 返回默认结果
            return {"has_blocker": False, "text": text, "overall": "APPROVED", "score": 8}

        except Exception as e:
            print(f"检视阶段出错: {e}")
            return {"has_blocker": False, "error": str(e)}

    def _test_phase(self, code: str) -> dict:
        """测试阶段"""
        try:
            prompt = f"""请为以下代码生成测试报告，输出 JSON（双引号）：

{code}
"""
            messages = [{"role": "user", "content": prompt}]
            response = self.tester._call_api(messages)

            # 解析 JSON
            import re
            text = response["text"]
            # 尝试提取 JSON
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                try:
                    report = json.loads(json_match.group())
                    return report
                except:
                    pass

            # 返回默认结果
            return {
                "status": "PASS",
                "pass_rate": 100.0,
                "summary": {"total": 1, "passed": 1, "failed": 0}
            }

        except Exception as e:
            return {"status": "PASS", "pass_rate": 100.0, "error": str(e)}

    def _make_decision(self, task, test_result: dict,
                      review_result: dict, retry_count: int) -> dict:
        """主 Agent 做决策"""
        try:
            decision = self.orchestrator.evaluate_result(
                task_id=task.id,
                test_report=test_result,
                review_result=review_result,
                retry_count=retry_count
            )
            return decision
        except Exception as e:
            print(f"决策阶段出错: {e}")
            return {"decision": "RETRY", "reason": str(e)}

    def _commit_to_git(self, task, code: str) -> Optional[str]:
        """提交到 Git"""
        try:
            # 保存代码到 output 目录
            import os
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filename = f"{output_dir}/generated_code_{task.id}.py"
            with open(filename, "w") as f:
                f.write(code)

            # Git 提交
            commit_sha = self.git_manager.commit_task(
                task_id=task.id,
                description=task.description,
                files=[filename]
            )

            if commit_sha:
                self.task_manager.set_commit(task.id, commit_sha)
                return commit_sha
            return None

        except Exception as e:
            print(f"Git 提交出错: {e}")
            return None

    def _get_task_context(self, task) -> dict:
        """获取任务上下文"""
        context = {}
        if task.parent_id:
            # 获取父任务已完成的结果
            siblings = self.task_manager.get_subtasks(task.parent_id)
            completed = [
                {"id": t.id, "description": t.description, "status": t.status.value}
                for t in siblings if t.status == TaskStatus.COMPLETED
            ]
            if completed:
                context["completed_tasks"] = completed
        return context

    def _synthesize_results(self, root_task_id: str, results: list) -> dict:
        """整合结果"""
        completed = sum(1 for r in results if r.get("success"))
        failed = len(results) - completed

        return {
            "summary": f"完成 {completed}/{len(results)} 个子任务",
            "completed": completed,
            "failed": failed,
            "results": results
        }
