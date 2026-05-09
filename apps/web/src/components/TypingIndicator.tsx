export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 p-3 sm:p-4 animate-fadeIn">
      <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-3 py-2 sm:px-4 sm:py-3 flex items-center gap-2">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Đang trả lời...</span>
      </div>
    </div>
  );
}
