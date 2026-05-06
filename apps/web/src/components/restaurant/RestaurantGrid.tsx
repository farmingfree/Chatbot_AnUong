'use client';

import { useState, useMemo } from 'react';
import { PlaceCard } from '@/types/chat';
import { RestaurantCard } from './RestaurantCard';

type SortOption = 'nearest' | 'rating' | 'cheapest';

interface RestaurantGridProps {
  places: PlaceCard[];
  isLoading: boolean;
  favorites?: Set<string>;
  onFavorite?: (placeId: string) => void;
  onPlaceClick?: (place: PlaceCard) => void;
}

export function RestaurantGrid({
  places,
  isLoading,
  favorites = new Set(),
  onFavorite,
  onPlaceClick,
}: RestaurantGridProps) {
  const [sortBy, setSortBy] = useState<SortOption>('nearest');

  const sortOptions: { key: SortOption; label: string }[] = [
    { key: 'nearest', label: 'Gần nhất' },
    { key: 'rating', label: 'Rating cao' },
    { key: 'cheapest', label: 'Giá thấp nhất' },
  ];

  const sortedPlaces = useMemo(() => {
    const sorted = [...places];
    switch (sortBy) {
      case 'nearest':
        return sorted.sort((a, b) => (a.distance_m ?? Infinity) - (b.distance_m ?? Infinity));
      case 'rating':
        return sorted.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
      case 'cheapest':
        return sorted.sort((a, b) => (a.price_level ?? 5) - (b.price_level ?? 5));
      default:
        return sorted;
    }
  }, [places, sortBy]);

  // Skeleton loading
  if (isLoading) {
    return (
      <div className="my-4">
        <div className="h-5 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-3" />
        <div className="flex gap-2 mb-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-7 w-20 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <RestaurantCard key={i} place={null} isFavorited={false} onFavorite={() => {}} onClick={() => {}} />
          ))}
        </div>
      </div>
    );
  }

  if (places.length === 0) return null;

  // Layout logic
  const isSingle = places.length === 1;
  const isSmallGrid = places.length >= 2 && places.length <= 3;
  const isScrollable = places.length >= 4;

  return (
    <div className="my-4">
      {/* Header */}
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
        Tìm được {places.length} quán phù hợp 🎯
      </p>

      {/* Sort pills */}
      <div className="flex gap-2 mb-3 overflow-x-auto">
        {sortOptions.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setSortBy(opt.key)}
            className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-colors ${
              sortBy === opt.key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {opt.label} {sortBy === opt.key && '✓'}
          </button>
        ))}
      </div>

      {/* Cards layout */}
      {isSingle && (
        <div className="max-w-sm">
          <RestaurantCard
            place={sortedPlaces[0]}
            isFavorited={favorites.has(sortedPlaces[0].id)}
            onFavorite={() => onFavorite?.(sortedPlaces[0].id)}
            onClick={() => onPlaceClick?.(sortedPlaces[0])}
          />
        </div>
      )}

      {isSmallGrid && (
        <div className="grid grid-cols-2 gap-3">
          {sortedPlaces.map((place) => (
            <RestaurantCard
              key={place.id}
              place={place}
              isFavorited={favorites.has(place.id)}
              onFavorite={() => onFavorite?.(place.id)}
              onClick={() => onPlaceClick?.(place)}
            />
          ))}
        </div>
      )}

      {isScrollable && (
        <div className="overflow-x-auto -mx-4 px-4">
          <div className="flex gap-3 snap-x snap-mandatory pb-2" style={{ scrollSnapType: 'x mandatory' }}>
            {sortedPlaces.map((place) => (
              <div key={place.id} className="snap-start shrink-0 min-w-[280px]">
                <RestaurantCard
                  place={place}
                  isFavorited={favorites.has(place.id)}
                  onFavorite={() => onFavorite?.(place.id)}
                  onClick={() => onPlaceClick?.(place)}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
