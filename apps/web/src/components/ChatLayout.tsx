'use client';

import { ReactNode, useState, useEffect } from 'react';
import { ThemeToggle } from './ThemeToggle';

interface ChatLayoutProps {
  children: ReactNode;
  onNewChat?: () => void;
  sessionTitle?: string;
}

export function ChatLayout({ children, onNewChat, sessionTitle }: ChatLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside
        className={`
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          fixed md:static inset-y-0 left-0 z-50
          w-72 sm:w-80 md:w-64 bg-white dark:bg-gray-800
          border-r border-gray-200 dark:border-gray-700
          transition-transform duration-300 ease-in-out
          flex flex-col
          shadow-xl md:shadow-none
        `}
      >
        {/* Sidebar Header */}
        <div className="p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700 shrink-0">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🍜</span>
              <h1 className="font-semibold text-base sm:text-lg text-gray-900 dark:text-gray-100">Ăn gì cũng được</h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="md:hidden p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-700 dark:text-gray-300"
              aria-label="Đóng menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button
            onClick={() => {
              onNewChat?.();
              setSidebarOpen(false);
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 sm:py-2
                     bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white
                     rounded-lg transition-colors font-medium text-sm sm:text-base
                     touch-manipulation"
          >
            <span className="text-lg sm:text-xl">+</span>
            <span>Chat mới</span>
          </button>
        </div>

        {/* Chat Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 overscroll-contain">
          <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 px-2 mb-2">
            Lịch sử chat
          </div>
          <div className="text-xs sm:text-sm text-gray-400 dark:text-gray-500 px-2 py-4 text-center">
            Chưa có lịch sử chat
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 sm:p-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
          <button className="w-full flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors touch-manipulation">
            <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center shrink-0">
              <span className="text-sm">👤</span>
            </div>
            <span className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 truncate">Đăng nhập</span>
          </button>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
          aria-label="Đóng menu"
        />
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3 sm:p-4 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-1.5 sm:p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors touch-manipulation shrink-0 text-gray-700 dark:text-gray-300"
                aria-label="Mở menu"
              >
                <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h2 className="font-semibold text-base sm:text-lg truncate text-gray-900 dark:text-gray-100">
                {sessionTitle || 'Chat mới'}
              </h2>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <ThemeToggle />
              <div className="hidden sm:flex items-center gap-1 text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                <span>📍</span>
                <span className="hidden md:inline">TP. Hồ Chí Minh</span>
                <span className="md:hidden">HCM</span>
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
