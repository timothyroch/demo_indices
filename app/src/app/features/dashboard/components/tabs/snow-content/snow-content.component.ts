import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  OnInit,
  OnDestroy,
  inject,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ZoneDataService } from '../../../services/zone-data.service';
import { catchError, EMPTY, Subscription } from 'rxjs';
import {
  SNOW_RISK_LABELS,
  SNOW_RISK_CLASSES,
  SNOW_RISK_LEVEL,
  SNOW_STRINGS,
  snowPredictionValueToRiskLevel,
  type SnowRiskLevel,
} from '../../../../../constants/snow';
import type { PublicDecisionSeverity } from '../../../../../constants/dashboard';
import {
  SNOW_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY,
  snowRiskLevelToDecisionSeverity,
} from '../../../../../constants/snow-recommendations';
import { RecommendationsComponent } from '../ui-shared/recommendations/recommendations.component';
import { TabStatusGateComponent } from '../ui-shared/tab-status-gate/tab-status-gate.component';
import { InfoBubbleComponent } from '../ui-shared/info-bubble/info-bubble.component';
import { RiskZonesContentComponent } from '../risk-zones-content/risk-zones-content.component';
import {
  ForecastColumn,
  ForecastContentComponent,
} from '../ui-shared/forecast-content/forecast-content.component';
import { SnowDayDetail, SnowPrediction } from '../../../../../interfaces/snow.model';
import { LoadingStatus, PanelSlot, SECTION_STRINGS } from '../../../../../constants/dashboard';
import { partnerCityFromZoneData } from '../../../../../constants/recommendation-sources';
import type { PartnerCityId } from '../../../../../constants/partner-city';
import { probabilityToRiskLevelClass } from '../../../../../constants/recommendations.shared';
import { formatRecoDateLabel } from '../ui-shared/recommendations/calendar-date';
import { RiskBadgeComponent } from '../ui-shared/risk-badge/risk-badge.component';

@Component({
  selector: 'app-snow-content',
  standalone: true,
  imports: [
    CommonModule,
    RiskBadgeComponent,
    TabStatusGateComponent,
    ForecastContentComponent,
    RecommendationsComponent,
    InfoBubbleComponent,
    RiskZonesContentComponent,
  ],
  templateUrl: './snow-content.component.html',
  styleUrl: './snow-content.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SnowContentComponent implements OnInit, OnDestroy {
  @Input({ required: true }) panelSlot!: PanelSlot;

  private readonly zoneDataService = inject(ZoneDataService);
  private readonly cdr = inject(ChangeDetectorRef);
  private sub: Subscription | null = null;
  private zoneSub: Subscription | null = null;

  activePartnerCity: PartnerCityId | null = null;

  status: LoadingStatus = 'loading';
  prediction: SnowPrediction | null = null;
  originalPrediction: SnowPrediction | null = null;
  errorMessage: string | null = null;
  simulatedForecast: SnowDayDetail[] = [];
  isSimulating = false;
  isSimulationOpen = false;

  readonly strings = SNOW_STRINGS;
  readonly sectionTitleStrings = SECTION_STRINGS;
  readonly snowPublicRecoByCity = SNOW_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY;

  recoDayId = '';

  readonly columns: ForecastColumn<SnowDayDetail>[] = [
    { label: SNOW_STRINGS.HEADER_DATE, display: (d) => d.date },
    {
      label: SNOW_STRINGS.HEADER_SNOW,
      display: (d) => `${d.total_snow_cm.toFixed(1)}${SNOW_STRINGS.UNIT_CM}`,
      simField: 'total_snow_cm',
    },
    {
      label: SNOW_STRINGS.HEADER_TEMP,
      display: (d) => `${d.mean_temperature.toFixed(1)}${SNOW_STRINGS.UNIT_DEGREE_C}`,
      simField: 'mean_temperature',
    },
    {
      label: SNOW_STRINGS.HEADER_RISK,
      display: (d) => `${(d.prediction_value * 100).toFixed(2)}%`,
    },
  ];

  ngOnInit(): void {
    this.zoneSub = this.zoneDataService.zoneDataForSlot(this.panelSlot).subscribe((zd) => {
      this.activePartnerCity = partnerCityFromZoneData(zd);
      this.cdr.markForCheck();
    });

    this.sub = this.zoneDataService
      .fetchSnowPrediction(this.panelSlot)
      .pipe(
        catchError(() => {
          this.status = 'error';
          this.isSimulating = false;
          this.errorMessage = SNOW_STRINGS.ERROR_MESSAGE;
          this.cdr.markForCheck();
          return EMPTY;
        }),
      )
      .subscribe((prediction) => {
        this.originalPrediction = prediction;
        this.simulatedForecast = prediction.daily_details?.map((d) => ({ ...d })) ?? [];
        this.prediction = prediction;
        this.recoDayId = prediction.daily_details[0]?.date ?? '';
        this.isSimulating = false;
        this.status = 'ready';
        this.cdr.markForCheck();
      });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.zoneSub?.unsubscribe();
  }

  openSimulation(): void {
    this.isSimulationOpen = true;
  }

  closeSimulation(): void {
    this.isSimulationOpen = false;
    this.resetSimulationDetails();
  }

  applySimulation(): void {
    this.isSimulating = true;
    this.cdr.markForCheck();
    this.sub?.unsubscribe();
    this.sub = this.zoneDataService
      .fetchSnowSimulatedForecast(this.panelSlot, this.simulatedForecast)
      .pipe(
        catchError(() => {
          this.status = 'error';
          this.isSimulating = false;
          this.errorMessage = SNOW_STRINGS.ERROR_MESSAGE;
          this.cdr.markForCheck();
          return EMPTY;
        }),
      )
      .subscribe((simulatedForecast) => {
        this.prediction = {
          ...this.originalPrediction!,
          daily_details: simulatedForecast,
        };
        this.simulatedForecast = this.simulatedForecast.map((day, i) => ({
          ...day,
          prediction_value: simulatedForecast[i]?.prediction_value ?? day.prediction_value,
        }));
        this.isSimulating = false;
        this.cdr.markForCheck();
      });
  }

  resetSimulationDetails(): void {
    this.prediction = this.originalPrediction;
    this.simulatedForecast = this.originalPrediction?.daily_details?.map((d) => ({ ...d })) ?? [];
    this.recoDayId = this.originalPrediction?.daily_details[0]?.date ?? '';
  }

  getProbabilityTooltip = (day: SnowDayDetail): string => {
    const val = this.getRiskExplanationLines(day)
      .map((line) => `${line.label}: ${line.value}`)
      .join('\n');
    return val;
  };

  get todayRiskLevel(): SnowRiskLevel {
    if (this.today) {
      return snowPredictionValueToRiskLevel(this.today.prediction_value);
    }
    return (this.prediction?.risk_level as SnowRiskLevel) ?? SNOW_RISK_LEVEL.NONE;
  }

  get riskLevelClass(): string {
    if (!this.prediction) return '';
    return SNOW_RISK_CLASSES[this.todayRiskLevel] ?? '';
  }

  get riskLabel(): string {
    if (!this.prediction) return '–';
    return SNOW_RISK_LABELS[this.todayRiskLevel] ?? '–';
  }

  onRecoDayChange(id: string): void {
    this.recoDayId = id;
    this.cdr.markForCheck();
  }

  get recoDayOptions(): { id: string; label: string }[] {
    return (
      this.prediction?.daily_details?.map((d) => ({
        id: d.date,
        label: formatRecoDateLabel(d.date),
      })) ?? []
    );
  }

  private get recoDayProbability(): number {
    if (!this.prediction?.daily_details?.length) return -1;
    const day =
      this.prediction.daily_details.find((d) => d.date === this.recoDayId) ??
      this.prediction.daily_details[0];
    return day?.prediction_value ?? -1;
  }

  get recommendationSeverity(): PublicDecisionSeverity {
    const cls = probabilityToRiskLevelClass(this.recoDayProbability);
    return snowRiskLevelToDecisionSeverity(cls);
  }

  get today(): SnowDayDetail | null {
    return this.prediction?.daily_details?.[0] ?? null;
  }

  riskPct(risk: number): number {
    return Math.round(risk * 100);
  }

  contribPct(value: number | undefined): number {
    if (value == null) return 0;
    return Math.round(value * 100);
  }

  getRiskExplanationLines(day: SnowDayDetail): { label: string; value: string }[] {
    const lines: { label: string; value: string }[] = [];
    const b = this.contribPct(day.risk_base);
    const qt = this.contribPct(day.inc_quartile);
    const t = this.contribPct(day.inc_temp);
    const h = this.contribPct(day.inc_humidity);
    const f = this.contribPct(day.inc_forecast);
    const s = this.contribPct(day.small_snow);
    if (b > 0) lines.push({ label: this.strings.EXPLAIN_BASE, value: `+${b} %` });
    if (day.quartile_label && qt > 0)
      lines.push({ label: `${day.total_snow_cm} cm → ${day.quartile_label}`, value: `+${qt} %` });
    else if (day.quartile_label)
      lines.push({ label: `${day.total_snow_cm} cm → ${day.quartile_label}`, value: '+0 %' });
    if (t > 0) lines.push({ label: this.strings.EXPLAIN_TEMP, value: `+${t} %` });
    if (h > 0) lines.push({ label: this.strings.EXPLAIN_HUMIDITY, value: `+${h} %` });
    if (f > 0) lines.push({ label: this.strings.EXPLAIN_FORECAST, value: `+${f} %` });
    if (s > 0) lines.push({ label: this.strings.EXPLAIN_SMALL, value: `+${s} %` });
    lines.push({
      label: this.strings.EXPLAIN_TOTAL,
      value: `${this.riskPct(day.prediction_value)} %`,
    });
    return lines;
  }
}
