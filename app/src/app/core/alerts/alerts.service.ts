import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../constants/dashboard';

export interface AlertSettings {
  alert_pluvial_enabled: boolean;
  alert_fluvial_enabled: boolean;
  alert_heatwave_enabled: boolean;
  alert_snow_enabled: boolean;
  alert_threshold_pluvial_pct: number | null;
  alert_threshold_fluvial_pct: number | null;
  alert_threshold_heatwave_humidex: number | null;
  alert_threshold_snow_pct: number | null;
  alert_via_sms: boolean;
  alert_via_email: boolean;
  alert_frequency_hours: number | null;
}

@Injectable({ providedIn: 'root' })
export class AlertsService {
  private readonly http = inject(HttpClient);

  getSettings(): Observable<AlertSettings> {
    return this.http.get<AlertSettings>(`${environment.apiUrl}${API_ENDPOINTS.ALERTS_SETTINGS}`);
  }

  updateSettings(partial: Partial<AlertSettings>): Observable<AlertSettings> {
    return this.http.patch<AlertSettings>(
      `${environment.apiUrl}${API_ENDPOINTS.ALERTS_SETTINGS}`,
      partial,
    );
  }

  sendTestSms(): Observable<{ sent: boolean }> {
    return this.http.post<{ sent: boolean }>(
      `${environment.apiUrl}${API_ENDPOINTS.ALERTS_TEST}`,
      {},
    );
  }

  sendTestEmail(): Observable<{ sent: boolean }> {
    return this.http.post<{ sent: boolean }>(
      `${environment.apiUrl}${API_ENDPOINTS.ALERTS_TEST_EMAIL}`,
      {},
    );
  }

  evaluateRiskAlerts(): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(
      `${environment.apiUrl}${API_ENDPOINTS.ALERTS_EVALUATE}`,
      {},
    );
  }
}
