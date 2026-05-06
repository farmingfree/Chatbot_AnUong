import { DishCard as DishCardType } from '@/types/chat';

interface DishCardProps {
  dish: DishCardType;
}

export function DishCard({ dish }: DishCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow bg-white dark:bg-gray-800">
      {dish.image_url && (
        <img
          src={dish.image_url}
          alt={dish.name}
          className="w-full h-40 object-cover"
        />
      )}
      <div className="p-3">
        <h3 className="font-semibold text-base mb-1">{dish.name}</h3>
        
        {dish.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">
            {dish.description}
          </p>
        )}

        <div className="flex items-center justify-between">
          {dish.price && (
            <span className="text-sm font-medium text-green-600 dark:text-green-400">
              {dish.price.toLocaleString('vi-VN')}đ
            </span>
          )}
          
          {dish.place_name && (
            <span className="text-xs text-gray-500 dark:text-gray-400 truncate ml-2">
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
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 my-4">
      {dishes.map((dish) => (
        <DishCard key={dish.id} dish={dish} />
      ))}
    </div>
  );
}
