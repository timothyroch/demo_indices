import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { RiskTabsComponent } from '../risk-tabs/risk-tabs.component';
import { ZoneDataService } from '../../services/zone-data.service';
import { INITIAL_WEATHER, PanelSlot, SIDE_PANEL_STRINGS } from '../../../../constants/dashboard';
import { Coordinates } from '../../../../interfaces/coordinates.model';
import { WeatherState } from '../../../../interfaces/weather.model';

interface ParsedLine {
  key: string;
  value: string;
}

@Component({
  selector: 'app-side-panel',
  standalone: true,
  imports: [CommonModule, RiskTabsComponent],
  templateUrl: './side-panel.component.html',
  styleUrls: ['./side-panel.component.css'],
  host: {
    '[class.side-panel-host--secondary]': 'panelSlot === "secondary"',
  },
})
export class SidePanelComponent implements OnInit, OnChanges, OnDestroy {
  @Input({ required: true }) panelSlot!: PanelSlot;
  @Input() coords: Coordinates | null = null;
  @Input() zoneId: string | null = null;
  @Input() zoneData: Record<string, unknown> | null = null;
  @Input() secondaryOpened = false;
  @Input() comparisonAllowed = true;
  @Output() closePanel = new EventEmitter<void>();
  @Output() openSecondaryPanel = new EventEmitter<void>();

  weatherState: WeatherState = INITIAL_WEATHER;
  placeLabel: string | null = null;

  readonly strings = SIDE_PANEL_STRINGS;

  private readonly zoneDataService = inject(ZoneDataService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly sub = new Subscription();

  ngOnInit(): void {
    const stream =
      this.panelSlot === 'primary'
        ? this.zoneDataService.weatherPrimary$
        : this.zoneDataService.weatherSecondary$;
    this.sub.add(
      stream.subscribe((s) => {
        this.weatherState = s;
        this.cdr.markForCheck();
      }),
    );
    const placeStream =
      this.panelSlot === 'primary'
        ? this.zoneDataService.placeLabelPrimary$
        : this.zoneDataService.placeLabelSecondary$;
    this.sub.add(
      placeStream.subscribe((label) => {
        this.placeLabel = label;
        this.cdr.markForCheck();
      }),
    );
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['coords'] || changes['zoneId']) {
      if (this.panelSlot === 'primary') {
        if (this.coords && this.zoneId) {
          this.zoneDataService.loadPrimaryZone(
            this.coords,
            this.zoneId,
            this.zoneData ?? undefined,
          );
        } else if (this.coords) {
          this.zoneDataService.loadWeatherOnly(this.coords, 'primary');
        } else {
          this.zoneDataService.resetPrimary();
        }
      } else if (this.coords && this.zoneId) {
        this.zoneDataService.loadSecondaryZone(
          this.coords,
          this.zoneId,
          this.zoneData ?? undefined,
        );
      } else if (this.coords) {
        this.zoneDataService.loadWeatherOnly(this.coords, 'secondary');
      } else {
        this.zoneDataService.resetSecondary();
      }
    }
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  onClose(): void {
    this.closePanel.emit();
  }

  onOpenSecondary(): void {
    this.openSecondaryPanel.emit();
  }

  get visible(): boolean {
    if (this.panelSlot === 'secondary') {
      return true;
    }
    return this.weatherState.status !== 'idle';
  }

  get showSecondaryPlaceholder(): boolean {
    return this.panelSlot === 'secondary' && !this.coords;
  }

  get panelHeaderTitle(): string {
    if (this.showSecondaryPlaceholder) {
      return this.strings.SECONDARY_PANEL_TITLE;
    }
    if (this.coords) {
      if (this.placeLabel) {
        return this.placeLabel;
      }
      return this.strings.PLACE_TITLE_PENDING;
    }
    return '';
  }

  get weatherLines(): ParsedLine[] {
    const w = this.weatherState.data;
    if (!w) return [];
    const lines: ParsedLine[] = [];
    if (w.temperature != null)
      lines.push({
        key: this.strings.WEATHER_TEMPERATURE,
        value: `${w.temperature.toFixed(1)} °C`,
      });
    if (w.humidity != null)
      lines.push({ key: this.strings.WEATHER_HUMIDITY, value: `${w.humidity.toFixed(0)} %` });
    if (w.precipitation != null)
      lines.push({
        key: this.strings.WEATHER_PRECIPITATION,
        value: `${w.precipitation.toFixed(1)} mm`,
      });
    return lines;
  }
}
