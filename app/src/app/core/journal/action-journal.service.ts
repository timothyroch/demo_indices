import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { API_ENDPOINTS } from '../../constants/endpoints';

import { AuthService } from '../auth/auth.service';

export interface UserActionJournalPayload {
  action: string;
  label?: string | null;
  route?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ActionJournalService {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);

  logAction(payload: UserActionJournalPayload): void {
    if (!this.authService.isAuthenticated) return;

    this.http
      .post<void>(`${environment.apiUrl}${API_ENDPOINTS.JOURNAL_ACTIONS}`, payload)
      .subscribe();
  }
}
