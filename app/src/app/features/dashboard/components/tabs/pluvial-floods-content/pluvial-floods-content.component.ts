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
import { PluvialForecast, PluvialPrediction } from '../../../../../interfaces/flood.model';
import { RecommendationsComponent } from '../ui-shared/recommendations/recommendations.component';
import {
  PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS,
  PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY,
  pluvialRiskLevelToDecisionSeverity,
} from '../../../../../constants/pluvial-recommendations';
import { partnerCityFromZoneData } from '../../../../../constants/recommendation-sources';
import type { PartnerCityId } from '../../../../../constants/partner-city';
import {
  probabilityToRiskLevelClass,
  RECO_DAY_ID_TODAY,
} from '../../../../../constants/recommendations.shared';
import { formatRecoDateLabel } from '../ui-shared/recommendations/calendar-date';

@Component({
  selector: 'app-pluvial-floods-content',
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
  templateUrl: './pluvial-floods-content.component.html',
  styleUrl: './pluvial-floods-content.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PluvialFloodsContentComponent implements OnInit, OnDestroy {
  @Input({ required: true }) panelSlot!: PanelSlot;

  readonly zoneDataService = inject(ZoneDataService);
  private readonly cdr = inject(ChangeDetectorRef);
  private sub: Subscription | null = null;
  private zoneSub: Subscription | null = null;

  readonly riskZoneConfig = RISK_ZONE_CONFIGS.pluvial;

  activePartnerCity: PartnerCityId | null = null;

  status: LoadingStatus = 'loading';
  prediction: PluvialPrediction | null = null;
  originalPrediction: PluvialPrediction | null = null;
  errorMessage: string | null = null;
  simulatedForecast: PluvialForecast[] = [];
  isSimulating = false;
  isSimulationOpen = false;

  readonly floodStrings = FLOOD_STRINGS;
  readonly sectionStrings = SECTION_STRINGS;

  readonly pluvialPublicRecoContent = PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS;
  readonly pluvialPublicRecoByCity = PLUVIAL_PUBLIC_DECISION_RECOMMENDATIONS_BY_CITY;

  recoDayId: string = RECO_DAY_ID_TODAY;

  readonly columns: ForecastColumn<PluvialForecast>[] = [
    { label: FLOOD_STRINGS.DATE_HEADER, display: (d) => d.date },
    {
      label: FLOOD_STRINGS.TEMP_HEADER,
      display: (d) => `${d.temperature_mean.toFixed(1)}°`,
      simField: 'temperature_mean',
    },
    {
      label: FLOOD_STRINGS.PREC_HEADER,
      display: (d) => `${d.precipitation.toFixed(1)} mm`,
      simField: 'precipitation',
    },
    {
      label: FLOOD_STRINGS.PLUVIAL_PROB_HEADER,
      display: (d) => `${(d.prediction_value * 100).toFixed(2)}%`,
    },
  ];

  ngOnInit(): void {
    this.zoneSub = this.zoneDataService.zoneDataForSlot(this.panelSlot).subscribe((zd) => {
      this.activePartnerCity = partnerCityFromZoneData(zd);
      this.cdr.markForCheck();
    });

    this.sub = this.zoneDataService
      .fetchPluvialFloodPrediction(this.panelSlot)
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
      .fetchPluvialSimulatedForecast(this.panelSlot, this.simulatedForecast)
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
          raw_prediction_value:
            simulatedForecast[i]?.raw_prediction_value ?? day.raw_prediction_value,
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

  formatPercent(value: number, shouldMultiply = true): string {
    return `${(shouldMultiply ? value * 100 : value).toFixed(2)}%`;
  }

  private formatInterval(value: number): string {
    return `±${value.toFixed(2)}`;
  }

  get riskLevelClass(): string {
    if (!this.prediction) return '';
    return probabilityToRiskLevelClass(this.prediction.probability);
  }

  get floodProbabilityLabel(): string {
    return this.prediction ? this.formatPercent(this.prediction.probability) : '–';
  }

  get infobubbleProbabilityText(): string {
    const rawProb = this.prediction ? this.formatPercent(this.prediction.raw_probability) : '–';
    return (
      'Probabilité brute du modèle: ' +
      rawProb +
      ' ' +
      this.floodStrings.INFOBUBBLE_PLUVIAL_PROBABILITY
    );
  }

  get riskLevelLabel(): string {
    return RISK_LABELS[this.riskLevelClass] ?? '–';
  }

  get riskScore(): string {
    return this.prediction?.risk_score != null
      ? this.formatPercent(this.prediction.risk_score, false)
      : '–';
  }

  get confidenceStd(): string {
    return this.prediction?.confidence_std != null
      ? this.formatInterval(this.prediction.confidence_std)
      : '–';
  }

  get recommendationSeverity(): PublicDecisionSeverity {
    const cls = probabilityToRiskLevelClass(this.recoDayProbability);
    return pluvialRiskLevelToDecisionSeverity(cls);
  }

  get infobubbleRiskText(): string {
    return this.activePartnerCity == 'montreal'
      ? this.floodStrings.INFOBUBBLE_RISK_PLUV_MTL
      : this.floodStrings.INFOBUBBLE_RISK_SOCIAL;
  }

  getProbabilityTooltip = (day: PluvialForecast): string => {
    const rawProb =
      day.raw_prediction_value != null ? this.formatPercent(day.raw_prediction_value) : '–';
    return `Probabilité brute du modèle: ${rawProb}`;
  };
}
