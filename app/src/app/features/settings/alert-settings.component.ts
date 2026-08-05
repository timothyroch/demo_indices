import { ChangeDetectorRef, Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AlertsService, type AlertSettings } from '../../core/alerts/alerts.service';
import { AuthService } from '../../core/auth/auth.service';
import { UI_STRINGS } from '../../core/constants/ui-strings';

@Component({
  selector: 'app-alert-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './alert-settings.component.html',
  styleUrls: ['./alert-settings.component.css'],
})
export class AlertSettingsComponent implements OnInit {
  private readonly alerts = inject(AlertsService);
  protected readonly auth = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly s = UI_STRINGS.alertSettings;

  settings: AlertSettings = {
    alert_pluvial_enabled: false,
    alert_fluvial_enabled: false,
    alert_heatwave_enabled: false,
    alert_snow_enabled: false,
    alert_threshold_pluvial_pct: null,
    alert_threshold_fluvial_pct: null,
    alert_threshold_heatwave_humidex: null,
    alert_threshold_snow_pct: null,
    alert_via_sms: true,
    alert_via_email: false,
    alert_frequency_hours: null,
  };

  thresholdPluvial = 50;
  thresholdFluvial = 50;
  thresholdHeatwaveHumidex = 41;
  thresholdSnow = 20;
  frequencyHours = 4;
  message = '';
  messageError = '';
  loading = false;
  saving = false;
  testingSms = false;
  testingEmail = false;

  ngOnInit(): void {
    this.auth.loadCurrentUser();
    this.loadSettings();
  }

  loadSettings(): void {
    this.loading = true;
    this.messageError = '';
    this.alerts.getSettings().subscribe({
      next: (s) => {
        this.settings = s;
        this.thresholdPluvial = s.alert_threshold_pluvial_pct ?? 50;
        this.thresholdFluvial = s.alert_threshold_fluvial_pct ?? 50;
        this.thresholdHeatwaveHumidex = s.alert_threshold_heatwave_humidex ?? 41;
        this.thresholdSnow = s.alert_threshold_snow_pct ?? 20;
        this.frequencyHours = s.alert_frequency_hours ?? 4;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.messageError = this.s.errorLoad;
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  save(): void {
    this.message = '';
    this.messageError = '';
    this.saving = true;
    this.alerts
      .updateSettings({
        alert_pluvial_enabled: this.settings.alert_pluvial_enabled,
        alert_fluvial_enabled: this.settings.alert_fluvial_enabled,
        alert_heatwave_enabled: this.settings.alert_heatwave_enabled,
        alert_snow_enabled: this.settings.alert_snow_enabled,
        alert_threshold_pluvial_pct: this.thresholdPluvial,
        alert_threshold_fluvial_pct: this.thresholdFluvial,
        alert_threshold_heatwave_humidex: this.thresholdHeatwaveHumidex,
        alert_threshold_snow_pct: this.thresholdSnow,
        alert_via_sms: this.settings.alert_via_sms,
        alert_via_email: this.settings.alert_via_email,
        alert_frequency_hours: this.frequencyHours,
      })
      .subscribe({
        next: (res) => {
          this.settings = res;
          this.saving = false;
          this.message = this.s.successSaved;
          this.cdr.detectChanges();
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.messageError = typeof d === 'string' ? d : this.s.errorSave;
          this.saving = false;
          this.cdr.detectChanges();
        },
      });
  }

  sendTestSms(): void {
    this.message = '';
    this.messageError = '';
    if (!this.auth.currentUser()?.phone) {
      this.messageError = this.s.errorNoPhone;
      this.cdr.detectChanges();
      return;
    }
    this.testingSms = true;
    this.alerts.sendTestSms().subscribe({
      next: () => {
        this.testingSms = false;
        this.message = this.s.successTestSms;
        this.cdr.detectChanges();
      },
      error: (err) => {
        const d = err?.error?.detail;
        this.messageError = typeof d === 'string' ? d : this.s.errorTestSms;
        this.testingSms = false;
        this.cdr.detectChanges();
      },
    });
  }

  sendTestEmail(): void {
    this.message = '';
    this.messageError = '';
    if (!this.auth.currentUser()?.email) {
      this.messageError = this.s.errorNoEmail;
      this.cdr.detectChanges();
      return;
    }
    this.testingEmail = true;
    this.alerts.sendTestEmail().subscribe({
      next: () => {
        this.testingEmail = false;
        this.message = this.s.successTestEmail;
        this.cdr.detectChanges();
      },
      error: (err) => {
        const d = err?.error?.detail;
        this.messageError = typeof d === 'string' ? d : this.s.errorTestEmail;
        this.testingEmail = false;
        this.cdr.detectChanges();
      },
    });
  }
}
