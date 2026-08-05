import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, of, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AUTH_STORAGE_TOKEN_KEY } from '../constants/auth.constants';
import { API_ENDPOINTS } from '../../constants/dashboard';
import type { PartnerCityId } from '../../constants/partner-city';

export type { PartnerCityId };

export interface UserInfo {
  id: number;
  username: string;
  is_admin: boolean;
  email?: string | null;
  phone?: string | null;
  partner_city?: PartnerCityId | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly authDisabled = (environment as { authDisabled?: boolean }).authDisabled === true;

  private readonly currentUserSignal = signal<UserInfo | null>(null);
  readonly currentUser = this.currentUserSignal.asReadonly();

  get token(): string | null {
    return typeof localStorage !== 'undefined'
      ? localStorage.getItem(AUTH_STORAGE_TOKEN_KEY)
      : null;
  }

  get isAuthenticated(): boolean {
    return this.authDisabled || !!this.token;
  }

  get isAdmin(): boolean {
    if (this.authDisabled) {
      return true;
    }
    return this.currentUserSignal()?.is_admin ?? false;
  }

  login(username: string, password: string): Observable<{ access_token: string }> {
    if (this.authDisabled) {
      const fakeToken = 'dev';
      localStorage.setItem(AUTH_STORAGE_TOKEN_KEY, fakeToken);
      this.loadCurrentUser();
      return of({ access_token: fakeToken });
    }
    return this.http
      .post<{
        access_token: string;
      }>(`${environment.apiUrl}${API_ENDPOINTS.AUTH_LOGIN}`, { username, password })
      .pipe(
        tap((res) => {
          localStorage.setItem(AUTH_STORAGE_TOKEN_KEY, res.access_token);
          this.loadCurrentUser();
        }),
      );
  }

  logout(): void {
    localStorage.removeItem(AUTH_STORAGE_TOKEN_KEY);
    this.currentUserSignal.set(null);
    this.router.navigate(['/login']);
  }

  loadCurrentUser(): void {
    if (!this.token) {
      this.currentUserSignal.set(null);
      return;
    }
    this.http.get<UserInfo>(`${environment.apiUrl}${API_ENDPOINTS.AUTH_ME}`).subscribe({
      next: (user) => this.currentUserSignal.set(user),
      error: () => {
        if (this.authDisabled) {
          this.currentUserSignal.set(null);
        } else {
          this.logout();
        }
      },
    });
  }

  initAuth(): void {
    if (this.authDisabled) {
      this.loadCurrentUser();
      return;
    }
    if (this.token) {
      this.loadCurrentUser();
      return;
    }
    this.currentUserSignal.set(null);
  }
}
