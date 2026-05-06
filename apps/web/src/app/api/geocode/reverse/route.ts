import { NextRequest, NextResponse } from 'next/server';

// Simple in-memory cache (1 hour TTL)
const cache = new Map<string, { data: any; expires: number }>();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour

function getCacheKey(lat: number, lng: number): string {
  return `${lat.toFixed(4)},${lng.toFixed(4)}`;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const lat = searchParams.get('lat');
  const lng = searchParams.get('lng');

  if (!lat || !lng) {
    return NextResponse.json({ error: 'lat and lng are required' }, { status: 400 });
  }

  const cacheKey = getCacheKey(parseFloat(lat), parseFloat(lng));
  const cached = cache.get(cacheKey);
  if (cached && cached.expires > Date.now()) {
    return NextResponse.json(cached.data);
  }

  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: 'Google Maps API key not configured' }, { status: 500 });
  }

  try {
    const res = await fetch(
      `https://maps.googleapis.com/maps/api/geocode/json?latlng=${lat},${lng}&language=vi&key=${apiKey}`
    );
    const json = await res.json();

    if (json.status !== 'OK' || !json.results?.length) {
      return NextResponse.json({ district: null, address: null });
    }

    const result = json.results[0];
    const address = result.formatted_address || null;

    // Extract district from address components
    let district: string | null = null;
    for (const component of result.address_components || []) {
      if (
        component.types.includes('administrative_area_level_2') ||
        component.types.includes('sublocality_level_1') ||
        component.types.includes('locality')
      ) {
        district = component.long_name;
        break;
      }
    }

    const data = { district, address };
    cache.set(cacheKey, { data, expires: Date.now() + CACHE_TTL });

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Geocoding failed' }, { status: 500 });
  }
}
