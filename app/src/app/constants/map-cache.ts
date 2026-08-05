export const RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY = {
  FULL_MAP: 'full',
  PENDING_USER: '__pending_user__',
  NO_PARTNER_CITY: 'none',
} as const;

export const WEATHER_PREDICTION_CACHE_COORD_DECIMALS = 1;

export const WEATHER_PREDICTION_CACHE_NO_ZONE_SEGMENT = 'nozone';

export function buildWeatherPredictionCacheKey(lat: number, lng: number, zoneId: string): string {
  const zoneSegment = zoneId.trim() === '' ? WEATHER_PREDICTION_CACHE_NO_ZONE_SEGMENT : zoneId;
  const d = WEATHER_PREDICTION_CACHE_COORD_DECIMALS;
  return `${lat.toFixed(d)}_${lng.toFixed(d)}_${zoneSegment}`;
}
