import { LoadingStatus } from '../constants/dashboard';

export interface WeatherData {
  temperature?: number;
  precipitation?: number;
  humidity?: number;
  source?: string;
}

export interface WeatherState {
  status: LoadingStatus;
  data: WeatherData | null;
  errorMessage: string | null;
}
