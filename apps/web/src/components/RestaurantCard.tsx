import { PlaceCard } from '@/types/chat';
import { MapView } from './MapView';

interface RestaurantCardProps {
  place: PlaceCard;
}

export function RestaurantCard({ place }: RestaurantCardProps) {
  return (
    <div className="border border-primary rounded-lg sm:rounded-xl overflow-hidden hover:shadow-lg transition-shadow bg-secondary touch-manipulation">
      {place.image_url && (
        <img
          src={place.image_url}
          alt={place.name}
          className="w-full h-40 sm:h-48 object-cover"
        />
      )}
      <div className="p-3 sm:p-4">
        <div className="flex items-start justify-between mb-2 gap-2">
          <h3 className="font-semibold text-sm sm:text-base lg:text-lg break-words flex-1 text-primary">{place.name}</h3>
          {place.is_open !== undefined && (
            <span
              className={`text-xs px-2 py-0.5 sm:py-1 rounded whitespace-nowrap shrink-0 ${
                place.is_open
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              }`}
            >
              {place.is_open ? 'Mở' : 'Đóng'}
            </span>
          )}
        </div>

        <p className="text-xs sm:text-sm text-secondary mb-2 line-clamp-2 break-words">{place.address}</p>

        <div className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm flex-wrap">
          {place.rating && (
            <div className="flex items-center gap-1">
              <span className="text-yellow-500">⭐</span>
              <span className="text-primary">{place.rating.toFixed(1)}</span>
            </div>
          )}

          {place.distance_m !== undefined && (
            <div className="flex items-center gap-1 text-secondary">
              <span>📍</span>
              <span>
                {place.distance_m < 1000
                  ? `${Math.round(place.distance_m)}m`
                  : `${(place.distance_m / 1000).toFixed(1)}km`}
              </span>
            </div>
          )}

          {place.price_range && (
            <div className="text-secondary">
              <span>{place.price_range}</span>
            </div>
          )}
        </div>

        {place.cuisine_types && place.cuisine_types.length > 0 && (
          <div className="flex flex-wrap gap-1 sm:gap-1.5 mt-2">
            {place.cuisine_types.slice(0, 3).map((cuisine, idx) => (
              <span
                key={idx}
                className="text-xs px-2 py-0.5 sm:py-1 bg-tertiary rounded-full text-primary"
              >
                {cuisine}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function RestaurantGrid({ places }: { places: PlaceCard[] }) {
  return (
    <div className="space-y-4 my-4 px-2 sm:px-0">
      {/* Map Section */}
      <MapView
        places={places}
        userLocation={null}
        radius={1000}
        className="h-64 sm:h-80 lg:h-96 rounded-lg border border-primary"
      />

      {/* Restaurant Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        {places.map((place) => (
          <RestaurantCard key={place.id} place={place} />
        ))}
      </div>
    </div>
  );
}
