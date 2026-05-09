import { DishCard as DishCardType } from '@/types/chat';

interface DishCardProps {
  dish: DishCardType;
}

export function DishCard({ dish }: DishCardProps) {
  return (
    <div className="border rounded-lg sm:rounded-xl overflow-hidden hover:shadow-lg transition-shadow bg-white dark:bg-gray-800 touch-manipulation">
      {dish.image_url && (
        <img
          src={dish.image_url}
          alt={dish.name}
          className="w-full h-32 sm:h-40 object-cover"
        />
      )}
      <div className="p-2.5 sm:p-3">
        <h3 className="font-semibold text-sm sm:text-base mb-1 line-clamp-1 break-words">{dish.name}</h3>

        {dish.description && (
          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-2 break-words">
            {dish.description}
          </p>
        )}

        <div className="flex items-center justify-between gap-2">
          {dish.price && (
            <span className="text-xs sm:text-sm font-medium text-green-600 dark:text-green-400 whitespace-nowrap">
              {dish.price.toLocaleString('vi-VN')}đ
            </span>
          )}

          {dish.place_name && (
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
              {dish.place_name}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function DishGrid({ dishes }: { dishes: DishCardType[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 sm:gap-3 my-3 sm:my-4 px-2 sm:px-0">
      {dishes.map((dish) => (
        <DishCard key={dish.id} dish={dish} />
      ))}
    </div>
  );
}
