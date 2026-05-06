export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type?: 'text' | 'places' | 'dishes' | 'place_detail';
  data?: any;
  timestamp: Date;
}

export interface ChatSession {
  id: string;
  title: string;
  preview: string;
  lastMessage: Date;
  messages: Message[];
}

export interface PlaceCard {
  id: string;
  name: string;
  address: string;
  district?: string;
  distance_m?: number;
  rating?: number;
  review_count?: number;
  price_range?: string;
  price_level?: number; // 1-4
  cuisine_types?: string[];
  image_url?: string;
  is_open?: boolean;
  lat?: number;
  lng?: number;
  dishes?: string[];
}

export interface PlaceDetail {
  id: string;
  name: string;
  address: string;
  district?: string;
  distance_m?: number;
  rating?: number;
  review_count?: number;
  price_range?: string;
  price_level?: number;
  cuisine_types?: string[];
  images?: string[];
  image_url?: string;
  is_open?: boolean;
  phone?: string;
  opening_hours?: { [day: string]: string };
  features?: string[];
  menu?: MenuCategory[];
  reviews?: Review[];
  lat?: number;
  lng?: number;
}

export interface MenuCategory {
  category: string;
  items: MenuItem[];
}

export interface MenuItem {
  name: string;
  price?: number;
  description?: string;
}

export interface Review {
  id: string;
  author: string;
  rating: number;
  content: string;
  source?: string;
  date?: string;
}

export interface DishCard {
  id: string;
  name: string;
  description?: string;
  price?: number;
  image_url?: string;
  place_name?: string;
  place_id?: string;
}

export interface UserLocation {
  lat: number;
  lng: number;
}
