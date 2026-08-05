import { ChangeDetectorRef, Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { JournalReportService } from '../../core/journal/journal-report.service';
import { AuthService } from '../../core/auth/auth.service';
import { UI_STRINGS } from '../../core/constants/ui-strings';

function defaultDateRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to);
  from.setDate(from.getDate() - 7);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { from: iso(from), to: iso(to) };
}

@Component({
  selector: 'app-journal-report',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './journal-report.component.html',
  styleUrls: ['./journal-report.component.css'],
})
export class JournalReportComponent implements OnInit {
  private readonly journalReportService = inject(JournalReportService);
  protected readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly s = UI_STRINGS.journalReport;

  logDateFrom = '';
  logDateTo = '';
  maxEntries = 400;
  includeActionLogs = true;
  includeModelDataSections = true;
  generating = false;
  messageError = '';

  ngOnInit(): void {
    this.authService.loadCurrentUser();
    const { from, to } = defaultDateRange();
    this.logDateFrom = from;
    this.logDateTo = to;
  }

  generate(): void {
    this.messageError = '';

    if (this.logDateFrom && this.logDateTo && this.logDateFrom > this.logDateTo) {
      this.messageError = this.s.errorDates;
      this.cdr.detectChanges();
      return;
    }

    this.generating = true;
    this.journalReportService
      .generateReport({
        log_date_from: this.logDateFrom || null,
        log_date_to: this.logDateTo || null,
        max_entries: this.maxEntries,
      })
      .subscribe({
        next: (r) => {
          this.generating = false;
          this.cdr.detectChanges();

          const labels = {
            sectionMetadata: this.s.sectionMetadata,
            sectionSubjectIdentity: this.s.sectionSubjectIdentity,
            sectionPeriod: this.s.sectionPeriod,
            sectionSummary: this.s.sectionSummary,
            sectionUsageOverview: this.s.sectionUsageOverview,
            sectionHighRisk: this.s.sectionHighRisk,
            sectionActivity: this.s.sectionActivity,
            sectionDetailedEvents: this.s.sectionDetailedEvents,
            sectionRecommendations: this.s.sectionRecommendations,
            sectionModelData: this.s.sectionModelData,
            emptyList: this.s.emptyList,
            emptyEvents: this.s.emptyEvents,
          };
          const fromTo =
            this.logDateFrom && this.logDateTo
              ? `${this.logDateFrom}_${this.logDateTo}`
              : 'periode';
          const pdfVisibility = {
            showActionLogSections: this.includeActionLogs,
            showModelDataSections: this.includeModelDataSections,
          };
          void import('../../core/journal/journal-report-pdf')
            .then(async (m) => {
              try {
                await m.downloadJournalReportPdf(
                  r,
                  labels,
                  `rapport-analyse_${fromTo}`,
                  pdfVisibility,
                );
              } catch {
                this.messageError = this.s.errorPdf;
                this.cdr.detectChanges();
              }
            })
            .catch(() => {
              this.messageError = this.s.errorPdf;
              this.cdr.detectChanges();
            });
        },
        error: (err) => {
          const d = err?.error?.detail;
          this.messageError = typeof d === 'string' ? d : this.s.errorGenerate;
          this.generating = false;
          this.cdr.detectChanges();
        },
      });
  }
}
