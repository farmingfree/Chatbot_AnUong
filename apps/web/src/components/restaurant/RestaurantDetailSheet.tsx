'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PlaceDetail } from '@/types/chat';

type Tab = 'menu' | 'reviews' | 'details';

const DAYS_VI: Record<string, string> = {
  monday: 'Thứ 2',
  tuesday: 'Thứ 3',
  wednesday: 'Thứ 4',
  thursday: 'Thứ 5',
  friday: 'Thứ 6',
  saturday: 'Thứ 7',
  sunday: 'Chủ nhật',
};

function getTodayKey(): string {
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return days[new Date().getDay()];
}

function formatPrice(price?: number): string {
  if (!price) return '';
  return price.toLocaleString('vi-VN') + '₫';
}

interface RestaurantDetailSheetProps {
  place: PlaceDetail | null;
  isOpen: boolean;
  onClose: () => void;
  isFavorited?: boolean;
  onFavorite?: () => void;
}

export function RestaurantDetailSheet({
  place,
  isOpen,
  onClose,
  isFavorited = false,
  onFavorite,
}: RestaurantDetailSheetProps) {
  const [activeTab, setActiveTab] = useState<Tab>('menu');
  const [imageIndex, setImageIndex] = useState(0);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'menu', label: 'Menu' },
    { key: 'reviews', label: 'Đánh giá' },
    { key: 'details', label: 'Chi tiết' },
  ];

  const todayKey = getTodayKey();

  const googleMapsUrl = place
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ' ' + place.address)}`
    : '#';

  const images = place?.images?.length ? place.images : place?.image_url ? [place.image_url] : [];

  const handleCopyAddress = () => {
    if (place?.address) {
      navigator.clipboard.writeText(place.address);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && place && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-40"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-50 max-h-[90vh] bg-white dark:bg-gray-900 rounded-t-2xl overflow-hidden flex flex-col"
          >
            {/* Handle bar */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full" />
            </div>

            <div className="overflow-y-auto flex-1">
              {/* Hero image */}
              <div className="relative h-48">
                {images.length > 0 ? (
                  <>
                    <img
                      src={images[imageIndex]}
                      alt={place.name}
                      className="w-full h-full object-cover"
                    />
                    {images.length > 1 && (
                      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                        {images.map((_, i) => (
                          <button
                            key={i}
                            onClick={() => setImageIndex(i)}
                            className={`w-2 h-2 rounded-full ${i === imageIndex ? 'bg-white' : 'bg-white/50'}`}
                          />
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center">
                    <span className="text-6xl">🍜</span>
                  </div>
                )}
              </div>

              {/* Info section */}
              <div className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-lg font-bold">{place.name}</h2>
                  {place.is_open !== undefined && (
                    <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${place.is_open ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {place.is_open ? 'Đang mở' : 'Đóng cửa'}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  {place.rating && <span>⭐ {place.rating.toFixed(1)}</span>}
                  {place.price_range && <span>· {place.price_range}</span>}
                  {place.distance_m && (
                    <span>· 📍 {place.distance_m < 1000 ? `${Math.round(place.distance_m)}m` : `${(place.distance_m / 1000).toFixed(1)}km`}</span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <p className="text-sm text-gray-500 dark:text-gray-400 flex-1">{place.address}</p>
                  <button onClick={handleCopyAddress} className="text-xs text-blue-600 shrink-0 hover:underline">
                    📋 Copy
                  </button>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-gray-200 dark:border-gray-700 px-4">
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`flex-1 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.key
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-4 pb-24">
                {/* Menu tab */}
                {activeTab === 'menu' && (
                  <div className="space-y-4">
                    {place.menu && place.menu.length > 0 ? (
                      place.menu.map((cat, ci) => (
                        <div key={ci}>
                          <h4 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-2">{cat.category}</h4>
                          <div className="space-y-1.5">
                            {cat.items.map((item, ii) => (
                              <div key={ii} className="flex justify-between items-center py-1">
                                <span className="text-sm">{item.name}</span>
                                {item.price && <span className="text-sm font-medium text-orange-600">{formatPrice(item.price)}</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-400 text-center py-6">Chưa có thông tin menu</p>
                    )}
                  </div>
                )}

                {/* Reviews tab */}
                {activeTab === 'reviews' && (
                  <div className="space-y-3">
                    {place.reviews && place.reviews.length > 0 ? (
                      place.reviews.slice(0, 5).map((review) => (
                        <div key={review.id} className="border border-gray-100 dark:border-gray-700 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <div className="w-7 h-7 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center text-xs font-bold text-blue-600">
                              {review.author.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm font-medium">{review.author}</span>
                            <span className="text-xs text-yellow-500">{'⭐'.repeat(Math.min(review.rating, 5))}</span>
                            {review.source && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-500 ml-auto">
                                {review.source}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{review.content}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-400 text-center py-6">Chưa có đánh giá</p>
                    )}
                  </div>
                )}

                {/* Details tab */}
                {activeTab === 'details' && (
                  <div className="space-y-4">
                    {/* Opening hours */}
                    {place.opening_hours && Object.keys(place.opening_hours).length > 0 && (
                      <div>
                        <h4 className="font-semibold text-sm mb-2">🕐 Giờ mở cửa</h4>
                        <div className="space-y-1">
                          {Object.entries(place.opening_hours).map(([day, hours]) => (
                            <div
                              key={day}
                              className={`flex justify-between text-sm py-1 px-2 rounded ${
                                day === todayKey ? 'bg-blue-50 dark:bg-blue-900/30 font-medium' : ''
                              }`}
                            >
                              <span>{DAYS_VI[day] || day}</span>
                              <span className="text-gray-600 dark:text-gray-400">{hours}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Phone */}
                    {place.phone && (
                      <div>
                        <h4 className="font-semibold text-sm mb-1">📞 Số điện thoại</h4>
                        <a href={`tel:${place.phone}`} className="text-sm text-blue-600 hover:underline">
                          {place.phone}
                        </a>
                      </div>
                    )}

                    {/* Features */}
                    {place.features && place.features.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-sm mb-2">✨ Tiện ích</h4>
                        <div className="flex flex-wrap gap-2">
                          {place.features.map((f, i) => (
                            <span key={i} className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full">
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Sticky footer */}
            <div className="sticky bottom-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 flex gap-3">
              <button
                onClick={onFavorite}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium border transition-colors ${
                  isFavorited
                    ? 'bg-red-50 border-red-200 text-red-600 dark:bg-red-900/30 dark:border-red-800'
                    : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                {isFavorited ? '❤️ Đã lưu' : '🤍 Lưu quán'}
              </button>
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-blue-600 text-white text-center hover:bg-blue-700 transition-colors"
              >
                🧭 Chỉ đường
              </a>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
