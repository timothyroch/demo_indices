export const SNOW_RISK_LEVEL = {
  NONE: 'none',
  MODERATE: 'moderate',
  HIGH: 'high',
} as const;

export type SnowRiskLevel = (typeof SNOW_RISK_LEVEL)[keyof typeof SNOW_RISK_LEVEL];

export function snowPredictionValueToRiskLevel(value: number | undefined | null): SnowRiskLevel {
  if (value == null || Number.isNaN(value)) {
    return SNOW_RISK_LEVEL.NONE;
  }
  if (value >= 0.5) {
    return SNOW_RISK_LEVEL.HIGH;
  }
  if (value >= 0.2) {
    return SNOW_RISK_LEVEL.MODERATE;
  }
  return SNOW_RISK_LEVEL.NONE;
}

export const SNOW_RISK_LABELS: Record<SnowRiskLevel, string> = {
  [SNOW_RISK_LEVEL.NONE]: 'Risque faible',
  [SNOW_RISK_LEVEL.MODERATE]: 'Risque modéré',
  [SNOW_RISK_LEVEL.HIGH]: 'Risque élevé',
};

export const SNOW_RISK_CLASSES: Record<SnowRiskLevel, string> = {
  [SNOW_RISK_LEVEL.NONE]: 'risk-green',
  [SNOW_RISK_LEVEL.MODERATE]: 'risk-orange',
  [SNOW_RISK_LEVEL.HIGH]: 'risk-red',
};

export const SNOW_STRINGS = {
  TAB_ROW_LABEL: 'Risque de chute de neige',
  SNOW_FORECAST_SUBTITLE: 'Risque de chute de neige prévue selon les données météo',
  HEADER_DATE: 'Date',
  HEADER_SNOW: 'Neige (cm)',
  HEADER_TEMP: 'Temp. moy. (°C)',
  HEADER_RISK: 'Risque (%)',
  ERROR_MESSAGE: 'Prévision neige indisponible',
  LOCALE: 'fr-CA',
  TITLE: 'CHUTES DE NEIGE',
  RISK_LABEL: 'Probabilité de risque (règles de décision)',
  TOOLTIP_RISK_PERCENT:
    'Pourcentage entre 0 et 100 obtenu par des règles sur les prévisions de neige (Open-Meteo). ' +
    'Pour chaque jour hors été (juin à septembre), on additionne (plafonné à 100 %) : un risque de base selon la neige du jour et les cumuls sur 2 ou 3 jours ; ' +
    'si des seuils sont atteints, des compléments : température entre −10 et 0 °C, humidité, neige prévue le lendemain, quartile d’accumulation ; ' +
    'sinon un petit risque proportionnel à la neige. Si la neige prévue pour le jour est 0 cm, le risque est 0 %. ' +
    'Le bloc « Détail du risque » détaille chaque contribution.',
  METRIC_SNOW: 'Neige prévue',
  METRIC_TEMP: 'Température moyenne',

  EXPLAIN_TITLE: 'Détail du risque',
  EXPLAIN_BASE: 'Risque de base (seuils 10/15/20/25 cm ou accum. 2–3 j)',
  EXPLAIN_QUARTILE: 'Quartile d’accumulation',
  EXPLAIN_TEMP: 'Température 0 à -10 °C',
  EXPLAIN_HUMIDITY: 'Humidité',
  EXPLAIN_FORECAST: 'Neige prévue (prochaines 24 h)',
  EXPLAIN_SMALL: 'Petit risque (2 %/cm, max 10 %)',
  EXPLAIN_TOTAL: 'Total',
  EXPAND_DETAIL: 'Détail',
  EXPAND_ARIA: 'Afficher le détail du risque pour ce jour',
  CHEVRON: '▼',

  UNIT_CM: ' cm',
  UNIT_DEGREE: ' °',
  UNIT_DEGREE_C: ' °C',
  UNIT_PERCENT: ' %',
} as const;
