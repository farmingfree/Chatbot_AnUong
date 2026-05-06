import { PlaceCard } from '@/types/chat';

interface RestaurantCardProps {
  place: PlaceCard;
}

export function RestaurantCard({ place }: RestaurantCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow bg-white dark:bg-gray-800">
      {place.image_url && (
        <img
          src={place.image_url}
          alt={place.name}
          className="w-full h-48 object-cover"
        />
      )}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-lg">{place.name}</h3>
          {place.is_open !== undefined && (
            <span
              className={`text-xs px-2 py-1 rounded ${
                place.is_open
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              }`}
            >
              {place.is_open ? 'Đang mở' : 'Đã đóng'}
            </span>
          )}
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{place.address}</p>

        <div className="flex items-center gap-3 text-sm">
          {place.rating && (
            <div className="flex items-center gap-1">
              <span className="text-yellow-500">⭐</span>
              <span>{place.rating.toFixed(1)}</span>
            </div>
          )}

          {place.distance_m !== undefined && (
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <span>📍</span>
              <span>
                {place.distance_m < 1000
                  ? `${Math.round(place.distance_m)}m`
                  : `${(place.distance_m / 1000).toFixed(1)}km`}
              </span>
            </div>
          )}

          {place.price_range && (
            <div className="text-gray-600 dark:text-gray-400">
              <span>{place.price_range}</span>
            </div>
          )}
        </div>

        {place.cuisine_types && place.cuisine_types.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {place.cuisine_types.slice(0, 3).map((cuisine, idx) => (
              <span
                key={idx}
                className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full"
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 my-4">
      {places.map((place) => (
        <RestaurantCard key={place.id} place={place} />
      ))}
    </div>
  );
}
