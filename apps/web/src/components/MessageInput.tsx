'use client';

import { useState, useRef, useEffect } from 'react';

interface MessageInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
}

const QUICK_CHIPS = [
  '🍜 Gợi ý cho tôi',
  '💰 Dưới 50k',
  '🌿 Ăn chay',
  '📍 Gần đây nhất',
  '👥 Đi 2 người',
  '🔀 Random cho tôi',
];

export function MessageInput({ onSend, isStreaming }: MessageInputProps) {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputValue]);

  const handleSubmit = () => {
    if (inputValue.trim() && !isStreaming) {
      onSend(inputValue.trim());
      setInputValue('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (chip: string) => {
    const text = chip.replace(/^[\u{1F300}-\u{1F9FF}]\s*/u, '').trim();
    setInputValue((prev) => (prev ? `${prev} ${text}` : text));
    textareaRef.current?.focus();
  };

  return (
    <div className="border-t bg-white dark:bg-gray-900 p-3 sm:p-4 shrink-0">
      {/* Quick chips */}
      <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-2 sm:mb-3 overflow-x-auto pb-1 scrollbar-hide">
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => handleChipClick(chip)}
            disabled={isStreaming}
            className="text-xs sm:text-sm px-2.5 py-1.5 sm:px-3 rounded-full border border-gray-300 dark:border-gray-600
                     hover:bg-gray-100 dark:hover:bg-gray-800 active:bg-gray-200 dark:active:bg-gray-700
                     transition-colors whitespace-nowrap touch-manipulation
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'Đang trả lời...' : 'Nhập tin nhắn...'}
          disabled={isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600
                   bg-white dark:bg-gray-800 px-3 py-2.5 sm:px-4 sm:py-3
                   text-sm sm:text-base
                   focus:outline-none focus:ring-2 focus:ring-blue-500
                   disabled:opacity-50 disabled:cursor-not-allowed
                   max-h-32 overflow-y-auto touch-manipulation"
        />
        <button
          onClick={handleSubmit}
          disabled={!inputValue.trim() || isStreaming}
          className="px-4 py-2.5 sm:px-6 sm:py-3 rounded-lg bg-blue-600 text-white font-medium text-sm sm:text-base
                   hover:bg-blue-700 active:bg-blue-800 transition-colors touch-manipulation shrink-0
                   disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
        >
          Gửi
        </button>
      </div>

      {/* Mobile hint */}
      <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center sm:hidden">
        Enter để gửi, Shift+Enter để xuống dòng
      </div>
    </div>
  );
}
