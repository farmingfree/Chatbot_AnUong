'use client';

import { useConversations } from '@/contexts/ConversationContext';
import { useState } from 'react';
import { Conversation } from '@/types/conversation';

export function ConversationSidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const {
    conversations,
    activeConversationId,
    createConversation,
    deleteConversation,
    renameConversation,
    togglePinConversation,
    switchConversation,
  } = useConversations();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const handleRename = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const saveRename = (id: string) => {
    if (editTitle.trim()) {
      renameConversation(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleNewChat = () => {
    createConversation();
    onClose();
  };

  const handleSwitch = (id: string) => {
    switchConversation(id);
    onClose();
  };

  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Vừa xong';
    if (minutes < 60) return `${minutes} phút trước`;
    if (hours < 24) return `${hours} giờ trước`;
    if (days < 7) return `${days} ngày trước`;
    return date.toLocaleDateString('vi-VN');
  };

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl z-50 transform transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 lg:relative lg:shadow-none`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Lịch sử trò chuyện
              </h2>
              <button
                onClick={onClose}
                className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <button
              onClick={handleNewChat}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              + Cuộc trò chuyện mới
            </button>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto p-2">
            {conversations.length === 0 ? (
              <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
                Chưa có cuộc trò chuyện nào
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group relative mb-2 p-3 rounded-lg cursor-pointer transition-colors ${
                    activeConversationId === conv.id
                      ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  onClick={() => handleSwitch(conv.id)}
                >
                  {/* Pin Icon */}
                  {conv.isPinned && (
                    <div className="absolute top-2 right-2">
                      <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" />
                      </svg>
                    </div>
                  )}

                  {/* Title */}
                  {editingId === conv.id ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => saveRename(conv.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveRename(conv.id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      className="w-full px-2 py-1 text-sm font-medium bg-white dark:bg-gray-700 border border-blue-500 rounded"
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate pr-6">
                      {conv.title}
                    </h3>
                  )}

                  {/* Last Message */}
                  {conv.lastMessage && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">
                      {conv.lastMessage}
                    </p>
                  )}

                  {/* Timestamp & Message Count */}
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-400 dark:text-gray-500">
                    <span>{formatTimestamp(conv.timestamp)}</span>
                    {conv.messageCount > 0 && (
                      <span>{conv.messageCount} tin nhắn</span>
                    )}
                  </div>

                  {/* Action Buttons (show on hover) */}
                  <div className="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePinConversation(conv.id);
                      }}
                      className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      title={conv.isPinned ? 'Bỏ ghim' : 'Ghim'}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(conv);
                      }}
                      className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                      title="Đổi tên"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('Xóa cuộc trò chuyện này?')) {
                          deleteConversation(conv.id);
                        }
                      }}
                      className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 rounded"
                      title="Xóa"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
