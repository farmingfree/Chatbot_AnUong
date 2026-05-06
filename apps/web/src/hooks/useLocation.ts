'use client';

import { useState, useEffect, useCallback } from 'react';

export type LocationStatus = 'idle' | 'loading' | 'granted' | 'denied' | 'manual';

export interface LocationState {
  lat: number | null;
  lng: number | null;
  address: string | null;
  district: string | null;
  status: LocationStatus;
}

const STORAGE_KEY = 'food_advisor_location';

const DEFAULT_STATE: LocationState = {
  lat: null,
  lng: null,
  address: null,
  district: null,
  status: 'idle',
};

export function useLocation() {
  const [location, setLocation] = useState<LocationState>(() => {
    if (typeof window === 'undefined') return DEFAULT_STATE;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : DEFAULT_STATE;
    } catch {
      return DEFAULT_STATE;
    }
  });

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocation((prev) => ({ ...prev, status: 'denied' }));
      return;
    }

    setLocation((prev) => ({ ...prev, status: 'loading' }));

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        try {
          const res = await fetch(`/api/geocode/reverse?lat=${lat}&lng=${lng}`);
          const { district, address } = await res.json();
          const newLoc: LocationState = { lat, lng, address, district, status: 'granted' };
          setLocation(newLoc);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newLoc));
        } catch {
          // Still save coordinates even if geocode fails
          const newLoc: LocationState = { lat, lng, address: null, district: null, status: 'granted' };
          setLocation(newLoc);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newLoc));
        }
      },
      () => {
        setLocation((prev) => ({ ...prev, status: 'denied' }));
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const setManualLocation = useCallback(async (addressInput: string) => {
    try {
      const res = await fetch(`/api/geocode/forward?address=${encodeURIComponent(addressInput)}`);
      const { lat, lng, district } = await res.json();
      const newLoc: LocationState = { lat, lng, address: addressInput, district, status: 'manual' };
      setLocation(newLoc);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newLoc));
    } catch {
      // If geocode fails, just save the address text
      const newLoc: LocationState = { lat: null, lng: null, address: addressInput, district: null, status: 'manual' };
      setLocation(newLoc);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newLoc));
    }
  }, []);

  const clearLocation = useCallback(() => {
    setLocation(DEFAULT_STATE);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { location, requestLocation, setManualLocation, clearLocation };
}
