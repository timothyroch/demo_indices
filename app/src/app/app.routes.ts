import { Routes } from '@angular/router';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { LoginComponent } from './features/auth/login/login.component';
import { AdminUsersComponent } from './features/admin/users/users.component';
import { AlertSettingsComponent } from './features/settings/alert-settings.component';
import { JournalReportComponent } from './features/reports/journal-report.component';
import { adminGuard, authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'admin/users', component: AdminUsersComponent, canMatch: [authGuard, adminGuard] },
  { path: 'settings', component: AlertSettingsComponent, canMatch: [authGuard] },
  { path: 'reports', component: JournalReportComponent, canMatch: [authGuard] },
  { path: '', component: DashboardComponent, canMatch: [authGuard] },
  { path: '**', redirectTo: 'login' },
];
