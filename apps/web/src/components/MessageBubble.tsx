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

  // User message
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4 animate-fadeIn">
        <div className="max-w-[80%]">
          <div className="bg-blue-600 text-white rounded-2xl px-4 py-3">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  // Assistant message - text
  if (message.type === 'text' || !message.type) {
    return (
      <div className="flex justify-start mb-4 animate-fadeIn">
        <div className="w-full">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl px-4 py-3">
            <div className="prose dark:prose-invert max-w-none">
              <p className="whitespace-pre-wrap m-0">{message.content}</p>
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTime(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  // Assistant message - places
  if (message.type === 'places' && message.data) {
    return (
      <div className="mb-4 animate-fadeIn">
        <RestaurantGrid places={message.data} />
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {formatTime(message.timestamp)}
        </div>
      </div>
    );
  }

  // Assistant message - dishes
  if (message.type === 'dishes' && message.data) {
    return (
      <div className="mb-4 animate-fadeIn">
        <DishGrid dishes={message.data} />
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {formatTime(message.timestamp)}
        </div>
      </div>
    );
  }

  // Assistant message - place detail
  if (message.type === 'place_detail' && message.data) {
    const place = message.data.place || message.data;
    return (
      <div className="mb-4 animate-fadeIn">
        <div className="border rounded-lg overflow-hidden bg-white dark:bg-gray-800 max-w-2xl">
          {place.image_url && (
            <img
              src={place.image_url}
              alt={place.name}
              className="w-full h-64 object-cover"
            />
          )}
          <div className="p-6">
            <h2 className="text-2xl font-bold mb-2">{place.name}</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{place.address}</p>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              {place.rating && (
                <div>
                  <span className="text-sm text-gray-500">Đánh giá</span>
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-500">⭐</span>
                    <span className="font-semibold">{place.rating.toFixed(1)}</span>
                  </div>
                </div>
              )}
              
              {place.distance_m !== undefined && (
                <div>
                  <span className="text-sm text-gray-500">Khoảng cách</span>
                  <div className="font-semibold">
                    {place.distance_m < 1000
                      ? `${Math.round(place.distance_m)}m`
                      : `${(place.distance_m / 1000).toFixed(1)}km`}
                  </div>
                </div>
              )}
            </div>

            {place.cuisine_types && place.cuisine_types.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {place.cuisine_types.map((cuisine: string, idx: number) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm"
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
