import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SimulationActionsComponent } from '../simulation-actions/simulation-actions.component';
import { SimulationModeToggleComponent } from '../simulation-mode-toggle/simulation-mode-toggle.component';
import { InfoBubbleComponent } from '../info-bubble/info-bubble.component';
import { RISK_BAND_CLASS, SECTION_STRINGS } from '../../../../../../constants/dashboard';
import {
  coerceProbabilityValue,
  probabilityToRiskLevelClass,
} from '../../../../../../constants/recommendations.shared';
import { parseLocalDateFromYmd } from '../recommendations/calendar-date';

export type RowRiskLevel = 'low' | 'moderate' | 'high';

export const ROW_RISK_LEVEL = {
  LOW: 'low',
  MODERATE: 'moderate',
  HIGH: 'high',
} as const satisfies Record<string, RowRiskLevel>;

export interface ForecastColumn<T> {
  label: string;
  display: (day: T) => string;
  simField?: keyof T;
}

function riskBandToRowLevel(cls: string): RowRiskLevel {
  if (cls === RISK_BAND_CLASS.ORANGE) return ROW_RISK_LEVEL.MODERATE;
  if (cls === RISK_BAND_CLASS.RED) return ROW_RISK_LEVEL.HIGH;
  return ROW_RISK_LEVEL.LOW;
}

const DEFAULT_ROW_CLASS_FN = (predictionValue: number): RowRiskLevel => {
  return riskBandToRowLevel(probabilityToRiskLevelClass(predictionValue));
};

@Component({
  selector: 'app-forecast-content',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SimulationActionsComponent,
    SimulationModeToggleComponent,
    InfoBubbleComponent,
  ],
  templateUrl: './forecast-content.component.html',
  styleUrl: './forecast-content.component.scss',
})
export class ForecastContentComponent<T extends { date: string; prediction_value: number }> {
  @Input({ required: true }) forecast!: T[];
  @Input({ required: true }) simulatedForecast!: T[];
  @Input({ required: true }) columns!: ForecastColumn<T>[];
  @Input() sectionSubtitle!: string;
  @Input() isSimulationOpen = false;
  @Input() isSimulating = false;
  @Input() probabilityTooltip?: (day: T) => string;
  @Input() rowClassFn: (predictionValue: number) => RowRiskLevel = DEFAULT_ROW_CLASS_FN;

  @Output() openSimulation = new EventEmitter<void>();
  @Output() closeSimulation = new EventEmitter<void>();
  @Output() applySimulation = new EventEmitter<void>();
  @Output() resetSimulation = new EventEmitter<void>();

  readonly forecastTitleString = SECTION_STRINGS.FORECAST_TITLE;
  readonly rowRisk = ROW_RISK_LEVEL;

  formatDate(dateStr: string): string {
    const d = parseLocalDateFromYmd(dateStr);
    if (Number.isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('fr-CA', { month: 'short', day: 'numeric' });
  }

  rowRiskLevel(day: T): RowRiskLevel {
    const n = coerceProbabilityValue(day.prediction_value as unknown);
    if (!Number.isFinite(n)) {
      return ROW_RISK_LEVEL.LOW;
    }
    return this.rowClassFn(n);
  }
}
