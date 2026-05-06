'use client';

import { ReactNode, useState } from 'react';

interface ChatLayoutProps {
  children: ReactNode;
  onNewChat?: () => void;
  sessionTitle?: string;
}

export function ChatLayout({ children, onNewChat, sessionTitle }: ChatLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside
        className={`
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          fixed md:static inset-y-0 left-0 z-50
          w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700
          transition-transform duration-300 ease-in-out
          flex flex-col
        `}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">🍜</span>
            <h1 className="font-semibold text-lg">Ăn gì cũng được</h1>
          </div>
          
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 
                     bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <span className="text-xl">+</span>
            <span>Chat mới</span>
          </button>
        </div>

        {/* Chat Sessions List */}
        <div className="flex-1 overflow-y-auto p-2">
          <div className="text-sm text-gray-500 dark:text-gray-400 px-2 mb-2">
            Lịch sử chat
          </div>
          {/* TODO: Load chat sessions from localStorage */}
          <div className="text-sm text-gray-400 dark:text-gray-500 px-2 py-4 text-center">
            Chưa có lịch sử chat
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
              <span className="text-sm">👤</span>
            </div>
            <span className="text-sm text-gray-600 dark:text-gray-400">Đăng nhập</span>
          </div>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h2 className="font-semibold text-lg">
                {sessionTitle || 'Chat mới'}
              </h2>
            </div>

            <div className="flex items-center gap-2">
              {/* Location indicator */}
              <div className="hidden sm:flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                <span>📍</span>
                <span>TP. Hồ Chí Minh</span>
              </div>
            </div>
          </div>
        </header>

        {/* Messages Area */}
        {children}
      </main>
    </div>
  );
}
