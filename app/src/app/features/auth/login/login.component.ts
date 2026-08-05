import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/auth/auth.service';
import { LOGIN_STRINGS, SERVER_INVALID_CREDENTIALS_FR } from '../../../constants/ui-strings';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly strings = LOGIN_STRINGS;

  username = '';
  password = '';
  readonly error = signal('');
  readonly loading = signal(false);

  ngOnInit(): void {
    if (this.authService.isAuthenticated) {
      this.router.navigate(['/']);
    }
  }

  onSubmit(): void {
    this.error.set('');
    if (!this.username.trim() || !this.password) {
      this.error.set(this.strings.ERROR_EMPTY);
      return;
    }
    this.loading.set(true);
    this.authService.login(this.username.trim(), this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/']);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        const detail = err?.error?.detail;
        const invalid =
          err?.status === 401 ||
          detail === 'Invalid username or password' ||
          detail === SERVER_INVALID_CREDENTIALS_FR;
        this.error.set(invalid ? this.strings.ERROR_INVALID : this.strings.ERROR_GENERIC);
      },
    });
  }
}
