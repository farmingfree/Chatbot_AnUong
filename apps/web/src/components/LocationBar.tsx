'use client';

import { useState } from 'react';
import { LocationState, LocationStatus } from '@/hooks/useLocation';

interface LocationBarProps {
  location: LocationState;
  onRequestLocation: () => void;
  onSetManualLocation: (address: string) => void;
  onClearLocation: () => void;
}

export function LocationBar({
  location,
  onRequestLocation,
  onSetManualLocation,
  onClearLocation,
}: LocationBarProps) {
  const [manualInput, setManualInput] = useState('');
  const [showInput, setShowInput] = useState(false);

  const handleSubmitManual = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualInput.trim()) {
      onSetManualLocation(manualInput.trim());
      setShowInput(false);
      setManualInput('');
    }
  };

  if (location.status === 'idle') {
    return (
      <div className="flex items-center justify-between px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800">
        <span className="text-xs text-blue-700 dark:text-blue-300">
          📍 Cho phép vị trí để tìm quán gần bạn
        </span>
        <button
          onClick={onRequestLocation}
          className="text-xs font-medium px-3 py-1 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors"
        >
          Bật vị trí
        </button>
      </div>
    );
  }

  if (location.status === 'loading') {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800">
        <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-blue-700 dark:text-blue-300">Đang xác định vị trí...</span>
      </div>
    );
  }

  if (location.status === 'granted') {
    return (
      <div className="flex items-center justify-between px-4 py-2 bg-green-50 dark:bg-green-900/20 border-b border-green-100 dark:border-green-800">
        <span className="text-xs text-green-700 dark:text-green-300">
          📍 {location.district || location.address || 'Đã xác định vị trí'}
        </span>
        <button
          onClick={() => setShowInput(true)}
          className="text-[10px] text-green-600 dark:text-green-400 hover:underline"
        >
          Đổi
        </button>
        {showInput && (
          <form onSubmit={handleSubmitManual} className="absolute top-full left-0 right-0 p-3 bg-white dark:bg-gray-800 shadow-lg border-b z-10">
            <div className="flex gap-2">
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="Nhập địa chỉ mới..."
                className="flex-1 text-sm px-3 py-1.5 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
                autoFocus
              />
              <button type="submit" className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg">OK</button>
              <button type="button" onClick={() => setShowInput(false)} className="text-xs px-2 text-gray-500">✕</button>
            </div>
          </form>
        )}
      </div>
    );
  }

  if (location.status === 'denied') {
    return (
      <div className="px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-100 dark:border-yellow-800">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-yellow-700 dark:text-yellow-300">
            📍 Nhập địa chỉ thủ công
          </span>
        </div>
        <form onSubmit={handleSubmitManual} className="flex gap-2">
          <input
            type="text"
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            placeholder="VD: Quận 1, HCM"
            className="flex-1 text-xs px-3 py-1.5 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
          />
          <button type="submit" className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg">
            Xác nhận
          </button>
        </form>
      </div>
    );
  }

  // status === 'manual'
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-green-50 dark:bg-green-900/20 border-b border-green-100 dark:border-green-800 relative">
      <span className="text-xs text-green-700 dark:text-green-300 truncate max-w-[70%]">
        📍 {location.address || 'Vị trí thủ công'}
      </span>
      <button
        onClick={() => setShowInput(true)}
        className="text-[10px] text-green-600 dark:text-green-400 hover:underline"
      >
        Đổi
      </button>
      {showInput && (
        <form onSubmit={handleSubmitManual} className="absolute top-full left-0 right-0 p-3 bg-white dark:bg-gray-800 shadow-lg border-b z-10">
          <div className="flex gap-2">
            <input
              type="text"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="Nhập địa chỉ mới..."
              className="flex-1 text-sm px-3 py-1.5 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
              autoFocus
            />
            <button type="submit" className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg">OK</button>
            <button type="button" onClick={() => setShowInput(false)} className="text-xs px-2 text-gray-500">✕</button>
          </div>
        </form>
      )}
    </div>
  );
}
