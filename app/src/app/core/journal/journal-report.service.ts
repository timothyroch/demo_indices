import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../constants/dashboard';

export interface JournalReportGenerateRequest {
  log_date_from: string | null;
  log_date_to: string | null;
  max_entries: number;
}

export interface JournalReportMetadata {
  period_covered: string;
  generated_at: string;
  generated_by: string;
}

export interface JournalReportUserIdentity {
  identifier_line: string;
  role_and_permissions: string;
  account_status: string;
}

export interface DetailedJournalEvent {
  timestamp: string;
  event_type: string;
  module_or_component: string;
  action_details: string;
  operation_status: string;
}

export interface JournalStructuredReport {
  metadata: JournalReportMetadata;
  subject_identity: JournalReportUserIdentity;
  title: string;
  summary: string;
  period_description: string;
  high_risk_events: string[];
  user_activity_notes: string[];
  recommendations: string[];
  usage_overview_bullets: string[];
  detailed_events: DetailedJournalEvent[];
  optional_model_data_notes: string[];
}

@Injectable({ providedIn: 'root' })
export class JournalReportService {
  private readonly http = inject(HttpClient);

  generateReport(body: JournalReportGenerateRequest): Observable<JournalStructuredReport> {
    return this.http.post<JournalStructuredReport>(
      `${environment.apiUrl}${API_ENDPOINTS.JOURNAL_REPORT_GENERATE}`,
      body,
    );
  }
}
