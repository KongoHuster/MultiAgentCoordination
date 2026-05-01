/**
 * ConversationList 对话列表组件
 */

import { useState } from 'react';
import { Plus, Trash2, Clock, Loader2 } from 'lucide-react';
import { useConversation } from '@/hooks';
import { Button, Input, Modal } from '../common';
import type { Conversation } from '@/types';
import { clsx } from 'clsx';

export function ConversationList() {
  const {
    conversations,
    currentConversation,
    isLoading,
    createConversation,
    selectConversation,
    deleteConversation,
  } = useConversation();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;

    setIsCreating(true);
    try {
      const conversation = await createConversation(newName);
      setIsCreateModalOpen(false);
      setNewName('');
      await selectConversation(conversation.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelect = async (id: string) => {
    await selectConversation(id);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('确定要删除这个对话吗？')) {
      await deleteConversation(id);
    }
  };

  const getStatusBadge = (status: Conversation['status']) => {
    const badges = {
      idle: { label: '空闲', className: 'bg-slate-500/20 text-slate-400' },
      running: { label: '运行中', className: 'bg-green-500/20 text-green-400' },
      paused: { label: '已暂停', className: 'bg-amber-500/20 text-amber-400' },
      completed: { label: '已完成', className: 'bg-blue-500/20 text-blue-400' },
      failed: { label: '失败', className: 'bg-red-500/20 text-red-400' },
    };
    const badge = badges[status] || badges.idle;
    return (
      <span className={clsx('px-2 py-0.5 text-xs rounded-full', badge.className)}>
        {badge.label}
      </span>
    );
  };

  const formatDate = (dateStr: string | undefined | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '-';
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <Button
          variant="primary"
          size="sm"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => setIsCreateModalOpen(true)}
          className="w-full"
        >
          新建对话
        </Button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && conversations.length === 0 ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>暂无对话</p>
            <p className="text-sm mt-2">点击上方按钮创建新对话</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-700/50">
            {conversations.map((conversation) => (
              <li
                key={conversation.id}
                onClick={() => handleSelect(conversation.id)}
                className={clsx(
                  'p-4 cursor-pointer transition-colors',
                  currentConversation?.id === conversation.id
                    ? 'bg-primary-500/10 border-l-2 border-primary-500'
                    : 'hover:bg-slate-800/50'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-slate-200 truncate">
                        {conversation.name}
                      </h3>
                      {getStatusBadge(conversation.status)}
                    </div>
                    <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
                      <Clock className="w-3 h-3" />
                      {formatDate(conversation.createdAt)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conversation.id)}
                    className="p-1 text-slate-500 hover:text-red-400 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Create Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setNewName('');
        }}
        title="创建新对话"
      >
        <div className="space-y-4">
          <Input
            label="对话名称"
            placeholder="输入对话名称"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setIsCreateModalOpen(false);
                setNewName('');
              }}
            >
              取消
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              isLoading={isCreating}
              disabled={!newName.trim()}
            >
              创建
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}