'use client';

import { Message } from '@/types/chat';
import { RestaurantGrid } from './RestaurantCard';
import { DishGrid } from './DishCard';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-3 sm:mb-4 animate-fadeIn px-2 sm:px-0">
        <div className="max-w-[85%] sm:max-w-[80%]">
          <div className="bg-blue-600 text-white rounded-2xl px-3 py-2 sm:px-4 sm:py-3">
            <p className="whitespace-pre-wrap text-sm sm:text-base break-words">{message.content}</p>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  if (message.type === 'text' || !message.type) {
    return (
      <div className="flex justify-start mb-3 sm:mb-4 animate-fadeIn px-2 sm:px-0">
        <div className="w-full max-w-full sm:max-w-[90%]">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-3 py-2 sm:px-4 sm:py-3">
            <div className="prose dark:prose-invert max-w-none prose-sm sm:prose-base">
              <p className="whitespace-pre-wrap m-0 break-words">{message.content}</p>
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  if (message.type === 'places' && message.data) {
    return (
      <div className="mb-3 sm:mb-4 animate-fadeIn">
        <RestaurantGrid places={message.data} />
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2 sm:px-0">
          {formatTime(message.timestamp)}
        </div>
      </div>
    );
  }

  if (message.type === 'dishes' && message.data) {
    return (
      <div className="mb-3 sm:mb-4 animate-fadeIn">
        <DishGrid dishes={message.data} />
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 px-2 sm:px-0">
          {formatTime(message.timestamp)}
        </div>
      </div>
    );
  }

  if (message.type === 'place_detail' && message.data) {
    const place = message.data.place || message.data;
    return (
      <div className="mb-3 sm:mb-4 animate-fadeIn px-2 sm:px-0">
        <div className="border rounded-lg sm:rounded-xl overflow-hidden bg-white dark:bg-gray-800 max-w-full sm:max-w-2xl">
          {place.image_url && (
            <img
              src={place.image_url}
              alt={place.name}
              className="w-full h-48 sm:h-64 object-cover"
            />
          )}
          <div className="p-4 sm:p-6">
            <h2 className="text-xl sm:text-2xl font-bold mb-2 break-words">{place.name}</h2>
            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mb-4 break-words">{place.address}</p>

            <div className="grid grid-cols-2 gap-3 sm:gap-4 mb-4">
              {place.rating && (
                <div>
                  <span className="text-xs sm:text-sm text-gray-500">Đánh giá</span>
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-500">⭐</span>
                    <span className="font-semibold text-sm sm:text-base">{place.rating.toFixed(1)}</span>
                  </div>
                </div>
              )}

              {place.distance_m !== undefined && (
                <div>
                  <span className="text-xs sm:text-sm text-gray-500">Khoảng cách</span>
                  <div className="font-semibold text-sm sm:text-base">
                    {place.distance_m < 1000
                      ? `${Math.round(place.distance_m)}m`
                      : `${(place.distance_m / 1000).toFixed(1)}km`}
                  </div>
                </div>
              )}
            </div>

            {place.cuisine_types && place.cuisine_types.length > 0 && (
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {place.cuisine_types.map((cuisine: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-2 sm:px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-xs sm:text-sm"
                  >
                    {cuisine}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {formatTime(message.timestamp)}
        </div>
      </div>
    );
  }

  return null;
}
