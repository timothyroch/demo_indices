import type { RiskKind } from './dashboard';
import {
  GEOJSON_ZONE_PROPERTY_PARTNER_CITY,
  isPartnerCityId,
  type PartnerCityId,
  PARTNER_CITY_ID,
} from './partner-city';

export const PARTNER_CITY_LABELS = {
  [PARTNER_CITY_ID.Montreal]: 'Montréal',
  [PARTNER_CITY_ID.Laval]: 'Laval',
} as const;

export type PartnerCityKey = PartnerCityId;

export function partnerCityFromZoneData(
  zoneData: Record<string, unknown> | null | undefined,
): PartnerCityId | null {
  const v = zoneData?.[GEOJSON_ZONE_PROPERTY_PARTNER_CITY];
  return isPartnerCityId(v) ? v : null;
}

const SOURCE_VILLE_MONTREAL = 'Ville de Montréal';
const SOURCE_VILLE_LAVAL = 'Ville de Laval';

const RECOMMENDATION_SOURCE_LABELS_BY_CITY = {
  [PARTNER_CITY_ID.Montreal]: SOURCE_VILLE_MONTREAL,
  [PARTNER_CITY_ID.Laval]: SOURCE_VILLE_LAVAL,
} as const satisfies Record<PartnerCityId, string>;

export const RECOMMENDATION_SOURCES_BY_CITY: Record<RiskKind, Record<PartnerCityId, string>> = {
  pluvial: RECOMMENDATION_SOURCE_LABELS_BY_CITY,
  crues: RECOMMENDATION_SOURCE_LABELS_BY_CITY,
  canicules: RECOMMENDATION_SOURCE_LABELS_BY_CITY,
  neige: RECOMMENDATION_SOURCE_LABELS_BY_CITY,
};
