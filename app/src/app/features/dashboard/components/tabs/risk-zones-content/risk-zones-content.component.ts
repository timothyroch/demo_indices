import { CommonModule } from '@angular/common';
import { Component, Input, inject } from '@angular/core';
import { ZoneDataService } from '../../../services/zone-data.service';
import {
  AIRE_DE_DIFFUSION_RISK_KINDS,
  getCityAverages,
  PanelSlot,
  type RiskKind,
} from '../../../../../constants/dashboard';
import { partnerCityFromZoneData } from '../../../../../constants/recommendation-sources';
import { RiskZoneConfig } from '../../../../../interfaces/coordinates.model';
import { InfoBubbleComponent } from '../ui-shared/info-bubble/info-bubble.component';
import { RISK_ZONES_CONTENT_STRINGS } from './risk-zones-content.constants';
export type { RiskZoneConfig };

interface SocialIndicatorComparison {
  value: number | null;
  avg: number;
  diff: number | null;
}

interface SocialIndicators {
  pct_65_plus: SocialIndicatorComparison;
  revenu_median_menage: SocialIndicatorComparison;
  gini: SocialIndicatorComparison;
  logement_reparations_majeures: SocialIndicatorComparison;
  // score_risque: number | null;
}

@Component({
  selector: 'app-risk-zones-content',
  standalone: true,
  imports: [CommonModule, InfoBubbleComponent],
  templateUrl: './risk-zones-content.component.html',
  styleUrl: './risk-zones-content.component.scss',
})
export class RiskZonesContentComponent {
  @Input() config: RiskZoneConfig = {
    title: 'Zones de risque',
    description: 'Visualisation des zones de risque sur la carte',
    helpText: 'Les zones colorées affichent différents niveaux de risque.',
  };
  @Input({ required: true }) panelSlot!: PanelSlot;

  readonly strings = RISK_ZONES_CONTENT_STRINGS;
  private readonly zoneDataService = inject(ZoneDataService);

  get zoneData(): Record<string, unknown> | null {
    return this.zoneDataService.getCurrentZoneData(this.panelSlot) as Record<
      string,
      unknown
    > | null;
  }

  get showSocialData(): boolean {
    const activeRiskTab = this.zoneDataService.getActiveRiskTabForSlot(this.panelSlot) as RiskKind;
    return AIRE_DE_DIFFUSION_RISK_KINDS.includes(activeRiskTab);
  }

  private buildComparison(value: unknown, avg: number): SocialIndicatorComparison {
    const num = value !== null && value !== undefined ? (value as number) : null;
    return {
      value: num,
      avg,
      diff: num !== null ? num - avg : null,
    };
  }

  get socialIndicators(): SocialIndicators | null {
    if (!this.zoneData) return null;

    const props = this.zoneData;
    const city = partnerCityFromZoneData(props);
    const avgs = getCityAverages(city);

    return {
      pct_65_plus: this.buildComparison(props['pct_65_plus'], avgs.pct_65_plus),
      revenu_median_menage: this.buildComparison(
        props['revenu_median_menage'],
        avgs.revenu_median_menage,
      ),
      gini: this.buildComparison(props['gini'], avgs.gini),
      logement_reparations_majeures: this.buildComparison(
        props['logement_reparations_majeures'],
        avgs.logement_reparations_majeures,
      ),
    };
  }
}
