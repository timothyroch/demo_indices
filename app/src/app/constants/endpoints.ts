export const API_ENDPOINTS = {
  // Risk Zones
  RISK_ZONES_COMPUTED: '/api/risk-zones/computed',

  // Weather
  WEATHER_DATA: '/api/weather-data',
  PLACE_LABEL: '/api/place-label',

  // Flood Predictions
  FLUVIAL_FLOOD_PREDICT: '/api/fluvial-flood/predict',
  FLUVIAL_FLOOD_SIMULATE_PREDICTION: '/api/fluvial-flood/simulate-predictions',
  PLUVIAL_FLOOD_PREDICT: '/api/pluvial-flood/predict',
  PLUVIAL_FLOOD_SIMULATE_PREDICTION: '/api/pluvial-flood/simulate-predictions',

  // Heatwave
  HEATWAVE_PREDICT: '/api/heatwave/predict',

  // Snow
  SNOW_PREDICT: '/api/snow/predict',
  SNOW_SIMULATE_PREDICTION: '/api/snow/simulate-predictions',

  // Authentication
  AUTH_LOGIN: '/api/auth/login',
  AUTH_ME: '/api/auth/me',
  AUTH_USERS: '/api/auth/users',

  // Alerts
  ALERTS_SETTINGS: '/api/alerts/settings',
  ALERTS_EVALUATE: '/api/alerts/evaluate',
  ALERTS_TEST: '/api/alerts/test',
  ALERTS_TEST_EMAIL: '/api/alerts/test-email',

  // Journal
  JOURNAL_ACTIONS: '/api/journal/actions',
  JOURNAL_REPORT_GENERATE: '/api/journal/reports/generate',
} as const;
