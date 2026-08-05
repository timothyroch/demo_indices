import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import {
  PUBLIC_DECISION_SEVERITY,
  SECTION_STRINGS,
  type PublicDecisionSeverity,
  type RiskKind,
} from '../../../../../../constants/dashboard';
import { PARTNER_CITY_ID, type PartnerCityId } from '../../../../../../constants/partner-city';
import {
  PARTNER_CITY_LABELS,
  RECOMMENDATION_SOURCES_BY_CITY,
} from '../../../../../../constants/recommendation-sources';
import type {
  PublicDecisionRecommendationsByCity,
  PublicDecisionRecommendationsContent,
} from '../../../../../../interfaces/public-decision-recommendations.model';
import { RECO_DAY_ID_TODAY } from '../../../../../../constants/recommendations.shared';
import { RecoDaySelectComponent } from '../reco-day-select/reco-day-select.component';

let recommendationsPanelSeq = 0;

@Component({
  selector: 'app-recommendations',
  standalone: true,
  imports: [CommonModule, RecoDaySelectComponent],
  templateUrl: './recommendations.component.html',
  styleUrl: './recommendations.component.scss',
})
export class RecommendationsComponent {
  @Input() content?: PublicDecisionRecommendationsContent;
  @Input() contentByCity?: PublicDecisionRecommendationsByCity;
  @Input() riskKind?: RiskKind;
  @Input({ required: true }) severity!: PublicDecisionSeverity;
  @Input() showAtRiskSection = true;
  @Input() activePartnerCity: PartnerCityId | null = null;
  @Input() recoDayOptions: { id: string; label: string }[] = [];
  @Input() selectedDayId: string = RECO_DAY_ID_TODAY;

  @Output() selectedDayIdChange = new EventEmitter<string>();

  readonly recTitleString = SECTION_STRINGS.RECO_TITLE;
  readonly publicDecisionSeverity = PUBLIC_DECISION_SEVERITY;
  readonly bodyId = `reco-panel-body-${++recommendationsPanelSeq}`;

  expanded = true;

  toggleExpanded(): void {
    this.expanded = !this.expanded;
  }

  onDayChange(id: string): void {
    this.selectedDayId = id;
    this.selectedDayIdChange.emit(id);
  }

  get useDualCity(): boolean {
    return !!(this.contentByCity && this.riskKind);
  }

  get cityRecoBlocks(): {
    key: PartnerCityId;
    label: string;
    content: PublicDecisionRecommendationsContent;
    source: string;
  }[] {
    if (!this.contentByCity || !this.riskKind) return [];
    const src = RECOMMENDATION_SOURCES_BY_CITY[this.riskKind];
    const blocks = [
      {
        key: PARTNER_CITY_ID.Montreal,
        label: PARTNER_CITY_LABELS[PARTNER_CITY_ID.Montreal],
        content: this.contentByCity.montreal,
        source: src[PARTNER_CITY_ID.Montreal],
      },
      {
        key: PARTNER_CITY_ID.Laval,
        label: PARTNER_CITY_LABELS[PARTNER_CITY_ID.Laval],
        content: this.contentByCity.laval,
        source: src[PARTNER_CITY_ID.Laval],
      },
    ];
    if (this.activePartnerCity != null) {
      return blocks.filter((b) => b.key === this.activePartnerCity);
    }
    return blocks;
  }
}
