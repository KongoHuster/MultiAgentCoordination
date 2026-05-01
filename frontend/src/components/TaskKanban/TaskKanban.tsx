/**
 * TaskKanban 任务看板组件
 */

import { clsx } from 'clsx';
import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';
import type { Task } from '@/types';

interface TaskKanbanProps {
  tasks: Task[];
  onTaskClick?: (task: Task) => void;
}

export function TaskKanban({ tasks, onTaskClick }: TaskKanbanProps) {
  const columns = [
    { id: 'pending', label: '待处理', color: 'slate' },
    { id: 'running', label: '进行中', color: 'blue' },
    { id: 'completed', label: '已完成', color: 'green' },
    { id: 'failed', label: '失败', color: 'red' },
  ] as const;

  const getStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'pending':
        return <Circle className="w-4 h-4 text-slate-500" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Circle className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <h2 className="text-lg font-semibold text-slate-200 mb-4">任务进度</h2>

      <div className="grid grid-cols-4 gap-3">
        {columns.map((column) => {
          const columnTasks = tasks.filter((t) => t.status === column.id);

          return (
            <div
              key={column.id}
              className="bg-slate-900/50 rounded-lg p-3 border-t-2"
              style={{ borderColor: `var(--color-${column.color}-500, #${column.color})` }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-slate-300">{column.label}</span>
                <span className="px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-400">
                  {columnTasks.length}
                </span>
              </div>

              <div className="space-y-2 min-h-[100px]">
                {columnTasks.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => onTaskClick?.(task)}
                    className={clsx(
                      'w-full text-left p-2 rounded-lg transition-colors',
                      'bg-slate-800/50 hover:bg-slate-800 border border-transparent hover:border-slate-700'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {getStatusIcon(task.status)}
                      <span className="text-sm text-slate-300 line-clamp-2">
                        {task.description}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span
                        className={clsx(
                          'px-2 py-0.5 text-xs rounded',
                          task.priority === 'high'
                            ? 'bg-red-500/20 text-red-400'
                            : task.priority === 'low'
                            ? 'bg-slate-600 text-slate-400'
                            : 'bg-amber-500/20 text-amber-400'
                        )}
                      >
                        {task.priority === 'high' ? '高' : task.priority === 'low' ? '低' : '中'}
                      </span>
                      <span className="text-xs text-slate-500">
                        {task.agentType}
                      </span>
                    </div>
                  </button>
                ))}

                {columnTasks.length === 0 && (
                  <div className="text-center text-slate-600 text-sm py-4">
                    暂无任务
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}