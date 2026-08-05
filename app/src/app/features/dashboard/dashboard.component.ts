import { ChangeDetectorRef, Component, effect, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NavbarComponent } from './components/navbar/navbar.component';
import { MapComponent } from './components/map/map.component';
import { SidePanelComponent } from './components/side-panel/side-panel.component';
import { Coordinates } from '../../interfaces/coordinates.model';
import { LayoutBreakpointsService } from './services/layout-breakpoints.service';
import { ZoneDataService } from './services/zone-data.service';
import { RiskKind, SOCIAL_FILTER_DEFAULTS } from '../../constants/dashboard';
import { AlertsService } from '../../core/alerts/alerts.service';
import { MapClickEvent } from '../../interfaces/map-click-event';
import { FilterComponent } from './components/filters/filter/filter.component';
import { SocialFilter } from '../../interfaces/social-filters';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NavbarComponent,
    MapComponent,
    SidePanelComponent,
    FilterComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit {
  selectedFeatureId: string | null = null;
  panelCoords: Coordinates | null = null;
  selectedZoneData: Record<string, unknown> | null = null;

  secondaryPanelOpen = false;
  secondaryFeatureId: string | null = null;
  secondaryPanelCoords: Coordinates | null = null;
  secondaryZoneData: Record<string, unknown> | null = null;

  riskFilter = { vert: true, jaune: true, orange: true, rouge: true };
  scoreThreshold = 0;
  socialFilter: SocialFilter = SOCIAL_FILTER_DEFAULTS;

  private readonly cdr = inject(ChangeDetectorRef);
  private readonly zoneDataService = inject(ZoneDataService);
  private readonly alertsService = inject(AlertsService);
  readonly layout = inject(LayoutBreakpointsService);

  constructor() {
    effect(() => {
      if (!this.layout.comparisonAllowed() && this.secondaryPanelOpen) {
        this.onSecondaryPanelClose();
      }
    });
  }

  ngOnInit(): void {
    this.alertsService.evaluateRiskAlerts().subscribe({
      error: () => undefined,
    });
  }

  get riskKind(): RiskKind {
    return this.zoneDataService.activeRiskTab;
  }

  get mapSelectedFeatureId(): string | null {
    if (this.secondaryPanelOpen) {
      return this.secondaryFeatureId ?? this.selectedFeatureId;
    }
    return this.selectedFeatureId;
  }

  get selectedRiskLevels(): string[] {
    const levels: string[] = [];
    if (this.riskFilter.vert) levels.push('vert');
    if (this.riskFilter.jaune) levels.push('jaune');
    if (this.riskFilter.orange) levels.push('orange');
    if (this.riskFilter.rouge) levels.push('rouge');
    return levels;
  }

  onRiskFilterChange(filter: {
    vert: boolean;
    jaune: boolean;
    orange: boolean;
    rouge: boolean;
  }): void {
    this.riskFilter = filter;
    this.cdr.markForCheck();
  }

  onScoreThresholdChange(value: number): void {
    this.scoreThreshold = value;
    this.cdr.markForCheck();
  }

  onSocialFilterChange(filter: SocialFilter): void {
    this.socialFilter = filter;
    this.cdr.markForCheck();
  }

  onMapClick(event: MapClickEvent): void {
    const properties = event.feature?.properties;
    const zoneData = properties ?? null;
    const rawAdidu = properties?.['adidu'];
    const coords = { lat: event.centerLat, lng: event.centerLng };

    if (this.secondaryPanelOpen) {
      this.secondaryFeatureId = rawAdidu ?? null;
      this.secondaryPanelCoords = coords;
      this.secondaryZoneData = zoneData;
    } else {
      this.selectedFeatureId = rawAdidu ?? null;
      this.panelCoords = coords;
      this.selectedZoneData = zoneData;
    }

    this.cdr.markForCheck();
  }

  onPanelClose(): void {
    this.selectedFeatureId = null;
    this.panelCoords = null;
    this.selectedZoneData = null;
    if (this.secondaryPanelOpen) {
      this.onSecondaryPanelClose();
    }
    this.cdr.markForCheck();
  }

  onOpenSecondaryPanel(): void {
    if (!this.layout.comparisonAllowed()) {
      return;
    }
    this.secondaryPanelOpen = true;
    this.cdr.markForCheck();
  }

  onSecondaryPanelClose(): void {
    this.secondaryPanelOpen = false;
    this.secondaryFeatureId = null;
    this.secondaryPanelCoords = null;
    this.secondaryZoneData = null;
    this.zoneDataService.resetSecondary();
    this.cdr.markForCheck();
  }
}
