'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { PlaceCard } from '@/types/chat';

// Fix Leaflet default icon issue in Next.js
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  });
}

const userIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#3b82f6">
      <circle cx="12" cy="12" r="8" stroke="white" stroke-width="2"/>
    </svg>
  `),
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const restaurantIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#ef4444">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" stroke="white" stroke-width="1"/>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

interface MapViewClientProps {
  places: PlaceCard[];
  userLocation: { lat: number; lng: number } | null;
  radius?: number;
  onPlaceClick?: (place: PlaceCard) => void;
  className?: string;
}

function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

export default function MapViewClient({
  places,
  userLocation,
  radius = 1000,
  onPlaceClick,
  className = '',
}: MapViewClientProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const center: [number, number] = userLocation
    ? [userLocation.lat, userLocation.lng]
    : [10.7769, 106.7009]; // HCM center

  return (
    <div className={`relative ${className}`}>
      <MapContainer
        center={center}
        zoom={15}
        scrollWheelZoom={true}
        className="h-full w-full rounded-lg"
        style={{ background: '#e5e7eb' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapUpdater center={center} zoom={15} />

        {userLocation && (
          <>
            <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon}>
              <Popup>
                <strong>Vị trí của bạn</strong>
              </Popup>
            </Marker>
            <Circle
              center={[userLocation.lat, userLocation.lng]}
              radius={radius}
              pathOptions={{
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.1,
                weight: 1,
              }}
            />
          </>
        )}

        {places.map((place) => {
          if (!place.lat || !place.lng) return null;
          return (
            <Marker
              key={place.id}
              position={[place.lat, place.lng]}
              icon={restaurantIcon}
            >
              <Popup>
                <div className="min-w-[160px]">
                  <strong className="block mb-1">{place.name}</strong>
                  {place.rating && (
                    <div className="text-sm">⭐ {place.rating.toFixed(1)}</div>
                  )}
                  {place.distance_m !== undefined && (
                    <div className="text-sm text-gray-600">
                      {place.distance_m < 1000
                        ? `${Math.round(place.distance_m)}m`
                        : `${(place.distance_m / 1000).toFixed(1)}km`}
                    </div>
                  )}
                  {onPlaceClick && (
                    <button
                      onClick={() => onPlaceClick(place)}
                      className="mt-2 text-sm text-blue-600 font-semibold hover:underline"
                    >
                      Xem chi tiết →
                    </button>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
