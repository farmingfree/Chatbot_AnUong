'use client';

import { PlaceCard } from '@/types/chat';

const DISTRICT_GRADIENTS: Record<string, string> = {
  '1': 'from-orange-400 to-red-500',
  '2': 'from-blue-400 to-cyan-500',
  '3': 'from-purple-400 to-pink-500',
  '4': 'from-green-400 to-teal-500',
  '5': 'from-yellow-400 to-orange-500',
  '7': 'from-indigo-400 to-purple-500',
  'Bình Thạnh': 'from-rose-400 to-red-500',
  'Phú Nhuận': 'from-emerald-400 to-green-500',
  'Tân Bình': 'from-sky-400 to-blue-500',
  'Gò Vấp': 'from-amber-400 to-yellow-500',
  default: 'from-gray-400 to-gray-600',
};

function getGradient(district?: string): string {
  if (!district) return DISTRICT_GRADIENTS.default;
  return DISTRICT_GRADIENTS[district] || DISTRICT_GRADIENTS.default;
}

function getPriceLevelLabel(level?: number): string {
  if (!level) return '';
  return '₫'.repeat(level);
}

interface RestaurantCardProps {
  place: PlaceCard | null;
  isFavorited: boolean;
  onFavorite: () => void;
  onClick: () => void;
}

export function RestaurantCard({ place, isFavorited, onFavorite, onClick }: RestaurantCardProps) {
  // Skeleton loading
  if (!place) {
    return (
      <div className="w-full max-w-[320px] rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 animate-pulse">
        <div className="h-28 bg-gray-200 dark:bg-gray-700" />
        <div className="p-3 space-y-2">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
          <div className="flex gap-1">
            <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded-full" />
            <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded-full" />
          </div>
        </div>
        <div className="border-t border-gray-200 dark:border-gray-700 px-3 py-2 flex justify-between">
          <div className="h-6 w-6 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  const formatDistance = (m?: number) => {
    if (!m) return '';
    return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`;
  };

  return (
    <div className="w-full max-w-[320px] rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:shadow-lg transition-shadow cursor-pointer">
      {/* Image Area */}
      <div className="relative h-28 overflow-hidden" onClick={onClick}>
        {place.image_url ? (
          <img
            src={place.image_url}
            alt={place.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${getGradient(place.district)} flex items-center justify-center`}>
            <span className="text-4xl opacity-60">🍜</span>
          </div>
        )}

        {/* Overlay badges */}
        <div className="absolute top-2 left-2">
          {place.is_open !== undefined && (
            <span
              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                place.is_open
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-500 text-white'
              }`}
            >
              {place.is_open ? 'Đang mở' : 'Đóng cửa'}
            </span>
          )}
        </div>

        <div className="absolute top-2 right-2">
          {place.price_level && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/90 dark:bg-gray-900/90 text-gray-800 dark:text-gray-200">
              {getPriceLevelLabel(place.price_level)}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-3" onClick={onClick}>
        <h3 className="font-semibold text-sm truncate">{place.name}</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
          {place.address}
        </p>

        <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-600 dark:text-gray-400">
          {place.rating && (
            <span className="flex items-center gap-0.5">
              <span className="text-yellow-500">⭐</span>
              <span className="font-medium">{place.rating.toFixed(1)}</span>
            </span>
          )}
          {place.review_count && (
            <>
              <span>·</span>
              <span>{place.review_count} đánh giá</span>
            </>
          )}
          {place.distance_m && (
            <>
              <span>·</span>
              <span>📍 {formatDistance(place.distance_m)}</span>
            </>
          )}
        </div>

        {/* Dish tags */}
        {place.dishes && place.dishes.length > 0 && (
          <div className="flex gap-1 mt-2 overflow-hidden">
            {place.dishes.slice(0, 2).map((dish, idx) => (
              <span
                key={idx}
                className="text-[10px] px-2 py-0.5 bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full truncate max-w-[120px]"
              >
                {dish}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-100 dark:border-gray-700 px-3 py-2 flex items-center justify-between">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onFavorite();
          }}
          className="p-1 hover:scale-110 transition-transform"
          aria-label={isFavorited ? 'Bỏ yêu thích' : 'Yêu thích'}
        >
          {isFavorited ? (
            <span className="text-red-500 text-lg">❤️</span>
          ) : (
            <span className="text-gray-400 text-lg">🤍</span>
          )}
        </button>

        <button
          onClick={onClick}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
        >
          Xem chi tiết →
        </button>
      </div>
    </div>
  );
}
