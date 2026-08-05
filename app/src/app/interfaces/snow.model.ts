export interface SnowDayDetail {
  date: string;
  total_snow_cm: number;
  mean_temperature: number;
  prediction_value: number;
  risk_base?: number;
  inc_temp?: number;
  inc_humidity?: number;
  inc_forecast?: number;
  inc_quartile?: number;
  small_snow?: number;
  quartile_label?: string;
}

export interface SnowPrediction {
  risk_detected: boolean;
  risk_level: string;
  message: string;
  daily_details: SnowDayDetail[];
}
