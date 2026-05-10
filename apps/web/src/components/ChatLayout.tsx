'use client';

import { ReactNode, useState, useEffect } from 'react';
import { ThemeToggle } from './ThemeToggle';
import { MapModal } from './MapModal';
import { ConversationSidebar } from './ConversationSidebar';
import { PlaceCard } from '@/types/chat';

interface ChatLayoutProps {
  children: ReactNode;
  onNewChat?: () => void;
  sessionTitle?: string;
  places?: PlaceCard[];
}

export function ChatLayout({ children, onNewChat, sessionTitle, places = [] }: ChatLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => {
          console.error('Error getting location:', error);
        }
      );
    }
  }, []);

  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [sidebarOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-primary">
      {/* Use ConversationSidebar component */}
      <ConversationSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
          aria-label="Đóng menu"
        />
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-secondary border-b border-primary p-3 sm:p-4 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-1.5 sm:p-2 hover-bg-tertiary rounded-lg transition-colors touch-manipulation shrink-0 text-secondary"
                aria-label="Mở menu"
              >
                <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h2 className="font-semibold text-base sm:text-lg truncate text-primary">
                {sessionTitle || 'Chat mới'}
              </h2>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setMapOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors text-sm font-medium"
                aria-label="Mở bản đồ"
              >
                <span>🗺️</span>
                <span className="hidden sm:inline">Bản đồ</span>
              </button>
              <ThemeToggle />
              <div className="hidden sm:flex items-center gap-1 text-xs sm:text-sm text-secondary">
                <span>📍</span>
                <span className="hidden md:inline">TP. Hồ Chí Minh</span>
                <span className="md:hidden">HCM</span>
              </div>
            </div>
          </div>
        </header>

        {/* Messages Area */}
        {children}
      </main>

      {/* Map Modal */}
      <MapModal
        isOpen={mapOpen}
        onClose={() => setMapOpen(false)}
        places={places}
        userLocation={userLocation}
      />
    </div>
  );
}
