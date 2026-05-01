/**
 * App 主组件
 */

import { useEffect } from 'react';
import { Brain, Settings, User } from 'lucide-react';
import {
  ConversationList,
  ChatPanel,
  AgentBoard,
  TaskKanban,
  LogStream,
} from '@/components';
import { useConversation } from '@/hooks';

function App() {
  const {
    currentConversation,
    logs,
    tasks,
    fetchConversations,
    connectWebSocket,
    disconnectWebSocket,
  } = useConversation();

  // 初始化
  useEffect(() => {
    fetchConversations();

    return () => {
      disconnectWebSocket();
    };
  }, []);

  // 连接 WebSocket 当选择对话时
  useEffect(() => {
    if (currentConversation) {
      connectWebSocket();
    }

    return () => {
      disconnectWebSocket();
    };
  }, [currentConversation?.id]);

  return (
    <div className="h-screen flex flex-col bg-slate-900">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
            <Brain className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Agency Visual</h1>
            <p className="text-xs text-slate-500">可视化多智能体协作平台</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors">
            <Settings className="w-5 h-5" />
          </button>
          <button className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded-lg transition-colors">
            <User className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Conversation List */}
        <aside className="w-72 bg-slate-800 border-r border-slate-700 overflow-hidden flex flex-col">
          <ConversationList />
        </aside>

        {/* Main Panel */}
        <main className="flex-1 flex flex-col overflow-hidden p-6 gap-6">
          {currentConversation ? (
            <>
              {/* Agent Board */}
              <AgentBoard
                status={currentConversation.status}
              />

              {/* Task Kanban (optional, can be collapsed) */}
              {tasks.length > 0 && (
                <TaskKanban tasks={tasks} />
              )}

              {/* Log Stream */}
              <LogStream logs={logs} maxHeight="300px" />

              {/* Chat Panel */}
              <div className="flex-1 min-h-0">
                <ChatPanel />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-primary-500/20 flex items-center justify-center">
                  <Brain className="w-10 h-10 text-primary-400" />
                </div>
                <h2 className="text-2xl font-bold text-slate-200 mb-2">
                  欢迎使用 Agency Visual
                </h2>
                <p className="text-slate-500 mb-6">
                  选择左侧对话列表中的对话，或创建新对话开始使用
                </p>
                <div className="flex items-center justify-center gap-6 text-sm text-slate-600">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500" />
                    <span>编排器</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span>编码器</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span>审查器</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amber-500" />
                    <span>测试器</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;