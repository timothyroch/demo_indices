import { SliderCheckpoint } from '../features/dashboard/components/filters/risk-filter/risk-filter.component';
import { RiskZoneConfig } from '../interfaces/coordinates.model';
import { WeatherState } from '../interfaces/weather.model';
// ============================================================================
// RISK TYPES & CONFIGURATION
// ============================================================================

export type RiskKind = 'pluvial' | 'crues' | 'canicules' | 'neige';
export type RiskBand = 'vert' | 'jaune' | 'orange' | 'rouge';
export type PanelSlot = 'primary' | 'secondary';
export type LoadingStatus = 'idle' | 'loading' | 'ready' | 'error';

export const INITIAL_WEATHER: WeatherState = {
  status: 'idle',
  data: null,
  errorMessage: null,
};

export const PUBLIC_DECISION_SEVERITY = {
  None: 'none',
  Normale: 'normale',
  Extreme: 'extreme',
} as const;

export type PublicDecisionSeverity =
  (typeof PUBLIC_DECISION_SEVERITY)[keyof typeof PUBLIC_DECISION_SEVERITY];

export const RISK_KINDS: Record<RiskKind, string> = {
  pluvial: 'Inondations pluviales',
  crues: 'Crues fluviales',
  canicules: 'Canicules',
  neige: 'Chutes de neige',
} as const;

export const SOCIAL_RISK_KINDS: RiskKind[] = ['canicules', 'crues', 'neige'];

export const AIRE_DE_DIFFUSION_RISK_KINDS: RiskKind[] = ['pluvial', 'crues', 'canicules', 'neige'];

export const RISK_BANDS: RiskBand[] = ['vert', 'jaune', 'orange', 'rouge'];

export const RISK_BAND_CLASS = {
  GREEN: 'risk-green',
  YELLOW: 'risk-yellow',
  ORANGE: 'risk-orange',
  RED: 'risk-red',
} as const;

export const RISK_LABELS: Record<string, string> = {
  [RISK_BAND_CLASS.GREEN]: 'Risque faible',
  [RISK_BAND_CLASS.YELLOW]: 'Certain risque',
  [RISK_BAND_CLASS.ORANGE]: 'Risque modéré',
  [RISK_BAND_CLASS.RED]: 'Risque élevé',
};

export const LOADING_LABEL = 'Chargement prévisions…';

export const SIDE_PANEL_STRINGS = {
  PLACE_TITLE_PENDING: '…',
  SECONDARY_PANEL_TITLE: 'Zone à comparer',
  CLOSE_ARIA: 'Fermer',
  CLOSE_ICON: '✕',
  ADD_PANEL_ARIA: 'Ouvrir une deuxième zone pour comparaison',
  ADD_PANEL_TOOLTIP: 'Ouvrir un second panneau pour comparaison',
  SECONDARY_HINT: 'Cliquez sur une zone de la carte pour l’afficher ici.',
  LOADING: 'Chargement météo…',
  WEATHER_SECTION_TITLE: 'Conditions météo',
  WEATHER_TEMPERATURE: 'Température',
  WEATHER_HUMIDITY: 'Humidité',
  WEATHER_PRECIPITATION: 'Précipitation (24 h)',
} as const;

export const RISK_TABS_STRINGS = {
  PLUVIAL: 'Inondations pluviales',
  FLUVIAL: 'Crues fluviales',
  HEATWAVES: 'Canicules',
  SNOW: 'Chutes de neige',
} as const;

export const SECTION_STRINGS = {
  TODAY_TITLE: "Aujourd'hui",
  EXPLAINABILITY_TITLE: 'Facteurs influençant la probabilité',
  RECO_TITLE: 'Recommandations',
  RECO_DAY_OPTION_TODAY: "Aujourd'hui",
  FORECAST_TITLE: 'Prévisions 7 jours',
  LEGEND_TITLE: 'Légende',
};

export const TAB_SECTION_STRINGS = {
  ERROR_MESSAGE: 'Prévision indisponible',
  PROBABILITY_LABEL: "Probabilité d'occurence",
  VULNERABILITY_LABEL: 'Indice de vulnérabilité de la zone',
  RAIN_INTENSITY_LABEL: 'Intensité de la pluie',
} as const;

export const FILTER_STRINGS = {
  MAP_NAME: 'Cartographie - Aires de diffusion',
  FILTER_ARIA_LABEL: 'Filtre par probabilité combinée',
  RISK_TITLE: 'Risque (Probabilité)',
  LOW: 'Faible (0–20 %)',
  MODERATE: 'Modéré (20–50 %)',
  HIGH: 'Élevé (50 %+)',
  THRESHOLD_TITLE: 'Seuil minimal',
  MIN_BOUND: '0 %',
  MAX_BOUND: '100 %',
  PREFIX_RISK: 'Risque :',
  PREFIX_HUMIDEX: 'Humidex :',
  // Collapse/Expand buttons
  COLLAPSE_ICON: '▲',
  EXPAND_ICON: '▼',
  COLLAPSE_ARIA: 'Collapse',
  EXPAND_ARIA: 'Expand',
  // Social Filters
  SOCIAL_FILTERS_TITLE: 'Filtres sociaux',
  PCT_65_PLUS_LABEL: '% Seniors (65+)',
  REVENU_MEDIAN_LABEL: 'Revenu médian',
  GINI_INDEX_LABEL: 'Indice Gini',
  LOGEMENT_LABEL: 'Logements à rénover',
  CURRENCY_UNIT: '$',
  PERCENT_UNIT: '%',
  PLACEHOLDER_MIN: 'Min',
  PLACEHOLDER_MAX: 'Max',
  RANGE_SEPARATOR: '-',
} as const;

export const PERCENT_TRACK_GRADIENT =
  'linear-gradient(to right, #22c55e 0%, #22c55e 20%, #f59e0b 20%, #f59e0b 50%, #ef4444 50%, #ef4444 100%)';

export const PERCENT_CHECKPOINTS: SliderCheckpoint[] = [
  { value: 20, left: '20%', ariaLabel: 'Preset 20 %' },
  { value: 50, left: '50%', ariaLabel: 'Preset 50 %' },
];

export const MAP_STRINGS = {
  LOADING: 'Chargement des zones à risques…',
  ZOOM_OUT: 'Zoom out',
  ZOOM_IN: 'Zoom in',
  ZOOM_MINUS: '−',
  ZOOM_PLUS: '+',
  ZOOM_ARIA: 'Zoom',
} as const;

export const MAP_ZONE_VIEWPORT_FRACTIONS = {
  SELECTED_ZONE_SCREEN_X: 0.25,
  SELECTED_ZONE_SCREEN_Y: 0.5,
} as const;

export const FOOTER_STRINGS = {
  COPYRIGHT_ORG: 'IRIU',
} as const;

export const WEATHER_STRINGS = {
  ERROR_MESSAGE: 'Données météo indisponibles',
} as const;

export const DEFAULT_WEATHER_LOADING_STATE = {
  status: 'loading' as const,
  data: null,
  errorMessage: null,
};

export const DEFAULT_WEATHER_ERROR_STATE = {
  status: 'error' as const,
  data: null,
  errorMessage: WEATHER_STRINGS.ERROR_MESSAGE,
};

// ============================================================================
// SOCIAL FILTERS & ISLAND STATISTICS
// ============================================================================

export const SOCIAL_FILTER_DEFAULTS = {
  pct_65_plus: { min: 0, max: 100 },
  revenu_median_menage: { min: 0, max: 500000 },
  gini: { min: 0, max: 1 },
  logement_reparations_majeures: { min: 0, max: 100 },
};

export const MONTREAL_ISLAND_AVERAGES = {
  pct_65_plus: 17.06,
  revenu_median_menage: 75809,
  gini: 0.3233,
  logement_reparations_majeures: 23.78,
} as const;

export const LAVAL_AVERAGES = {
  pct_65_plus: 18.5,
  revenu_median_menage: 91645,
  gini: 0.2692,
  logement_reparations_majeures: 13.15,
} as const;

export function getCityAverages(city: string | null) {
  if (city === 'laval') {
    return LAVAL_AVERAGES;
  }
  return MONTREAL_ISLAND_AVERAGES;
}

// ============================================================================
// RISK ZONE CONFIGURATIONS
// ============================================================================

export const RISK_ZONE_CONFIGS: Record<RiskKind, RiskZoneConfig> = {
  pluvial: {
    title: 'Zones de risque - Inondations pluviales',
    description: "Visualisation des zones à risque d'inondations pluviales",
    helpText:
      'Les zones colorées affichent les quartiers exposés aux inondations pluviales. ' +
      'Utilisez les filtres pour affiner votre sélection.',
  },
  crues: {
    title: 'Zones de risque - Crues fluviales',
    description: 'Zones à risque de crues',
    helpText:
      'Ces zones représentent les quartiers exposés aux risques de crues fluviales. ' +
      'Consultez les indicateurs sociaux pour comprendre la vulnérabilité de la population.',
  },

  canicules: {
    title: 'Zones de risque - Canicules',
    description: 'Visualisation des zones exposées aux canicules',
    helpText:
      'Les zones colorées indiquent les quartiers les plus vulnérables aux vagues de chaleur extrêmes. ' +
      'Consultez les filtres pour affiner votre sélection.',
  },
  neige: {
    title: 'Zones sociales vulnérables',
    description: 'Quartiers socialement vulnérables',
    helpText:
      'Ces zones représentent les quartiers avec les vulnérabilités sociales les plus importantes. ' +
      "Consultez les données pour plus d'informations sur les indicateurs utilisés.",
  },
} as const;

// ============================================================================
// MAP STYLING & COLORS
// ============================================================================

export const MAP_COLORS = {
  BASE_FILL_COLOR: [
    'match',
    ['get', 'display_band'],
    'vert',
    '#22c55e',
    'jaune',
    '#eab308',
    'orange',
    '#f97316',
    'rouge',
    '#e53935',
    '#a9a9a9',
  ],
  BASE_LINE_COLOR: [
    'match',
    ['get', 'display_band'],
    'vert',
    '#16a34a',
    'jaune',
    '#ca8a04',
    'orange',
    '#c2410c',
    'rouge',
    '#c62828',
    '#a9a9a9',
  ],
  SELECTED_FILL_COLOR: '#3a6ded',
  SELECTED_LINE_COLOR: '#2169b6',
  SELECTED_OPACITY: 0.65,
  DEFAULT_OPACITY: 0.4,
  SELECTED_LINE_WIDTH: 3.5,
  DEFAULT_LINE_WIDTH: 1.5,
} as const;

// API paths : voir `constants/endpoints.ts`
export { API_ENDPOINTS } from './endpoints';
export {
  RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY,
  WEATHER_PREDICTION_CACHE_COORD_DECIMALS,
  WEATHER_PREDICTION_CACHE_NO_ZONE_SEGMENT,
  buildWeatherPredictionCacheKey,
} from './map-cache';
