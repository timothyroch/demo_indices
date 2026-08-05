import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, catchError, EMPTY, Observable, of, tap } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  API_ENDPOINTS,
  buildWeatherPredictionCacheKey,
  DEFAULT_WEATHER_ERROR_STATE,
  DEFAULT_WEATHER_LOADING_STATE,
  INITIAL_WEATHER,
  PanelSlot,
} from '../../../constants/dashboard';
import { Coordinates } from '../../../interfaces/coordinates.model';
import { RiskKind } from '../../../../app/constants/dashboard';
import { WeatherData, WeatherState } from '../../../interfaces/weather.model';
import { HeatwavePrediction } from '../../../interfaces/heatwave.model';
import { SnowDayDetail, SnowPrediction } from '../../../interfaces/snow.model';
import {
  FluvialForecast,
  FluvialPrediction,
  PluvialForecast,
  PluvialPrediction,
} from '../../../interfaces/flood.model';

interface SlotState {
  location: Coordinates;
  zoneId: string;
  zoneData: Record<string, unknown> | null;
  zoneData$: BehaviorSubject<Record<string, unknown> | null>;
  currentZoneKey: string | null;
  activeRiskTab: RiskKind;
  weather$: BehaviorSubject<WeatherState>;
  placeLabel$: BehaviorSubject<string | null>;
}

@Injectable({ providedIn: 'root' })
export class ZoneDataService {
  private readonly http = inject(HttpClient);

  private readonly slots: Record<PanelSlot, SlotState> = {
    primary: ZoneDataService.createInitialSlotState(),
    secondary: ZoneDataService.createInitialSlotState(),
  };

  private static createInitialSlotState(): SlotState {
    return {
      location: { lat: 0, lng: 0 },
      zoneId: '',
      zoneData: null,
      zoneData$: new BehaviorSubject<Record<string, unknown> | null>(null),
      currentZoneKey: null,
      activeRiskTab: 'pluvial',
      weather$: new BehaviorSubject<WeatherState>(INITIAL_WEATHER),
      placeLabel$: new BehaviorSubject<string | null>(null),
    };
  }

  private _heatwaveCache = new Map<string, HeatwavePrediction>();
  private _snowCache = new Map<string, SnowPrediction>();

  readonly weatherPrimary$ = this.slots.primary.weather$.asObservable();
  readonly weatherSecondary$ = this.slots.secondary.weather$.asObservable();

  readonly placeLabelPrimary$ = this.slots.primary.placeLabel$.asObservable();
  readonly placeLabelSecondary$ = this.slots.secondary.placeLabel$.asObservable();

  readonly zoneDataPrimary$ = this.slots.primary.zoneData$.asObservable();
  readonly zoneDataSecondary$ = this.slots.secondary.zoneData$.asObservable();

  zoneDataForSlot(slot: PanelSlot): Observable<Record<string, unknown> | null> {
    return slot === 'primary' ? this.zoneDataPrimary$ : this.zoneDataSecondary$;
  }

  get activeRiskTab(): RiskKind {
    return this.slots.primary.activeRiskTab;
  }

  getActiveRiskTabForSlot(slot: PanelSlot): RiskKind {
    return this.slots[slot].activeRiskTab;
  }

  setActiveRiskTabForSlot(slot: PanelSlot, tab: RiskKind): void {
    this.slots[slot].activeRiskTab = tab;
  }

  getCurrentZoneData(slot: PanelSlot): Record<string, unknown> | null {
    return this.slots[slot].zoneData;
  }

  loadPrimaryZone(coords: Coordinates, zoneId: string, zoneData?: Record<string, unknown>): void {
    this.loadZoneForSlot('primary', coords, zoneId, zoneData);
  }

  loadSecondaryZone(coords: Coordinates, zoneId: string, zoneData?: Record<string, unknown>): void {
    this.loadZoneForSlot('secondary', coords, zoneId, zoneData);
  }

  loadWeatherOnly(coords: Coordinates, slot: PanelSlot = 'primary'): void {
    const currentTab = this.slots[slot].activeRiskTab;
    if (currentTab === 'pluvial' || currentTab === 'crues') {
      this.slots[slot].activeRiskTab = 'canicules';
    }
    this.loadZoneForSlot(slot, coords, '');
  }

  resetPrimary(): void {
    this.clearZoneState('primary');
  }

  resetSecondary(): void {
    this.clearZoneState('secondary');
  }

  clearZoneState(slot: PanelSlot): void {
    const slotState = this.slots[slot];
    slotState.weather$.next(INITIAL_WEATHER);
    slotState.placeLabel$.next(null);
    slotState.zoneData = null;
    slotState.zoneData$.next(null);
    slotState.currentZoneKey = null;
  }

  fetchFluvialFloodPrediction(slot: PanelSlot = 'primary'): Observable<FluvialPrediction> {
    const { lat, lng } = this.getLocation(slot);

    return this.http.post<FluvialPrediction>(
      `${environment.apiUrl}${API_ENDPOINTS.FLUVIAL_FLOOD_PREDICT}`,
      {
        lat,
        lng,
        adidu: this.getZoneId(slot),
      },
    );
  }

  fetchFluvialSimulatedForecast(
    slot: PanelSlot = 'primary',
    simulationOverrides: FluvialForecast[],
  ): Observable<FluvialForecast[]> {
    const { lat, lng } = this.getLocation(slot);

    return this.http.post<FluvialForecast[]>(
      `${environment.apiUrl}${API_ENDPOINTS.FLUVIAL_FLOOD_SIMULATE_PREDICTION}`,
      {
        lat,
        lng,
        adidu: this.getZoneId(slot),
        simulation_overrides: simulationOverrides,
      },
    );
  }

  fetchPluvialFloodPrediction(slot: PanelSlot = 'primary'): Observable<PluvialPrediction> {
    const { lat, lng } = this.getLocation(slot);

    return this.http.post<PluvialPrediction>(
      `${environment.apiUrl}${API_ENDPOINTS.PLUVIAL_FLOOD_PREDICT}`,
      {
        lat,
        lng,
        adidu: this.getZoneId(slot),
      },
    );
  }

  fetchPluvialSimulatedForecast(
    slot: PanelSlot = 'primary',
    simulationOverrides: PluvialForecast[],
  ): Observable<PluvialForecast[]> {
    const { lat, lng } = this.getLocation(slot);

    return this.http.post<PluvialForecast[]>(
      `${environment.apiUrl}${API_ENDPOINTS.PLUVIAL_FLOOD_SIMULATE_PREDICTION}`,
      {
        lat,
        lng,
        adidu: this.getZoneId(slot),
        simulation_overrides: simulationOverrides,
      },
    );
  }

  fetchHeatwavePrediction(slot: PanelSlot = 'primary'): Observable<HeatwavePrediction> {
    const { lat, lng } = this.getLocation(slot);
    this.slots[slot].currentZoneKey = `${lat}_${lng}`;

    const zoneId = this.getZoneId(slot);
    const key = buildWeatherPredictionCacheKey(lat, lng, zoneId);
    const cached = this._heatwaveCache.get(key);
    if (cached) {
      return of(cached);
    }
    const payload: Record<string, string | number> = { lat, lng };
    if (zoneId) {
      payload['adidu'] = zoneId;
    }

    return this.http
      .post<HeatwavePrediction>(`${environment.apiUrl}${API_ENDPOINTS.HEATWAVE_PREDICT}`, payload)
      .pipe(tap((res) => this._heatwaveCache.set(key, res)));
  }

  fetchSnowPrediction(slot: PanelSlot = 'primary'): Observable<SnowPrediction> {
    const { lat, lng } = this.getLocation(slot);
    const zoneId = this.getZoneId(slot);
    const key = buildWeatherPredictionCacheKey(lat, lng, zoneId);
    const cached = this._snowCache.get(key);
    if (cached) {
      return of(cached);
    }

    const payload: Record<string, string | number> = { lat, lng };
    if (zoneId) {
      payload['adidu'] = zoneId;
    }
    return this.http
      .post<SnowPrediction>(`${environment.apiUrl}${API_ENDPOINTS.SNOW_PREDICT}`, payload)
      .pipe(tap((res) => this._snowCache.set(key, res)));
  }

  fetchSnowSimulatedForecast(
    slot: PanelSlot = 'primary',
    simulationOverrides: SnowDayDetail[],
  ): Observable<SnowDayDetail[]> {
    const { lat, lng } = this.getLocation(slot);

    const zoneId = this.getZoneId(slot);
    const payload: Record<string, unknown> = {
      lat,
      lng,
      simulation_overrides: simulationOverrides,
    };
    if (zoneId) {
      payload['adidu'] = zoneId;
    }

    return this.http.post<SnowDayDetail[]>(
      `${environment.apiUrl}${API_ENDPOINTS.SNOW_SIMULATE_PREDICTION}`,
      payload,
    );
  }

  private loadZoneForSlot(
    slot: PanelSlot,
    coords: Coordinates,
    zoneId: string,
    zoneData?: Record<string, unknown>,
  ): void {
    const slotState = this.slots[slot];
    slotState.location = coords;
    slotState.zoneId = zoneId;
    slotState.zoneData = zoneData ?? null;
    slotState.zoneData$.next(slotState.zoneData);
    slotState.currentZoneKey = `${coords.lat}_${coords.lng}`;
    slotState.weather$.next(DEFAULT_WEATHER_LOADING_STATE);
    this.fetchPlaceLabel(slot, coords);

    this.http
      .get<WeatherData>(`${environment.apiUrl}${API_ENDPOINTS.WEATHER_DATA}`, {
        params: { lat: coords.lat, lng: coords.lng },
      })
      .pipe(
        catchError(() => {
          slotState.weather$.next(DEFAULT_WEATHER_ERROR_STATE);
          return EMPTY;
        }),
      )
      .subscribe((data) => {
        slotState.weather$.next({ status: 'ready', data, errorMessage: null });
      });
  }

  private fetchPlaceLabel(slot: PanelSlot, coords: Coordinates): void {
    const subject = this.slots[slot].placeLabel$;
    subject.next(null);
    this.http
      .get<{ label: string }>(`${environment.apiUrl}${API_ENDPOINTS.PLACE_LABEL}`, {
        params: { lat: coords.lat, lng: coords.lng },
      })
      .pipe(catchError(() => of({ label: '' })))
      .subscribe((res) => {
        const v = res.label?.trim();
        subject.next(v || '—');
      });
  }

  private getLocation(slot: PanelSlot): Coordinates {
    return this.slots[slot].location;
  }

  private getZoneId(slot: PanelSlot): string {
    return this.slots[slot].zoneId;
  }
}
