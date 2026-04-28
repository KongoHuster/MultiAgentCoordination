# Multi-Agent Orchestration System

基于 Claude API 的多智能体编排系统，支持长时间运行和复杂任务处理。

## 架构

```
用户请求 → Orchestrator (任务分解) → Coder → Reviewer → Tester → Git提交
                                         ↑         ↓
                              主Agent判断 ← 失败重试 ← (最多3次)
```

## 组件

| Agent | 职责 |
|-------|------|
| Orchestrator | 任务分解、判断完成、调度 |
| Coder | 编写代码 |
| Reviewer | 代码审查 |
| Tester | 测试执行 |

## 目录结构

```
multi_agent/
├── main.py              # 入口
├── config.py            # 配置
├── workflow_engine.py   # 工作流引擎
├── shared_memory.py     # 共享内存
├── task_manager.py      # 任务管理
├── message_queue.py     # 消息队列
├── git_manager.py       # Git 操作
├── agents/
│   ├── base_agent.py
│   ├── orchestrator.py
│   ├── coder.py
│   ├── reviewer.py
│   └── tester.py
└── output/              # 生成的代码
```

## 配置

```bash
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://milukey.cn"
```

## 使用

```bash
cd multi_agent
python3 main.py "写一个计算器"
```

## 工作流程

1. **任务分解** - 主 Agent 分析并分解复杂任务
2. **编码** - Coder Agent 编写代码
3. **检视** - Reviewer Agent 审查代码
4. **测试** - Tester Agent 运行测试
5. **判断** - 主 Agent 根据测试结果判断是否完成
6. **提交** - 成功后自动 Git 提交

## 特性

- 自动任务分解
- 编码→检视→测试循环
- 失败自动重试（最多3次）
- 成功自动 Git 提交
- API 超时重试
