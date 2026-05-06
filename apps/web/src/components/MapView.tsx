'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { GoogleMap, Marker, Circle, InfoWindow, useJsApiLoader } from '@react-google-maps/api';
import { MarkerClusterer } from '@googlemaps/markerclusterer';
import { PlaceCard } from '@/types/chat';

const MAP_CONTAINER_STYLE = { width: '100%', height: '100%' };

const MAP_OPTIONS: google.maps.MapOptions = {
  disableDefaultUI: true,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
  styles: [
    { featureType: 'poi', stylers: [{ visibility: 'off' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  ],
};

const USER_MARKER_ICON = {
  path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z',
  fillColor: '#4285F4',
  fillOpacity: 1,
  strokeColor: '#ffffff',
  strokeWeight: 2,
  scale: 1.5,
  anchor: { x: 12, y: 24 } as unknown as google.maps.Point,
};

const PLACE_MARKER_ICON = {
  path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z',
  fillColor: '#EA4335',
  fillOpacity: 1,
  strokeColor: '#ffffff',
  strokeWeight: 2,
  scale: 1.2,
  anchor: { x: 12, y: 24 } as unknown as google.maps.Point,
};

interface MapViewProps {
  places: PlaceCard[];
  userLocation: { lat: number; lng: number } | null;
  radius?: number;
  onPlaceClick?: (place: PlaceCard) => void;
  className?: string;
}

export function MapView({
  places,
  userLocation,
  radius = 1000,
  onPlaceClick,
  className = '',
}: MapViewProps) {
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || '',
  });

  const [selectedPlace, setSelectedPlace] = useState<PlaceCard | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const clustererRef = useRef<MarkerClusterer | null>(null);

  const center = useMemo(() => {
    if (userLocation) return userLocation;
    // Default: HCM center
    return { lat: 10.7769, lng: 106.7009 };
  }, [userLocation]);

  const onLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
  }, []);

  const onUnmount = useCallback(() => {
    if (clustererRef.current) {
      clustererRef.current.clearMarkers();
      clustererRef.current = null;
    }
    mapRef.current = null;
  }, []);

  if (!isLoaded) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 dark:bg-gray-800 ${className}`}>
        <div className="text-center">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-gray-500">Đang tải bản đồ...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <GoogleMap
        mapContainerStyle={MAP_CONTAINER_STYLE}
        center={center}
        zoom={15}
        options={MAP_OPTIONS}
        onLoad={onLoad}
        onUnmount={onUnmount}
      >
        {/* User location marker */}
        {userLocation && (
          <>
            <Marker position={userLocation} icon={USER_MARKER_ICON} zIndex={100} />
            <Circle
              center={userLocation}
              radius={radius}
              options={{
                strokeColor: '#4285F4',
                strokeOpacity: 0.3,
                strokeWeight: 1,
                fillColor: '#4285F4',
                fillOpacity: 0.08,
              }}
            />
          </>
        )}

        {/* Place markers */}
        {places.map((place) => {
          if (!place.lat || !place.lng) return null;
          return (
            <Marker
              key={place.id}
              position={{ lat: place.lat, lng: place.lng }}
              icon={PLACE_MARKER_ICON}
              title={place.name}
              onClick={() => setSelectedPlace(place)}
            />
          );
        })}

        {/* Info window */}
        {selectedPlace && selectedPlace.lat && selectedPlace.lng && (
          <InfoWindow
            position={{ lat: selectedPlace.lat, lng: selectedPlace.lng }}
            onCloseClick={() => setSelectedPlace(null)}
          >
            <div className="p-1 max-w-[200px]">
              <h4 className="font-semibold text-sm truncate">{selectedPlace.name}</h4>
              <div className="flex items-center gap-1 mt-1 text-xs text-gray-600">
                {selectedPlace.rating && <span>⭐ {selectedPlace.rating.toFixed(1)}</span>}
                {selectedPlace.distance_m && (
                  <span>· {selectedPlace.distance_m < 1000 ? `${Math.round(selectedPlace.distance_m)}m` : `${(selectedPlace.distance_m / 1000).toFixed(1)}km`}</span>
                )}
              </div>
              <button
                onClick={() => {
                  onPlaceClick?.(selectedPlace);
                  setSelectedPlace(null);
                }}
                className="mt-2 text-xs text-blue-600 font-medium hover:underline"
              >
                Xem chi tiết →
              </button>
            </div>
          </InfoWindow>
        )}
      </GoogleMap>
    </div>
  );
}
