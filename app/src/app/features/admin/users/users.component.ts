import { ChangeDetectorRef, Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { timeout } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AuthService, type UserInfo } from '../../../core/auth/auth.service';
import { PARTNER_CITY_ID, type PartnerCityId } from '../../../constants/partner-city';
import { ADMIN_USERS_STRINGS } from '../../../constants/ui-strings';
import { API_ENDPOINTS } from '../../../constants/dashboard';

const CREATE_USER_TIMEOUT_MS = 20_000;

interface UserActionLog {
  id: number;
  timestamp: string;
  log_date: string;
  user_id: number;
  username: string;
  action: string;
  label?: string | null;
  route?: string | null;
  payload_json?: string | null;
}

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './users.component.html',
  styleUrls: ['./users.component.css'],
})
export class AdminUsersComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly authService = inject(AuthService);

  readonly strings = ADMIN_USERS_STRINGS;

  readonly partnerCityId = PARTNER_CITY_ID;

  users: UserInfo[] = [];
  newUsername = '';
  newPassword = '';
  newEmail = '';
  newPhone = '';
  newPartnerCity: PartnerCityId = PARTNER_CITY_ID.Montreal;
  message = '';
  messageError = '';
  loading = false;
  loadingList = false;

  editingPasswordForId: number | null = null;
  newPasswordForUser = '';
  savingPassword = false;

  editingContactForId: number | null = null;
  editEmail = '';
  editPhone = '';
  savingContact = false;

  editingPartnerCityForId: number | null = null;
  editPartnerCity: PartnerCityId = PARTNER_CITY_ID.Montreal;
  savingPartnerCity = false;
  deletingId: number | null = null;
  viewingLogsForId: number | null = null;
  loadingLogs = false;
  logsError = '';
  logsLimit = 50;
  logsDate = '';
  userLogs: UserActionLog[] = [];

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loadingList = true;
    this.messageError = '';
    this.cdr.detectChanges();
    this.http.get<UserInfo[]>(`${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}`).subscribe({
      next: (list) => {
        this.users = list;
        this.loadingList = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.messageError = this.strings.ERROR_LOAD_LIST;
        this.loadingList = false;
        this.cdr.detectChanges();
      },
    });
  }

  private getErrorMessage(err: { error?: { detail?: string | unknown } }): string {
    const d = err?.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0];
      const msg =
        typeof first === 'object' && first && 'msg' in first
          ? String((first as { msg: string }).msg)
          : null;
      return msg ?? this.strings.ERROR_INVALID_DATA;
    }
    return this.strings.ERROR_CREATE_GENERIC;
  }

  createUser(): void {
    this.message = '';
    this.messageError = '';
    if (!this.newUsername.trim()) {
      this.messageError = this.strings.ERROR_USERNAME_REQUIRED;
      return;
    }
    if (!this.newPassword || this.newPassword.length < 8) {
      this.messageError = this.strings.ERROR_PASSWORD_MIN;
      return;
    }
    const email = this.newEmail.trim();
    if (!email) {
      this.messageError = this.strings.ERROR_EMAIL_REQUIRED;
      return;
    }
    if (!this.validateEmail(email)) {
      this.messageError = this.strings.ERROR_EMAIL_INVALID;
      return;
    }
    const phone = this.newPhone.trim();
    if (!phone) {
      this.messageError = this.strings.ERROR_PHONE_REQUIRED;
      return;
    }
    if (!this.validatePhone(phone)) {
      this.messageError = this.strings.ERROR_PHONE_INVALID;
      return;
    }
    this.loading = true;
    const username = this.newUsername.trim();

    this.http
      .post<UserInfo>(`${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}`, {
        username,
        password: this.newPassword,
        email,
        phone,
        partner_city: this.newPartnerCity,
      })
      .pipe(timeout(CREATE_USER_TIMEOUT_MS))
      .subscribe({
        next: (created) => {
          this.loading = false;
          this.newUsername = '';
          this.newPassword = '';
          this.newEmail = '';
          this.newPhone = '';
          this.newPartnerCity = PARTNER_CITY_ID.Montreal;
          this.users = [...this.users, created].sort((a, b) =>
            a.username.localeCompare(b.username),
          );
          this.message = this.strings.SUCCESS_CREATED;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.loading = false;
          this.messageError =
            err?.name === 'TimeoutError' ? this.strings.ERROR_TIMEOUT : this.getErrorMessage(err);
          this.cdr.detectChanges();
        },
      });
  }

  startEditPassword(user: UserInfo): void {
    this.editingPasswordForId = user.id;
    this.editingContactForId = null;
    this.editingPartnerCityForId = null;
    this.newPasswordForUser = '';
    this.messageError = '';
    this.cdr.detectChanges();
  }

  cancelEditPassword(): void {
    this.editingPasswordForId = null;
    this.newPasswordForUser = '';
    this.cdr.detectChanges();
  }

  startEditContact(user: UserInfo): void {
    this.editingContactForId = user.id;
    this.editingPasswordForId = null;
    this.editingPartnerCityForId = null;
    this.editEmail = user.email ?? '';
    this.editPhone = user.phone ?? '';
    this.messageError = '';
    this.cdr.detectChanges();
  }

  cancelEditContact(): void {
    this.editingContactForId = null;
    this.editEmail = '';
    this.editPhone = '';
    this.cdr.detectChanges();
  }

  startEditPartnerCity(user: UserInfo): void {
    if (user.is_admin) return;
    this.editingPartnerCityForId = user.id;
    this.editingPasswordForId = null;
    this.editingContactForId = null;
    this.editPartnerCity = (user.partner_city as PartnerCityId) ?? PARTNER_CITY_ID.Montreal;
    this.messageError = '';
    this.cdr.detectChanges();
  }

  cancelEditPartnerCity(): void {
    this.editingPartnerCityForId = null;
    this.cdr.detectChanges();
  }

  savePartnerCity(): void {
    if (this.editingPartnerCityForId == null) return;
    this.savingPartnerCity = true;
    this.messageError = '';
    this.http
      .patch<UserInfo>(
        `${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}/${this.editingPartnerCityForId}/partner-city`,
        { partner_city: this.editPartnerCity },
      )
      .subscribe({
        next: (updated) => {
          this.savingPartnerCity = false;
          this.editingPartnerCityForId = null;
          this.users = this.users.map((u) => (u.id === updated.id ? updated : u));
          this.message = this.strings.SUCCESS_PARTNER_CITY_UPDATED;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.savingPartnerCity = false;
          this.messageError = this.getErrorMessage(err);
          this.cdr.detectChanges();
        },
      });
  }

  partnerCityLabel(c: string | null | undefined): string {
    if (!c) return '—';
    return c === PARTNER_CITY_ID.Montreal
      ? this.strings.PARTNER_CITY_MONTREAL
      : this.strings.PARTNER_CITY_LAVAL;
  }

  private validateEmail(email: string): boolean {
    const s = email.trim();
    return (
      s.length > 0 && !s.includes(' ') && /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(s)
    );
  }

  private validatePhone(phone: string): boolean {
    const digits = phone.replace(/\D/g, '');
    return digits.length >= 10 && digits.length <= 15;
  }

  saveContact(): void {
    if (this.editingContactForId == null) return;
    const email = this.editEmail.trim();
    const phone = this.editPhone.trim();
    if (!email) {
      this.messageError = this.strings.ERROR_EMAIL_REQUIRED;
      this.cdr.detectChanges();
      return;
    }
    if (!this.validateEmail(email)) {
      this.messageError = this.strings.ERROR_EMAIL_INVALID;
      this.cdr.detectChanges();
      return;
    }
    if (!phone) {
      this.messageError = this.strings.ERROR_PHONE_REQUIRED;
      this.cdr.detectChanges();
      return;
    }
    if (!this.validatePhone(phone)) {
      this.messageError = this.strings.ERROR_PHONE_INVALID_SHORT;
      this.cdr.detectChanges();
      return;
    }
    this.savingContact = true;
    this.messageError = '';
    this.http
      .patch<UserInfo>(
        `${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}/${this.editingContactForId}/contact`,
        { email, phone },
      )
      .subscribe({
        next: (updated) => {
          this.savingContact = false;
          this.editingContactForId = null;
          this.users = this.users.map((u) => (u.id === updated.id ? updated : u));
          this.message = this.strings.SUCCESS_CONTACT_UPDATED;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.savingContact = false;
          this.messageError = this.getErrorMessage(err);
          this.cdr.detectChanges();
        },
      });
  }

  saveNewPassword(): void {
    if (this.editingPasswordForId == null || this.newPasswordForUser.length < 8) {
      this.messageError = this.strings.ERROR_PASSWORD_MIN;
      this.cdr.detectChanges();
      return;
    }
    this.savingPassword = true;
    this.messageError = '';
    this.http
      .patch<UserInfo>(
        `${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}/${this.editingPasswordForId}`,
        {
          password: this.newPasswordForUser,
        },
      )
      .subscribe({
        next: () => {
          this.savingPassword = false;
          this.editingPasswordForId = null;
          this.newPasswordForUser = '';
          this.message = this.strings.SUCCESS_PASSWORD_UPDATED;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.savingPassword = false;
          this.messageError = this.getErrorMessage(err);
          this.cdr.detectChanges();
        },
      });
  }

  deleteUser(user: UserInfo): void {
    if (!confirm(this.strings.CONFIRM_DELETE.replace('{username}', user.username))) {
      return;
    }
    this.deletingId = user.id;
    this.messageError = '';
    this.http.delete(`${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}/${user.id}`).subscribe({
      next: () => {
        this.deletingId = null;
        this.users = this.users.filter((u) => u.id !== user.id);
        const currentUser = this.authService.currentUser();
        if (currentUser && currentUser.id === user.id) {
          this.authService.logout();
        } else {
          this.message = this.strings.SUCCESS_DELETED;
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        this.deletingId = null;
        this.messageError = this.getErrorMessage(err);
        this.cdr.detectChanges();
      },
    });
  }

  toggleLogs(user: UserInfo): void {
    if (this.viewingLogsForId === user.id) {
      this.viewingLogsForId = null;
      this.userLogs = [];
      this.logsError = '';
      this.loadingLogs = false;
      this.cdr.detectChanges();
      return;
    }
    this.viewingLogsForId = user.id;
    this.loadUserLogs();
  }

  loadUserLogs(): void {
    if (this.viewingLogsForId == null) return;
    this.loadingLogs = true;
    this.logsError = '';

    const params: Record<string, string> = {
      limit: String(this.logsLimit),
    };
    if (this.logsDate.trim()) {
      params['date'] = this.logsDate.trim();
    }

    this.http
      .get<
        UserActionLog[]
      >(`${environment.apiUrl}${API_ENDPOINTS.AUTH_USERS}/${this.viewingLogsForId}/logs`, { params })
      .subscribe({
        next: (logs) => {
          this.userLogs = logs;
          this.loadingLogs = false;
          this.cdr.detectChanges();
        },
        error: () => {
          this.loadingLogs = false;
          this.userLogs = [];
          this.logsError = this.strings.LOGS_ERROR;
          this.cdr.detectChanges();
        },
      });
  }

  formatLogTimestamp(value: string): string {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString('fr-CA');
  }

  formatLogPayload(payload: string | null | undefined): string {
    if (!payload) return '—';
    return payload.length <= 250 ? payload : `${payload.slice(0, 250)}…`;
  }
}
