# Agency Visual

可视化多智能体协作平台，基于 msitarzewski/agency-agents 实现。

## 功能特性

- 🎨 **可视化界面**：实时展示 Agent 工作状态
- 🔄 **多 Agent 协作**：Orchestrator、Coder、Reviewer、Tester 协同完成任务
- 💬 **实时交互**：用户可随时加入对话补充信息
- 📁 **对话即项目**：每个对话对应一个 Git 项目
- 🤖 **多 LLM 支持**：Ollama、Anthropic、GLM、DeepSeek

## 项目结构

```
agency-visual/
├── backend/                 # Python FastAPI 后端
│   ├── agents/             # Agent 实现
│   ├── api/                # API 路由
│   ├── core/               # 核心组件
│   ├── db/                 # 数据库
│   ├── git/                # Git 操作
│   ├── llm/                # LLM 网关
│   └── websocket/          # WebSocket 管理
├── frontend/               # React + TypeScript 前端
│   └── src/
│       ├── components/     # UI 组件
│       ├── hooks/          # 自定义 Hooks
│       ├── services/       # API 客户端
│       ├── stores/         # 状态管理
│       └── types/          # 类型定义
└── generated_projects/     # 生成的 Git 项目
```

## 快速开始

### 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agency_visual
export LLM_BACKEND=ollama
export LLM_MODEL=gemma2:9b

# 启动服务
python main.py
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### Ollama (可选)

如果使用本地 Ollama 模型：

```bash
# ���装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull gemma2:9b

# 启动 Ollama
ollama serve
```

## API

### 对话管理

- `POST /api/conversations` - 创建对话
- `GET /api/conversations` - 获取对话列表
- `GET /api/conversations/{id}` - 获取对话详情
- `DELETE /api/conversations/{id}` - 删除对话

### Agent 控制

- `POST /api/conversations/{id}/start` - 启动任务
- `POST /api/conversations/{id}/pause` - 暂停
- `POST /api/conversations/{id}/resume` - 恢复
- `POST /api/conversations/{id}/stop` - 停止

### Git 操作

- `GET /api/conversations/{id}/git/status` - Git 状态
- `GET /api/conversations/{id}/git/log` - 提交历史
- `POST /api/conversations/{id}/git/commit` - 提交

### WebSocket

- `ws://localhost:8000/ws/{conversation_id}` - 实时事件

## License

MIT