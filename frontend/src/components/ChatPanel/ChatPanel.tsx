/**
 * ChatPanel 聊天面板组件
 */

import { useState, useRef, useEffect, FormEvent } from 'react';
import { Send, Square, Pause, Play } from 'lucide-react';
import { useConversation } from '@/hooks';
import { Button } from '../common';
import { clsx } from 'clsx';

export function ChatPanel() {
  const {
    currentConversation,
    messages,
    logs,
    sendMessage,
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    stopWorkflow,
  } = useConversation();

  const [input, setInput] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动调整输入框高度
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSubmit = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!input.trim()) return;

    if (!currentConversation) return;

    if (currentConversation.status === 'idle') {
      // 启动工作流
      setIsStarting(true);
      try {
        await sendMessage(input);
        await startWorkflow(input);
      } catch (error) {
        console.error('Failed to start workflow:', error);
      } finally {
        setIsStarting(false);
      }
    } else {
      // 发送消息
      await sendMessage(input);
    }

    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isRunning = currentConversation?.status === 'running';
  const isPaused = currentConversation?.status === 'paused';

  return (
    <div className="flex flex-col h-full bg-slate-800/50 rounded-xl border border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-slate-200">
          {currentConversation?.name || '聊天'}
        </h2>
        <div className="flex items-center gap-2">
          {isRunning && (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<Pause className="w-4 h-4" />}
              onClick={pauseWorkflow}
            >
              暂停
            </Button>
          )}
          {isPaused && (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<Play className="w-4 h-4" />}
              onClick={resumeWorkflow}
            >
              继续
            </Button>
          )}
          {(isRunning || isPaused) && (
            <Button
              variant="danger"
              size="sm"
              leftIcon={<Square className="w-4 h-4" />}
              onClick={stopWorkflow}
            >
              停止
            </Button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <p className="text-lg mb-2">开始一个新任务</p>
            <p className="text-sm">在下方输入框中描述你想要完成的任务</p>
          </div>
        ) : (
          <>
            {/* Logs as system messages */}
            {logs.map((log) => (
              <div
                key={log.id}
                className={clsx(
                  'flex gap-2 text-sm',
                  log.agentName === 'user' ? 'flex-row-reverse' : ''
                )}
              >
                <div
                  className={clsx(
                    'max-w-[80%] rounded-lg px-3 py-2',
                    log.agentName === 'user'
                      ? 'bg-primary-500/20 text-primary-300'
                      : log.level === 'error'
                      ? 'bg-red-500/20 text-red-300'
                      : log.level === 'warning'
                      ? 'bg-amber-500/20 text-amber-300'
                      : log.level === 'success'
                      ? 'bg-green-500/20 text-green-300'
                      : 'bg-slate-700 text-slate-300'
                  )}
                >
                  {log.content}
                </div>
              </div>
            ))}

            {/* User messages */}
            {messages
              .filter((m) => m.sender === 'user')
              .map((message) => (
                <div key={message.id} className="flex gap-2 text-sm flex-row-reverse">
                  <div className="max-w-[80%] rounded-lg px-3 py-2 bg-primary-500/20 text-primary-300">
                    {message.content}
                  </div>
                </div>
              ))}
          </>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="p-4 border-t border-slate-700"
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              currentConversation?.status === 'idle'
                ? '描述你要完成的任务...'
                : '输入消息...'
            }
            className={clsx(
              'flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2',
              'text-slate-100 placeholder-slate-500 resize-none',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              'max-h-32'
            )}
            rows={1}
            disabled={isStarting}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={!input.trim() || isStarting}
            isLoading={isStarting}
            leftIcon={<Send className="w-4 h-4" />}
          >
            {currentConversation?.status === 'idle' ? '开始' : '发送'}
          </Button>
        </div>
      </form>
    </div>
  );
}