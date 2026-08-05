import { effect, inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, catchError, of, tap } from 'rxjs';
import type { Map as MapboxMap } from 'mapbox-gl';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/auth/auth.service';
import {
  API_ENDPOINTS,
  MAP_COLORS,
  RISK_BANDS,
  RISK_KINDS,
  RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY,
} from '../../../constants/dashboard';
import { SocialFilter } from '../../../interfaces/social-filters';

const BASE_FILL_COLOR = MAP_COLORS.BASE_FILL_COLOR;
const BASE_LINE_COLOR = MAP_COLORS.BASE_LINE_COLOR;

@Injectable({ providedIn: 'root' })
export class MapGeoJsonService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private readonly originalScores = new Map<number, number>();
  private currentSelectedId: string | null = null;
  private riskZonesCache: {
    scopeKey: string;
    geojson: GeoJSON.FeatureCollection;
  } | null = null;

  readonly riskZonesScopeChanged$ = new Subject<void>();

  constructor() {
    let previousScopeKey: string | null = null;
    effect(() => {
      const sk = this.riskZonesScopeKey();
      if (previousScopeKey !== null && previousScopeKey !== sk) {
        this.riskZonesCache = null;
        this.riskZonesScopeChanged$.next();
      }
      previousScopeKey = sk;
    });
  }

  private riskZonesScopeKey(): string {
    const env = environment as { authDisabled?: boolean };
    if (env.authDisabled === true) {
      return RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY.FULL_MAP;
    }
    const u = this.auth.currentUser();
    if (!u) {
      return RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY.PENDING_USER;
    }
    if (u.is_admin) {
      return RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY.FULL_MAP;
    }
    return u.partner_city ?? RISK_ZONES_GEOJSON_SCOPE_CACHE_KEY.NO_PARTNER_CITY;
  }

  private fetchAllHazards(): Observable<GeoJSON.FeatureCollection | null> {
    const scopeKey = this.riskZonesScopeKey();
    if (this.riskZonesCache?.scopeKey === scopeKey) {
      return of(this.riskZonesCache.geojson);
    }
    return this.http
      .get<GeoJSON.FeatureCollection>(`${environment.apiUrl}${API_ENDPOINTS.RISK_ZONES_COMPUTED}`)
      .pipe(
        tap((geojson) => {
          this.riskZonesCache = { scopeKey, geojson };
        }),
        catchError((err) => {
          console.error('[MapGeoJsonService] Erreur chargement GeoJSON:', err);
          return of(null);
        }),
      );
  }

  private flattenHazard(
    geojson: GeoJSON.FeatureCollection,
    riskKind: string,
  ): GeoJSON.FeatureCollection {
    return {
      ...geojson,
      features: geojson.features.map((f) => {
        const props = (f.properties ?? {}) as Record<string, unknown>;
        const hazards = (props['hazards'] as Record<string, Record<string, unknown>>) ?? {};
        const hazardData = hazards[riskKind] ?? {};
        return {
          ...f,
          properties: {
            ...props,
            ...hazardData,
          },
        };
      }),
    };
  }

  setupRiskZonesLayers(
    map: MapboxMap,
    initialFilter?: string[],
    initialScoreThreshold?: number,
    onDone?: () => void,
    riskKind = RISK_KINDS.pluvial,
    socialFilter?: SocialFilter,
  ): void {
    this.fetchAllHazards().subscribe({
      next: (geojson) => {
        if (map.getSource('risk-zones')) {
          if (map.getLayer('risk-zones-fill')) map.removeLayer('risk-zones-fill');
          if (map.getLayer('risk-zones-line')) map.removeLayer('risk-zones-line');
          map.removeSource('risk-zones');
        }

        if (!geojson?.features?.length) {
          onDone?.();
          return;
        }

        const flattened = this.flattenHazard(geojson, riskKind);
        this._indexScores(flattened);

        map.addSource('risk-zones', {
          type: 'geojson',
          data: flattened,
          promoteId: 'adidu',
        });

        map.addLayer({
          id: 'risk-zones-fill',
          type: 'fill',
          source: 'risk-zones',
          paint: {
            'fill-color': BASE_FILL_COLOR as unknown as string,
            'fill-opacity': 0.4,
          },
        });

        map.addLayer({
          id: 'risk-zones-line',
          type: 'line',
          source: 'risk-zones',
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: {
            'line-color': BASE_LINE_COLOR as unknown as string,
            'line-width': 1.5,
          },
        });

        this.setRiskBandFilter(
          map,
          initialFilter ?? RISK_BANDS,
          initialScoreThreshold ?? 0,
          socialFilter,
        );
        onDone?.();
      },
      error: () => {
        onDone?.();
      },
    });
  }

  switchRiskKind(map: MapboxMap, riskKind: string): void {
    if (!this.riskZonesCache?.geojson) return;

    const flattened = this.flattenHazard(this.riskZonesCache.geojson, riskKind);
    this._indexScores(flattened);

    (map.getSource('risk-zones') as mapboxgl.GeoJSONSource)?.setData(flattened);
  }

  setRiskBandFilter(
    map: MapboxMap | null,
    selectedBands: string[],
    scoreThreshold = 0,
    socialFilter?: SocialFilter,
  ): void {
    if (!map?.getLayer('risk-zones-fill')) return;

    const updateLayers = (filterExpression?: unknown) => {
      const typedFilter = filterExpression as Parameters<MapboxMap['setFilter']>[1];
      map.setFilter('risk-zones-fill', typedFilter);
      map.setFilter('risk-zones-line', typedFilter);
    };

    if (selectedBands.length === 0) {
      updateLayers(['==', ['get', 'adidu'], -1]);
      return;
    }

    const conditions: unknown[][] = [];

    if (selectedBands.length < RISK_BANDS.length) {
      conditions.push(['in', ['get', 'display_band'], ['literal', selectedBands]]);
    }

    if (scoreThreshold > 0) {
      conditions.push(['>=', ['get', 'combined_probability'], scoreThreshold]);
    }

    if (socialFilter) {
      const socialConditions = [
        this.buildSocialCondition(socialFilter, 'pct_65_plus', 100),
        this.buildSocialCondition(socialFilter, 'revenu_median_menage', 500000),
        this.buildSocialCondition(socialFilter, 'gini', 1),
        this.buildSocialCondition(socialFilter, 'logement_reparations_majeures', 100),
      ];

      for (const condition of socialConditions) {
        if (condition !== null) {
          conditions.push(condition);
        }
      }
    }

    if (conditions.length === 0) {
      updateLayers();
    } else {
      const combinedFilter = conditions.length === 1 ? conditions[0] : ['all', ...conditions];
      updateLayers(combinedFilter);
    }
  }

  private buildSocialCondition(
    socialFilter: SocialFilter,
    key: keyof SocialFilter,
    maxLimit: number,
  ): unknown[] | null {
    const { min, max } = socialFilter[key];

    const isModified = min > 0 || max < maxLimit;

    if (!isModified) {
      return null;
    }

    return ['all', ['>=', ['get', key], min], ['<=', ['get', key], max]];
  }

  setSelectedZone(map: MapboxMap | null, id: string | null): void {
    if (!map?.getLayer('risk-zones-fill')) return;
    this.currentSelectedId = id;
    this.applySelectionColor(map);
  }

  private applySelectionColor(map: MapboxMap): void {
    const id = this.currentSelectedId;

    const fillColor =
      id == null
        ? BASE_FILL_COLOR
        : [
            'case',
            ['==', ['to-string', ['get', 'adidu']], id],
            MAP_COLORS.SELECTED_FILL_COLOR,
            BASE_FILL_COLOR,
          ];

    map.setPaintProperty('risk-zones-fill', 'fill-color', fillColor as unknown as string);
  }

  private _indexScores(geojson: GeoJSON.FeatureCollection): void {
    this.originalScores.clear();
    for (const f of geojson.features) {
      const zoneId = f.properties?.['adidu'] as string;
      const score = (f.properties?.['combined_probability'] as number) ?? 0;
      if (zoneId != null) this.originalScores.set(Number(zoneId), score);
    }
  }

  getOriginalScore(zoneId: string): number {
    return this.originalScores.get(Number(zoneId)) ?? 0;
  }
}
