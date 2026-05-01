/**
 * AgentBoard Agent 可视化组件
 */

import { clsx } from 'clsx';
import { Bot, Code, Eye, FlaskConical, ArrowRight } from 'lucide-react';
import type { AgentType, ConversationStatus } from '@/types';

interface AgentNode {
  type: AgentType;
  name: string;
  icon: typeof Bot;
  color: string;
  description: string;
}

const AGENTS: AgentNode[] = [
  {
    type: 'orchestrator',
    name: '编排器',
    icon: Bot,
    color: 'purple',
    description: '分解任务，分配工作',
  },
  {
    type: 'coder',
    name: '编码器',
    icon: Code,
    color: 'blue',
    description: '生成高质量代码',
  },
  {
    type: 'reviewer',
    name: '审查器',
    icon: Eye,
    color: 'green',
    description: '代码审查与建议',
  },
  {
    type: 'tester',
    name: '测试器',
    icon: FlaskConical,
    color: 'amber',
    description: '验证功能正确性',
  },
];

interface AgentBoardProps {
  status: ConversationStatus;
  currentAgent?: AgentType;
  onAgentClick?: (agentType: AgentType) => void;
}

export function AgentBoard({ status, currentAgent, onAgentClick }: AgentBoardProps) {
  const isRunning = status === 'running';

  const getColorClasses = (color: string, isActive: boolean) => {
    const colors: Record<string, { bg: string; border: string; text: string; active: string }> = {
      purple: {
        bg: 'bg-purple-500/20',
        border: 'border-purple-500/50',
        text: 'text-purple-400',
        active: 'ring-purple-500',
      },
      blue: {
        bg: 'bg-blue-500/20',
        border: 'border-blue-500/50',
        text: 'text-blue-400',
        active: 'ring-blue-500',
      },
      green: {
        bg: 'bg-green-500/20',
        border: 'border-green-500/50',
        text: 'text-green-400',
        active: 'ring-green-500',
      },
      amber: {
        bg: 'bg-amber-500/20',
        border: 'border-amber-500/50',
        text: 'text-amber-400',
        active: 'ring-amber-500',
      },
    };
    const c = colors[color] || colors.blue;
    return {
      bg: c.bg,
      border: c.border,
      text: c.text,
      ring: isActive ? c.active : 'ring-transparent',
    };
  };

  return (
    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">Agent 工作状态</h2>

      <div className="flex items-center justify-between">
        {AGENTS.map((agent, index) => {
          const isActive = currentAgent === agent.type;
          const isExecuting = isRunning && isActive;
          const classes = getColorClasses(agent.color, isActive);
          const Icon = agent.icon;

          return (
            <div key={agent.type} className="flex items-center">
              <div className="flex flex-col items-center">
                <button
                  onClick={() => onAgentClick?.(agent.type)}
                  className={clsx(
                    'w-16 h-16 rounded-2xl border-2 flex items-center justify-center transition-all',
                    'hover:scale-105 hover:shadow-lg',
                    classes.bg,
                    classes.border,
                    isExecuting && 'ring-4 ring-offset-2 ring-offset-slate-900 animate-pulse'
                  )}
                  disabled={!isRunning}
                >
                  <Icon className={clsx('w-8 h-8', classes.text)} />
                </button>
                <span className={clsx('mt-2 text-sm font-medium', classes.text)}>
                  {agent.name}
                </span>
                {isExecuting && (
                  <span className="mt-1 text-xs text-slate-500 animate-pulse">
                    执行中...
                  </span>
                )}
              </div>

              {index < AGENTS.length - 1 && (
                <ArrowRight className="w-6 h-6 text-slate-600 mx-2" />
              )}
            </div>
          );
        })}
      </div>

      {/* 状态指示 */}
      <div className="mt-6 flex items-center justify-center gap-4">
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              'w-3 h-3 rounded-full',
              status === 'idle' && 'bg-slate-500',
              status === 'running' && 'bg-green-500 animate-pulse',
              status === 'paused' && 'bg-amber-500',
              status === 'completed' && 'bg-blue-500',
              status === 'failed' && 'bg-red-500'
            )}
          />
          <span className="text-sm text-slate-400">
            {status === 'idle' && '等待开始'}
            {status === 'running' && '执行中'}
            {status === 'paused' && '已暂停'}
            {status === 'completed' && '已完成'}
            {status === 'failed' && '执行失败'}
          </span>
        </div>
      </div>
    </div>
  );
}