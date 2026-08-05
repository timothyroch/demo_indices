export interface Explainability {
  rank: number;
  label: string;
  value: number;
  unit: string;
  weight_pct: number;
  direction: 'up' | 'down';
  direction_label: string;
  strength_label: string;
}

export interface FluvialForecast extends PluvialForecast {
  water_level: number;
}

export interface FluvialPrediction {
  probability: number;
  raw_probability: number;
  explainability: Explainability[];
  risk_score: number;
  forecast: FluvialForecast[];
}

export interface PluvialForecast {
  date: string;
  temperature_mean: number;
  precipitation: number;
  prediction_value: number;
  raw_prediction_value: number;
}

export interface RainIntensityInfo {
  level: RainIntensityLevel;
  label: string;
  info: string | null;
}

type RainIntensityLevel =
  | 'unknown'
  | 'none'
  | 'light'
  | 'moderate'
  | 'heavy'
  | 'torrential'
  | 'extreme';

export interface PluvialPrediction {
  probability: number;
  raw_probability: number;
  confidence_std: number;
  explainability: Explainability[];
  risk_score: number;
  forecast: PluvialForecast[];
  rain_intensity_info: RainIntensityInfo;
}
