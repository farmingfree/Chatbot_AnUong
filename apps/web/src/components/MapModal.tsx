'use client';

import { useEffect, useState } from 'react';
import { MapView } from './MapView';
import { PlaceCard } from '@/types/chat';

interface MapModalProps {
  isOpen: boolean;
  onClose: () => void;
  places?: PlaceCard[];
  userLocation: { lat: number; lng: number } | null;
}

export function MapModal({ isOpen, onClose, places = [], userLocation }: MapModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!mounted || !isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-6xl h-[80vh] bg-white dark:bg-gray-800 rounded-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xl">🗺️</span>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Bản đồ
            </h2>
            {places.length > 0 && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({places.length} địa điểm)
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Đóng bản đồ"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Map Content */}
        <div className="flex-1 relative">
          {userLocation ? (
            <MapView
              places={places}
              userLocation={userLocation}
              radius={2000}
              className="h-full w-full"
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-4">
              <span className="text-6xl mb-4">📍</span>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
                Cần quyền truy cập vị trí
              </h3>
              <p className="text-gray-600 dark:text-gray-400 max-w-md mb-4">
                Vui lòng cho phép trình duyệt truy cập vị trí của bạn để hiển thị bản đồ
              </p>
              <button
                onClick={() => {
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                      () => window.location.reload(),
                      (error) => alert('Không thể lấy vị trí: ' + error.message)
                    );
                  }
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Cho phép truy cập vị trí
              </button>
            </div>
          )}
        </div>

        {/* Footer Info */}
        {userLocation && (
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 shrink-0">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <span>📍</span>
                <span>
                  Vị trí của bạn: {userLocation.lat.toFixed(4)}, {userLocation.lng.toFixed(4)}
                </span>
              </div>
              <div className="text-gray-500 dark:text-gray-500 text-xs">
                Dữ liệu từ OpenStreetMap
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
