export interface HeatwaveDayDetail {
  date: string;
  temperature_max: number;
  temperature_min: number;
  prediction_value: number; // humidex
  relative_humidity_max: number;
  meets_criteria: boolean;
}

export interface HeatwavePrediction {
  risk_detected: boolean;
  risk_level: string;
  message: string;
  heatwave_windows: { start: string; end: string; peak_humidex: number }[];
  daily_details: HeatwaveDayDetail[];
}
