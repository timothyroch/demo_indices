import { Component, EventEmitter, inject, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PluvialFloodsContentComponent } from '../tabs/pluvial-floods-content/pluvial-floods-content.component';
import { FluvialFloodsContentComponent } from '../tabs/fluvial-floods-content/fluvial-floods-content.component';
import { HeatwaveContentComponent } from '../tabs/heatwave-content/heatwave-content.component';
import { SnowContentComponent } from '../tabs/snow-content/snow-content.component';
import { ZoneDataService } from '../../services/zone-data.service';
import {
  PanelSlot,
  RISK_TABS_STRINGS,
  RISK_ZONE_CONFIGS,
  type RiskKind,
} from '../../../../constants/dashboard';
import { ActionJournalService } from '../../../../core/journal/action-journal.service';

interface Tab {
  id: RiskKind;
  label: string;
  svg: string;
  color: string;
  disabled?: boolean;
}

@Component({
  selector: 'app-risk-tabs',
  standalone: true,
  imports: [
    CommonModule,
    PluvialFloodsContentComponent,
    FluvialFloodsContentComponent,
    HeatwaveContentComponent,
    SnowContentComponent,
  ],
  templateUrl: './risk-tabs.component.html',
  styleUrl: './risk-tabs.component.css',
})
export class RiskTabsComponent {
  @Input({ required: true }) panelSlot!: PanelSlot;
  @Output() tabChange = new EventEmitter<RiskKind>();

  private readonly zoneDataService = inject(ZoneDataService);
  private readonly router = inject(Router);
  private readonly actionJournal = inject(ActionJournalService);

  readonly strings = RISK_TABS_STRINGS;

  readonly allTabs: Tab[] = [
    {
      id: 'pluvial',
      label: RISK_TABS_STRINGS.PLUVIAL,
      svg: 'assets/svg/rain-cloud-weather.svg',
      color: '#cce5ff',
    },
    {
      id: 'crues',
      label: RISK_TABS_STRINGS.FLUVIAL,
      svg: 'assets/svg/flood-svgrepo-com.svg',
      color: '#99ccff',
    },
    {
      id: 'canicules',
      label: RISK_TABS_STRINGS.HEATWAVES,
      svg: 'assets/svg/heat.svg',
      color: '#ffe6cc',
    },
    {
      id: 'neige',
      label: RISK_TABS_STRINGS.SNOW,
      svg: 'assets/svg/snow-crystal-2.svg',
      color: '#ccf0ff',
    },
  ];

  readonly riskZoneConfigs = RISK_ZONE_CONFIGS;

  get tabs(): Tab[] {
    const zoneData = this.zoneDataService.getCurrentZoneData(this.panelSlot);
    if (!zoneData) {
      return this.allTabs.map((t) => ({
        ...t,
        disabled: t.id === 'pluvial' || t.id === 'crues',
      }));
    }
    return this.allTabs;
  }

  get activeTab(): RiskKind {
    return this.zoneDataService.getActiveRiskTabForSlot(this.panelSlot);
  }

  select(id: RiskKind): void {
    const tab = this.tabs.find((t) => t.id === id);
    if (!tab || tab.disabled || id === this.activeTab) {
      return;
    }
    this.zoneDataService.setActiveRiskTabForSlot(this.panelSlot, id);
    this.actionJournal.logAction({
      action: 'model_tab_click',
      route: this.router.url,
      label: id,
    });
    this.tabChange.emit(id);
  }
}
