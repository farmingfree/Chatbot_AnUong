'use client';

import dynamic from 'next/dynamic';
import { PlaceCard } from '@/types/chat';

const MapViewClient = dynamic(() => import('./MapViewClient'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center bg-gray-100 dark:bg-gray-800 h-full w-full">
      <div className="text-center">
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-gray-500 dark:text-gray-400">Đang tải bản đồ...</p>
      </div>
    </div>
  ),
});

interface MapViewProps {
  places: PlaceCard[];
  userLocation: { lat: number; lng: number } | null;
  radius?: number;
  onPlaceClick?: (place: PlaceCard) => void;
  className?: string;
}

export function MapView(props: MapViewProps) {
  return <MapViewClient {...props} />;
}
