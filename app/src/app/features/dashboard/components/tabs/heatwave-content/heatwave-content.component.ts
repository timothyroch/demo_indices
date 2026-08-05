import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, OnDestroy, inject } from '@angular/core';
import { ZoneDataService } from '../../../services/zone-data.service';
import { catchError, EMPTY, Subscription } from 'rxjs';
import {
  HEATWAVE_RISK_LABELS,
  HEATWAVE_RISK_CLASSES,
  HEATWAVE_STRINGS,
  computeHeatwaveMeetsCriteria,
  computeHumidexFromTmaxTmin,
  getHumidexLevel,
  HUMIDEX_DISPLAY_MIN,
  HUMIDEX_SCALE,
} from '../../../../../constants/heatwave';
import { TabStatusGateComponent } from '../ui-shared/tab-status-gate/tab-status-gate.component';
import { InfoBubbleComponent } from '../ui-shared/info-bubble/info-bubble.component';
import {
  ForecastColumn,
  ForecastContentComponent,
  RowRiskLevel,
} from '../ui-shared/forecast-content/forecast-content.component';
import { LoadingStatus, PanelSlot, SECTION_STRINGS } from '../../../../../constants/dashboard';
import { HeatwaveDayDetail, HeatwavePrediction } from '../../../../../interfaces/heatwave.model';
import { RiskBadgeComponent } from '../ui-shared/risk-badge/risk-badge.component';

const SCALE_MIN = 20;
const SCALE_MAX = 50;

@Component({
  selector: 'app-heatwave-content',
  standalone: true,
  imports: [
    CommonModule,
    RiskBadgeComponent,
    TabStatusGateComponent,
    InfoBubbleComponent,
    ForecastContentComponent,
  ],
  templateUrl: './heatwave-content.component.html',
  styleUrl: './heatwave-content.component.scss',
})
export class HeatwaveContentComponent implements OnInit, OnDestroy {
  @Input({ required: true }) panelSlot!: PanelSlot;

  private readonly zoneDataService = inject(ZoneDataService);
  private sub: Subscription | null = null;

  status: LoadingStatus = 'loading';
  heatwave: HeatwavePrediction | null = null;
  errorMessage: string | null = null;

  readonly strings = HEATWAVE_STRINGS;
  readonly sectionTitleStrings = SECTION_STRINGS;
  readonly humidexScale = HUMIDEX_SCALE;
  readonly Infinity = Infinity;

  simulatedDailyDetails: HeatwaveDayDetail[] = [];
  isSimulationOpen = false;
  isRecommendationsCollapsed = false;

  readonly columns: ForecastColumn<HeatwaveDayDetail>[] = [
    {
      label: this.strings.HEADER_DATE,
      display: (day) => day.date,
    },
    {
      label: this.strings.HEADER_MAX,
      display: (day) => `${day.temperature_max}°`,
      simField: 'temperature_max',
    },
    {
      label: this.strings.HEADER_MIN,
      display: (day) => `${day.temperature_min}°`,
      simField: 'temperature_min',
    },
    {
      label: this.strings.HEADER_HUMIDITY,
      display: (day) => `${day.relative_humidity_max}%`,
    },
    {
      label: this.strings.HEADER_HUMIDEX,
      display: (day) =>
        day.prediction_value >= HUMIDEX_DISPLAY_MIN ? `${day.prediction_value}` : 'N/A',
    },
  ];

  ngOnInit(): void {
    this.sub = this.zoneDataService
      .fetchHeatwavePrediction(this.panelSlot)
      .pipe(
        catchError(() => {
          this.status = 'error';
          this.errorMessage = HEATWAVE_STRINGS.ERROR_MESSAGE;
          return EMPTY;
        }),
      )
      .subscribe((response) => {
        this.heatwave = response;
        this.simulatedDailyDetails = response.daily_details.map((d) => ({ ...d }));
        this.status = 'ready';
      });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  readonly rowClassFn = (predictionValue: number): RowRiskLevel => {
    if (predictionValue >= 45) return 'high';
    if (predictionValue >= 30) return 'moderate';
    return 'low';
  };

  get riskLevelClass(): string {
    if (!this.heatwave) return '';
    return HEATWAVE_RISK_CLASSES[this.heatwave.risk_level] ?? '';
  }

  get riskLabel(): string {
    if (!this.heatwave) return '–';
    return HEATWAVE_RISK_LABELS[this.heatwave.risk_level] ?? '–';
  }

  get today(): HeatwaveDayDetail | null {
    return this.weeklyDetails[0] ?? null;
  }

  get todayHumidexLevel() {
    if (!this.today || !this.isHumidexAvailable(this.today.prediction_value)) return null;
    return getHumidexLevel(this.today.prediction_value);
  }

  get scalePosition(): number {
    if (!this.today) return 0;
    if (!this.isHumidexAvailable(this.today.prediction_value)) return 0;
    const clamped = Math.max(SCALE_MIN, Math.min(SCALE_MAX, this.today.prediction_value));
    return ((clamped - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
  }

  get weeklyDetails(): HeatwaveDayDetail[] {
    if (!this.heatwave) return [];
    return this.simulatedDailyDetails.length
      ? this.simulatedDailyDetails
      : this.heatwave.daily_details;
  }

  isHumidexAvailable(humidex: number): boolean {
    return humidex >= HUMIDEX_DISPLAY_MIN;
  }

  getHumidexTooltip = (day: HeatwaveDayDetail) => {
    if (!this.isHumidexAvailable(day.prediction_value)) return 'N/A';
    const level = getHumidexLevel(day.prediction_value);
    return `${level.label} — ${level.description}`;
  };

  openSimulation(): void {
    this.isSimulationOpen = true;
  }

  closeSimulation(): void {
    this.isSimulationOpen = false;
    this.resetSimulationDetails();
  }

  resetSimulationDetails(): void {
    this.simulatedDailyDetails = this.heatwave?.daily_details.map((d) => ({ ...d })) ?? [];
  }

  applySimulation(): void {
    this.simulatedDailyDetails = this.simulatedDailyDetails.map((d) => {
      const prediction_value = computeHumidexFromTmaxTmin(d.temperature_max, d.temperature_min);
      return {
        ...d,
        prediction_value,
        meets_criteria: computeHeatwaveMeetsCriteria(
          d.temperature_max,
          d.temperature_min,
          prediction_value,
        ),
      };
    });
  }

  toggleRecommendations(): void {
    this.isRecommendationsCollapsed = !this.isRecommendationsCollapsed;
  }
}
