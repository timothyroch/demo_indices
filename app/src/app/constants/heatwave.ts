import { SliderCheckpoint } from '../features/dashboard/components/filters/risk-filter/risk-filter.component';
import { HEATWAVE_RECOMMENDATION_STRINGS } from './heatwave-recommendations';

export interface HumidexLevel {
  min: number;
  max: number;
  bg: string;
  fg: string;
  label: string;
  description: string;
}

const HUMIDEX_BASE_VAPOR_PRESSURE_HPA = 6.11;
const HUMIDEX_EXPONENT_COEFFICIENT = 5417.753;
const HUMIDEX_KELVIN_OFFSET_C = 273.15;
const HUMIDEX_REFERENCE_K = 273.16;
const HUMIDEX_FACTOR = 0.5555;
const HUMIDEX_REFERENCE_PRESSURE_HPA = 10;
const HUMIDEX_ROUND_DECIMALS = 1;

const HEATWAVE_TMAX_THRESHOLD_C = 32;
const HEATWAVE_TMIN_THRESHOLD_C = 20;
const HEATWAVE_HUMIDEX_THRESHOLD = 41;

const HUMIDEX_LIGHT_DISCOMFORT_MIN = 20;
const HUMIDEX_LIGHT_DISCOMFORT_MAX = 29;
const HUMIDEX_SOME_DISCOMFORT_MIN = 30;
const HUMIDEX_SOME_DISCOMFORT_MAX = 39;
const HUMIDEX_HIGH_DISCOMFORT_MIN = 40;
const HUMIDEX_HIGH_DISCOMFORT_MAX = 45;
const HUMIDEX_DANGER_MIN = 46;
export const HUMIDEX_DISPLAY_MIN = 20;

export const HUMIDEX_SCALE: HumidexLevel[] = [
  {
    min: 20,
    max: 29,
    bg: '#4caf50',
    fg: '#ffffff',
    label: "Un peu d'inconfort",
    description: `De ${HUMIDEX_LIGHT_DISCOMFORT_MIN} à ${HUMIDEX_LIGHT_DISCOMFORT_MAX}`,
  },
  {
    min: HUMIDEX_SOME_DISCOMFORT_MIN,
    max: HUMIDEX_SOME_DISCOMFORT_MAX,
    bg: '#ffeb3b',
    fg: '#333333',
    label: 'Un certain inconfort',
    description: `De ${HUMIDEX_SOME_DISCOMFORT_MIN} à ${HUMIDEX_SOME_DISCOMFORT_MAX}`,
  },
  {
    min: HUMIDEX_HIGH_DISCOMFORT_MIN,
    max: HUMIDEX_HIGH_DISCOMFORT_MAX,
    bg: '#ff9800',
    fg: '#ffffff',
    label: "Beaucoup d'inconfort; évitez les efforts",
    description: `De ${HUMIDEX_HIGH_DISCOMFORT_MIN} à ${HUMIDEX_HIGH_DISCOMFORT_MAX}`,
  },
  {
    min: HUMIDEX_DANGER_MIN,
    max: Infinity,
    bg: '#f44336',
    fg: '#ffffff',
    label: 'Danger; risque de coup de chaleur',
    description: 'Plus de 45',
  },
];

export function getHumidexLevel(humidex: number): HumidexLevel {
  return HUMIDEX_SCALE.find((l) => humidex >= l.min && humidex <= l.max) ?? HUMIDEX_SCALE[0];
}

export function computeHumidex(tAirC: number, dewPointC: number): number {
  const tDewK = dewPointC + HUMIDEX_KELVIN_OFFSET_C;
  const vaporPressure =
    HUMIDEX_BASE_VAPOR_PRESSURE_HPA *
    Math.exp(HUMIDEX_EXPONENT_COEFFICIENT * (1 / HUMIDEX_REFERENCE_K - 1 / tDewK));

  const humidex = tAirC + HUMIDEX_FACTOR * (vaporPressure - HUMIDEX_REFERENCE_PRESSURE_HPA);
  const factor = 10 ** HUMIDEX_ROUND_DECIMALS;
  return Math.round(humidex * factor) / factor;
}

export function computeHumidexFromTmaxTmin(tMaxC: number, tMinC: number): number {
  return computeHumidex(tMaxC, tMinC);
}

export function computeHeatwaveMeetsCriteria(
  tMaxC: number,
  tMinC: number,
  humidex: number,
): boolean {
  return (
    (tMaxC >= HEATWAVE_TMAX_THRESHOLD_C && tMinC >= HEATWAVE_TMIN_THRESHOLD_C) ||
    humidex >= HEATWAVE_HUMIDEX_THRESHOLD
  );
}

export const HEATWAVE_RISK_LABELS: Record<string, string> = {
  none: 'Aucun risque',
  little: 'Certain risque',
  moderate: 'Risque modéré',
  high: 'Risque élevé',
};

export const HEATWAVE_RISK_CLASSES: Record<string, string> = {
  none: 'risk-green',
  little: 'risk-yellow',
  moderate: 'risk-orange',
  high: 'risk-red',
};

export const HEATWAVE_STRINGS = {
  TAB_ROW_LABEL: 'Risque de canicule',
  HEADER_DATE: 'Date',
  HEADER_MAX: 'Tmax',
  HEADER_MIN: 'Tmin',
  HEADER_HUMIDITY: 'Humidité',
  HEADER_HUMIDEX: 'Humidex',
  ERROR_MESSAGE: 'Prévision canicule indisponible',
  LOCALE: 'fr-CA',
  TITLE: 'CANICULES',
  HUMIDEX_LEVEL_LABEL: 'Niveau Humidex',
  HUMIDEX_PREFIX: 'Humidex: ',
  METRIC_HUMIDEX: 'Humidex',
  METRIC_TEMP_MAX: 'Température max',
  METRIC_TEMP_MIN: 'Température min',
  METRIC_HUMIDITY: 'Humidité relative',
  LEGEND_PREFIX_ABOVE: 'Plus de',
  LEGEND_PREFIX_RANGE: 'De',
  LEGEND_SEPARATOR: 'à',
  LEGEND_SOURCE: 'Source: Environnement Canada',
  TOOLTIP_HUMIDEX:
    `L'humidex est un outil que nous utilisons pour décrire la sensation de chaleur et d'humidité ressentie par une personne moyenne.\n` +
    `Il combine la température de l'air et l'humidité relative en un seul chiffre qui reflète la température perçue.`,
  TOOLTIP_LEGEND:
    `Comprendre l'indice humidex\n\n` +
    `Nous divisons l'indice humidex en quatre plages de températures distinctes, groupées en fonction de leur niveau d'incidence. ` +
    `Les plages vont du plus bas degré d'inconfort et de risque pour la santé au niveau le plus élevé d'inconfort et de risque.\n\n` +
    `Il faut noter que certaines personnes seront plus affectées par l'humidex que d'autres.\n\n` +
    `L'humidex et votre santé\n\n` +
    `Si l'indice humidex est supérieur à 30, vous devriez limiter ou modifier l'exercice que vous faites en plein air, en fonction :\n` +
    `• de votre âge\n` +
    `• de vos limitations physiques\n` +
    `• du type de vêtements que vous portez\n` +
    `• des autres conditions météorologiques\n\n` +
    `Toute valeur d'humidex supérieure à 40 est extrêmement élevée. Dans ce cas, vous devriez réduire toute activité physique inutile.\n\n` +
    `Les valeurs extrêmement élevées d'humidex sont rares, sauf dans les régions du sud de l'Ontario, du Manitoba et du Québec.`,

  ...HEATWAVE_RECOMMENDATION_STRINGS,

  COLLAPSE_ICON: '▼',
  EXPAND_ICON: '▶',
  COLLAPSE_ARIA: 'Réduire',
  EXPAND_ARIA: 'Développer',

  SOCIAL_INDICATORS_TITLE: 'Indicateurs sociaux de la zone',
  PCT_65_PLUS_LABEL: '% Seniors (65+)',
  REVENU_MEDIAN_LABEL: 'Revenu médian',
  GINI_INDEX_LABEL: 'Indice Gini',
  LOGEMENT_REPAIRS_LABEL: 'Logements à rénover',
  AVERAGE_PREFIX: 'Moy:',
  CURRENCY_UNIT: 'k$',
} as const;

// Filter constants
export const HUMIDEX_MIN = 0;
export const HUMIDEX_MAX = 50;
export const HUMIDEX_RANGE = HUMIDEX_MAX - HUMIDEX_MIN;

/** Convert an absolute humidex value to a 0-100 track % */
export function humidexToTrackPct(value: number): number {
  return ((value - HUMIDEX_MIN) / HUMIDEX_RANGE) * 100;
}

export const HUMIDEX_BREAKPOINTS = {
  comfort: 30, // 0-29  green
  discomfort: 40, // 30-39 yellow
  heavy: 46, // 40-45 orange
  // 46+           red
} as const;

export const HUMIDEX_TRACK_GRADIENT = (() => {
  const p1 = humidexToTrackPct(HUMIDEX_BREAKPOINTS.comfort).toFixed(2);
  const p2 = humidexToTrackPct(HUMIDEX_BREAKPOINTS.discomfort).toFixed(2);
  const p3 = humidexToTrackPct(HUMIDEX_BREAKPOINTS.heavy).toFixed(2);
  return (
    `linear-gradient(to right,` +
    ` #4caf50 0%, #4caf50 ${p1}%,` +
    ` #ffeb3b ${p1}%, #ffeb3b ${p2}%,` +
    ` #ff9800 ${p2}%, #ff9800 ${p3}%,` +
    ` #f44336 ${p3}%, #f44336 100%)`
  );
})();

export const HUMIDEX_CHECKPOINTS: SliderCheckpoint[] = [
  {
    value: 30,
    left: `${humidexToTrackPct(30).toFixed(2)}%`,
    ariaLabel: 'Preset 30 (humidex)',
  },
  {
    value: 40,
    left: `${humidexToTrackPct(40).toFixed(2)}%`,
    ariaLabel: 'Preset 40 (humidex)',
  },
  {
    value: 46,
    left: `${humidexToTrackPct(46).toFixed(2)}%`,
    ariaLabel: 'Preset 46 (humidex)',
  },
];
