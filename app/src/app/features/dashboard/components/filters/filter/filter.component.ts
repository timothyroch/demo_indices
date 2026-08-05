import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FILTER_STRINGS,
  RiskKind,
  SOCIAL_FILTER_DEFAULTS,
} from '../../../../../constants/dashboard';
import { HUMIDEX_MIN } from '../../../../../constants/heatwave';
import { RiskFilterComponent } from '../risk-filter/risk-filter.component';
import { SocialFilterComponent } from '../social-filter/social-filter.component';
import { SocialFilter } from '../../../../../interfaces/social-filters';

@Component({
  selector: 'app-filter',
  standalone: true,
  imports: [CommonModule, RiskFilterComponent, SocialFilterComponent],
  templateUrl: './filter.component.html',
  styleUrl: './filter.component.scss',
})
export class FilterComponent implements OnChanges {
  @Input() riskFilter = { vert: true, jaune: true, orange: true, rouge: true };
  @Input() scoreThreshold = 0;
  @Input() riskKind: RiskKind = 'pluvial';
  @Input() socialFilter: SocialFilter = SOCIAL_FILTER_DEFAULTS;

  isCollapsed = globalThis.window?.matchMedia('(max-width: 640px)').matches;

  @Output() riskFilterChange = new EventEmitter<{
    vert: boolean;
    jaune: boolean;
    orange: boolean;
    rouge: boolean;
  }>();
  @Output() scoreThresholdChange = new EventEmitter<number>();
  @Output() socialFilterChange = new EventEmitter<SocialFilter>();

  readonly strings = FILTER_STRINGS;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['riskKind'] && !changes['riskKind'].firstChange) {
      const newMode = changes['riskKind'].currentValue === 'canicules' ? 'humidex' : 'percent';
      const previousMode =
        changes['riskKind'].previousValue === 'canicules' ? 'humidex' : 'percent';

      if (newMode !== previousMode) {
        const defaultThreshold = newMode === 'humidex' ? HUMIDEX_MIN : 0;
        this.scoreThresholdChange.emit(defaultThreshold);
      }
    }
  }

  toggleCollapse(): void {
    this.isCollapsed = !this.isCollapsed;
  }
}
