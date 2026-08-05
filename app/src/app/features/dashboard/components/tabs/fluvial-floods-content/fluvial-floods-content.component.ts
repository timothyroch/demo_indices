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
import { CommonModule } from '@angular/common';
import { FloodTodayContentComponent } from '../ui-shared/floods-today-content/floods-today-content.component';
import {
  LoadingStatus,
  PanelSlot,
  PublicDecisionSeverity,
  RISK_LABELS,
  RISK_ZONE_CONFIGS,
  SECTION_STRINGS,
} from '../../../../../constants/dashboard';
import { ExplainabilityContentComponent } from '../ui-shared/explainability-content/explainability-content.component';
import { RiskZonesContentComponent } from '../risk-zones-content/risk-zones-content.component';
import { TabStatusGateComponent } from '../ui-shared/tab-status-gate/tab-status-gate.component';
import {
  ForecastColumn,
  ForecastContentComponent,
} from '../ui-shared/forecast-content/forecast-content.component';
import { FLOOD_STRINGS } from '../../../../../constants/floods';
import { FluvialForecast, FluvialPrediction } from '../../../../../interfaces/flood.model';
import {
  FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS,
  FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY,
  fluvialRiskLevelToDecisionSeverity,
} from '../../../../../constants/fluvial-recommendations';
import {
  probabilityToRiskLevelClass,
  RECO_DAY_ID_TODAY,
} from '../../../../../constants/recommendations.shared';
import { formatRecoDateLabel } from '../ui-shared/recommendations/calendar-date';
import { RecommendationsComponent } from '../ui-shared/recommendations/recommendations.component';
import { partnerCityFromZoneData } from '../../../../../constants/recommendation-sources';
import type { PartnerCityId } from '../../../../../constants/partner-city';

@Component({
  selector: 'app-fluvial-floods-content',
  standalone: true,
  imports: [
    CommonModule,
    FloodTodayContentComponent,
    ExplainabilityContentComponent,
    TabStatusGateComponent,
    ForecastContentComponent,
    RecommendationsComponent,
    RiskZonesContentComponent,
  ],
  templateUrl: './fluvial-floods-content.component.html',
  styleUrl: './fluvial-floods-content.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FluvialFloodsContentComponent implements OnInit, OnDestroy {
  @Input({ required: true }) panelSlot!: PanelSlot;

  readonly zoneDataService = inject(ZoneDataService);
  private readonly cdr = inject(ChangeDetectorRef);
  private sub: Subscription | null = null;
  private zoneSub: Subscription | null = null;

  readonly riskZoneConfig = RISK_ZONE_CONFIGS.crues;

  activePartnerCity: PartnerCityId | null = null;

  status: LoadingStatus = 'loading';
  prediction: FluvialPrediction | null = null;
  originalPrediction: FluvialPrediction | null = null;
  errorMessage: string | null = null;
  simulatedForecast: FluvialForecast[] = [];
  isSimulating = false;
  isSimulationOpen = false;

  readonly floodStrings = FLOOD_STRINGS;
  readonly fluvialPublicRecoContent = FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS;
  readonly sectionStrings = SECTION_STRINGS;
  readonly fluvialPublicRecoByCity = FLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY;

  recoDayId: string = RECO_DAY_ID_TODAY;

  readonly columns: ForecastColumn<FluvialForecast>[] = [
    { label: FLOOD_STRINGS.DATE_HEADER, display: (d) => d.date },
    {
      label: FLOOD_STRINGS.WATER_LEVEL_HEADER,
      display: (d) => (d.water_level != null ? `${d.water_level.toFixed(1)} m` : '-'),
      simField: 'water_level',
    },
    {
      label: FLOOD_STRINGS.TEMP_HEADER,
      display: (d) => (d.temperature_mean != null ? `${d.temperature_mean.toFixed(1)}°` : '-'),
      simField: 'temperature_mean',
    },
    {
      label: FLOOD_STRINGS.PREC_HEADER,
      display: (d) => (d.precipitation != null ? `${d.precipitation.toFixed(1)} mm` : '-'),
      simField: 'precipitation',
    },
    {
      label: FLOOD_STRINGS.FLUVIAL_PROB_HEADER,
      display: (d) =>
        d.prediction_value != null ? `${(d.prediction_value * 100).toFixed(2)}%` : '-',
    },
  ];

  ngOnInit(): void {
    this.zoneSub = this.zoneDataService.zoneDataForSlot(this.panelSlot).subscribe((zoneData) => {
      this.activePartnerCity = partnerCityFromZoneData(zoneData);
      this.cdr.markForCheck();
    });

    this.sub = this.zoneDataService
      .fetchFluvialFloodPrediction(this.panelSlot)
      .pipe(
        catchError(() => {
          this.status = 'error';
          this.isSimulating = false;
          this.errorMessage = FLOOD_STRINGS.ERROR_MESSAGE;
          this.cdr.markForCheck();
          return EMPTY;
        }),
      )
      .subscribe((prediction) => {
        console.log('Flood Prediction Received:', prediction);

        this.originalPrediction = prediction;
        this.simulatedForecast = prediction.forecast?.map((d) => ({ ...d })) ?? [];
        this.prediction = prediction;
        this.recoDayId = RECO_DAY_ID_TODAY;
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
      .fetchFluvialSimulatedForecast(this.panelSlot, this.simulatedForecast)
      .pipe(
        catchError(() => {
          this.status = 'error';
          this.isSimulating = false;
          this.errorMessage = FLOOD_STRINGS.ERROR_MESSAGE;
          this.cdr.markForCheck();
          return EMPTY;
        }),
      )
      .subscribe((simulatedForecast) => {
        this.prediction = {
          ...this.originalPrediction!,
          forecast: simulatedForecast,
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
    this.simulatedForecast = this.originalPrediction?.forecast?.map((d) => ({ ...d })) ?? [];
    this.recoDayId = RECO_DAY_ID_TODAY;
  }

  onRecoDayChange(id: string): void {
    this.recoDayId = id;
    this.cdr.markForCheck();
  }

  get recoDayOptions(): { id: string; label: string }[] {
    const opts: { id: string; label: string }[] = [
      { id: RECO_DAY_ID_TODAY, label: this.sectionStrings.RECO_DAY_OPTION_TODAY },
    ];
    for (const d of this.prediction?.forecast ?? []) {
      opts.push({ id: d.date, label: formatRecoDateLabel(d.date) });
    }
    return opts;
  }

  private get recoDayProbability(): number {
    if (!this.prediction) return -1;
    if (this.recoDayId === RECO_DAY_ID_TODAY) {
      return this.prediction.probability;
    }
    const day = this.prediction.forecast?.find((d) => d.date === this.recoDayId);
    return day?.prediction_value ?? this.prediction.probability;
  }

  get floodProbabilityLabel(): string | null {
    return this.prediction != null ? `${(this.prediction.probability * 100)?.toFixed(2)} %` : null;
  }

  get riskLevelClass(): string {
    if (!this.prediction) return '';
    return probabilityToRiskLevelClass(this.prediction.probability);
  }

  get riskLevelLabel(): string {
    return RISK_LABELS[this.riskLevelClass] ?? '–';
  }

  get riskScore(): string {
    return this.prediction?.risk_score != null
      ? this.formatPercent(this.prediction.risk_score, false)
      : '–';
  }

  get recommendationSeverity(): PublicDecisionSeverity {
    const cls = probabilityToRiskLevelClass(this.recoDayProbability);
    return fluvialRiskLevelToDecisionSeverity(cls);
  }

  get infobubbleProbabilityText(): string {
    const rawProb = this.prediction ? this.formatPercent(this.prediction.raw_probability) : '–';
    return (
      'Probabilité brute du modèle: ' +
      rawProb +
      ' ' +
      this.floodStrings.INFOBUBBLE_FLUVIAL_PROBABILITY
    );
  }

  get infobubbleRiskText(): string {
    return this.activePartnerCity == 'montreal'
      ? this.floodStrings.INFOBUBBLE_RISK_FLUV_MTL
      : this.floodStrings.INFOBUBBLE_RISK_SOCIAL;
  }

  formatPercent(value: number, shouldMultiply = true): string {
    return `${(shouldMultiply ? value * 100 : value).toFixed(2)}%`;
  }
}
