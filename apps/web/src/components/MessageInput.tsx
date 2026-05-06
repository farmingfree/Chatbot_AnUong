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

  // Auto-resize textarea
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
    <div className="border-t bg-white dark:bg-gray-900 p-4">
      {/* Quick chips */}
      <div className="flex flex-wrap gap-2 mb-3">
        {QUICK_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => handleChipClick(chip)}
            disabled={isStreaming}
            className="text-sm px-3 py-1.5 rounded-full border border-gray-300 dark:border-gray-600 
                     hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors
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
          placeholder={isStreaming ? 'Đang trả lời...' : 'Nhập tin nhắn... (Enter để gửi, Shift+Enter để xuống dòng)'}
          disabled={isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 
                   bg-white dark:bg-gray-800 px-4 py-3 
                   focus:outline-none focus:ring-2 focus:ring-blue-500
                   disabled:opacity-50 disabled:cursor-not-allowed
                   max-h-32 overflow-y-auto"
        />
        <button
          onClick={handleSubmit}
          disabled={!inputValue.trim() || isStreaming}
          className="px-6 py-3 rounded-lg bg-blue-600 text-white font-medium
                   hover:bg-blue-700 transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
        >
          Gửi
        </button>
      </div>
    </div>
  );
}
