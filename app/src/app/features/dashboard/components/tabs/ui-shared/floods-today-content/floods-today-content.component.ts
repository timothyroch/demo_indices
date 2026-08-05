import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  getCityAverages,
  SECTION_STRINGS,
  TAB_SECTION_STRINGS,
} from '../../../../../../constants/dashboard';
import { InfoBubbleComponent } from '../info-bubble/info-bubble.component';
import { RainIntensityInfo } from '../../../../../../interfaces/flood.model';
import { RiskBadgeComponent } from '../risk-badge/risk-badge.component';
import { FLOOD_STRINGS } from '../../../../../../constants/floods';
import { PartnerCityId } from '../../../../../../constants/partner-city';

export interface RiskInfoStat {
  label: string;
  value: string;
  comparison?: 'above' | 'below' | null;
}

export interface RiskInfoData {
  isFloodable: boolean | null;
  floodableLabel: string;
  stats: RiskInfoStat[];
  synthesisLevel: 'high' | 'medium' | 'low' | null;
  synthesisText: string | null;
  rawEntries: { key: string; value: string }[];
}

@Component({
  selector: 'app-floods-today-content',
  standalone: true,
  imports: [CommonModule, InfoBubbleComponent, RiskBadgeComponent],
  templateUrl: './floods-today-content.component.html',
  styleUrl: './floods-today-content.component.scss',
})
export class FloodTodayContentComponent {
  @Input() probabilityLabel: string | null = null;
  @Input() riskScore: string | null = null;
  @Input() confidenceStd: string | null = null;
  @Input() infobubbleProbabilityText = '';
  @Input() infobubbleRiskText = '';
  @Input() rainIntensityInfo: RainIntensityInfo | null = null;
  @Input() riskLevelClass!: string;
  @Input() riskLevelLabel!: string;
  @Input() activePartnerCity!: PartnerCityId | null;
  @Input() zoneData!: Record<string, unknown> | null;

  readonly strings = TAB_SECTION_STRINGS;
  readonly todayTitleString = SECTION_STRINGS.TODAY_TITLE;
  readonly floodStrings = FLOOD_STRINGS;

  get riskInfoData(): RiskInfoData {
    if (!this.zoneData) {
      return {
        isFloodable: null,
        floodableLabel: '',
        stats: [],
        synthesisLevel: null,
        synthesisText: null,
        rawEntries: [],
      };
    }

    const age65 = this.zoneData['pct_65_plus'] as number | undefined;
    const income = this.zoneData['revenu_median_menage'] as number | undefined;
    const majorRepairs = this.zoneData['logement_reparations_majeures'] as number | undefined;

    const floodVal = this.zoneData['val_crues'];
    const isFloodable = floodVal !== undefined && floodVal !== null && floodVal !== 'NoData';

    if (age65 !== undefined && income !== undefined) {
      const cityAverages = getCityAverages(this.activePartnerCity);
      const isLaval = this.activePartnerCity === 'laval';
      const cityLabel = isLaval ? 'lavalloise' : 'montréalaise';

      const isVulnAge = age65 > cityAverages.pct_65_plus;
      const isVulnIncome = income < cityAverages.revenu_median_menage;

      const stats: RiskInfoStat[] = [
        {
          label: `Population 65+ (moy. ${cityLabel}: ${cityAverages.pct_65_plus}%)`,
          value: `${age65.toFixed(1)}%`,
          comparison: isVulnAge ? 'above' : 'below',
        },
        {
          label: `Revenu médian (moy. ${cityLabel}: ${cityAverages.revenu_median_menage.toLocaleString('fr-CA')} $)`,
          value: `${income.toLocaleString('fr-CA')} $`,
          comparison: isVulnIncome ? 'below' : 'above',
        },
      ];

      if (majorRepairs !== undefined) {
        const isVulnRepairs = majorRepairs > cityAverages.logement_reparations_majeures;
        stats.push({
          label: `Logements en réparations majeures (moy. ${cityLabel}: ${cityAverages.logement_reparations_majeures}%)`,
          value: `${majorRepairs.toFixed(1)}%`,
          comparison: isVulnRepairs ? 'above' : 'below',
        });
      }

      let synthesisLevel: 'high' | 'medium' | 'low';
      let synthesisText: string;
      if (isVulnAge && isVulnIncome) {
        synthesisLevel = 'high';
        synthesisText = this.floodStrings.SOCIAL_SYNTHESIS_HIGH_VULN;
      } else if (isVulnAge || isVulnIncome) {
        synthesisLevel = 'medium';
        synthesisText = this.floodStrings.SOCIAL_SYNTHESIS_MED_VULN;
      } else {
        synthesisLevel = 'low';
        synthesisText = this.floodStrings.SOCIAL_SYNTHESIS_LOW_VULN;
      }

      return {
        isFloodable,
        floodableLabel: isFloodable
          ? this.floodStrings.ZONE_IS_FLOODABLE
          : this.floodStrings.ZONE_NOT_FLOODABLE,
        stats,
        synthesisLevel,
        synthesisText,
        rawEntries: [],
      };
    }

    // Fallback: raw zone data entries
    const IGNORE_KEYS = ['id', 'layer', 'source', 'bbox', 'center', 'geometry'];
    const rawEntries = Object.entries(this.zoneData)
      .filter(
        ([key, value]) =>
          value !== null &&
          value !== undefined &&
          typeof value !== 'object' &&
          typeof value !== 'function' &&
          !IGNORE_KEYS.includes(key),
      )
      .map(([key, value]) => ({ key, value: String(value) }));

    return {
      isFloodable,
      floodableLabel: isFloodable
        ? this.floodStrings.ZONE_IS_FLOODABLE
        : this.floodStrings.ZONE_NOT_FLOODABLE,
      stats: [],
      synthesisLevel: null,
      synthesisText: null,
      rawEntries,
    };
  }
}
