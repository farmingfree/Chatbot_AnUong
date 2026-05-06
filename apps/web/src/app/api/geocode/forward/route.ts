import { NextRequest, NextResponse } from 'next/server';

// Simple in-memory cache (1 hour TTL)
const cache = new Map<string, { data: any; expires: number }>();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const address = searchParams.get('address');

  if (!address) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  const cacheKey = address.toLowerCase().trim();
  const cached = cache.get(cacheKey);
  if (cached && cached.expires > Date.now()) {
    return NextResponse.json(cached.data);
  }

  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: 'Google Maps API key not configured' }, { status: 500 });
  }

  try {
    // Append "Ho Chi Minh" to improve results for local addresses
    const query = address.includes('HCM') || address.includes('Hồ Chí Minh')
      ? address
      : `${address}, Hồ Chí Minh, Việt Nam`;

    const res = await fetch(
      `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(query)}&language=vi&key=${apiKey}`
    );
    const json = await res.json();

    if (json.status !== 'OK' || !json.results?.length) {
      return NextResponse.json({ lat: null, lng: null, district: null });
    }

    const result = json.results[0];
    const { lat, lng } = result.geometry.location;

    // Extract district
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

    const data = { lat, lng, district };
    cache.set(cacheKey, { data, expires: Date.now() + CACHE_TTL });

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Geocoding failed' }, { status: 500 });
  }
}
