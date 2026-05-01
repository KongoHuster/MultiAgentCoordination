/**
 * LogStream 实时日志流组件
 */

import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import { Bot, User, AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import type { LogEntry } from '@/types';

interface LogStreamProps {
  logs: LogEntry[];
  maxHeight?: string;
  onClear?: () => void;
}

export function LogStream({ logs, maxHeight = '400px', onClear }: LogStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const getAgentIcon = (agentName: string) => {
    if (agentName === 'user') {
      return <User className="w-4 h-4" />;
    }
    if (agentName === 'system' || agentName === 'git') {
      return <Info className="w-4 h-4" />;
    }
    return <Bot className="w-4 h-4" />;
  };

  const getAgentColor = (agentName: string) => {
    const colors: Record<string, string> = {
      orchestrator: 'text-purple-400',
      coder: 'text-blue-400',
      reviewer: 'text-green-400',
      tester: 'text-amber-400',
      user: 'text-slate-300',
      system: 'text-slate-400',
      git: 'text-emerald-400',
    };
    return colors[agentName] || 'text-slate-400';
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-slate-200">实时日志</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{logs.length} 条记录</span>
          {onClear && (
            <button
              onClick={onClear}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              清空
            </button>
          )}
        </div>
      </div>

      {/* Log List */}
      <div
        ref={containerRef}
        className="overflow-y-auto p-4 space-y-2"
        style={{ maxHeight }}
      >
        {logs.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            暂无日志
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className={clsx(
                'flex items-start gap-3 p-2 rounded-lg transition-colors',
                log.level === 'error' && 'bg-red-500/10',
                log.level === 'warning' && 'bg-amber-500/10',
                log.level === 'success' && 'bg-green-500/10'
              )}
            >
              {/* Timestamp */}
              <span className="text-xs text-slate-600 font-mono shrink-0">
                [{formatTimestamp(log.timestamp)}]
              </span>

              {/* Agent Icon */}
              <div className={clsx('shrink-0', getAgentColor(log.agentName || ''))}>
                {getAgentIcon(log.agentName || '')}
              </div>

              {/* Level Icon */}
              {getLevelIcon(log.level)}

              {/* Content */}
              <span className={clsx('text-sm flex-1', getAgentColor(log.agentName || ''))}>
                {log.content}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}