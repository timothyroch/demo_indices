export const PARTNER_CITY_ID = {
  Montreal: 'montreal',
  Laval: 'laval',
} as const;

export type PartnerCityId = (typeof PARTNER_CITY_ID)[keyof typeof PARTNER_CITY_ID];

export const GEOJSON_ZONE_PROPERTY_PARTNER_CITY = 'partner_city' as const;

export function isPartnerCityId(value: unknown): value is PartnerCityId {
  return value === PARTNER_CITY_ID.Montreal || value === PARTNER_CITY_ID.Laval;
}
