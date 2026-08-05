import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  EventEmitter,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import mapboxgl, { Map, MapMouseEvent } from 'mapbox-gl';
import { environment } from '../../../../../environments/environment';
import { MapGeoJsonService } from '../../services/map-geojson.service';
import {
  MAP_STRINGS,
  MAP_ZONE_VIEWPORT_FRACTIONS,
  RISK_BANDS,
  RiskKind,
  SOCIAL_FILTER_DEFAULTS,
} from '../../../../constants/dashboard';
import { MapClickEvent } from '../../../../interfaces/map-click-event';
import { SocialFilter } from '../../../../interfaces/social-filters';

@Component({
  selector: 'app-map',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './map.component.html',
  styleUrls: ['./map.component.css'],
})
export class MapComponent implements AfterViewInit, OnDestroy, OnChanges {
  @ViewChild('mapContainer') mapContainerRef!: ElementRef<HTMLDivElement>;

  @Input() selectedFeatureId: string | null = null;
  @Input() riskBandFilter: string[] = RISK_BANDS;
  @Input() scoreThreshold = 0;
  @Input() riskKind: RiskKind = 'pluvial';
  @Input() socialFilter: SocialFilter = SOCIAL_FILTER_DEFAULTS;

  @Output() mapClick = new EventEmitter<MapClickEvent>();

  layersLoading = true;
  readonly strings = MAP_STRINGS;
  hoveredCityName: string | null = null;
  hoverX = 0;
  hoverY = 0;
  zoomLevel = 9;
  minZoom = 2;
  maxZoom = 16;
  zoomStep = 0.5;

  private map: Map | null = null;
  private readonly token = environment.mapboxToken;
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly mapGeoJsonService = inject(MapGeoJsonService);

  ngAfterViewInit(): void {
    this.mapGeoJsonService.riskZonesScopeChanged$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!this.map?.isStyleLoaded()) return;
        this.layersLoading = true;
        this.cdr.markForCheck();
        this.mapGeoJsonService.setupRiskZonesLayers(
          this.map,
          this.riskBandFilter,
          this.scoreThreshold,
          () => {
            this.layersLoading = false;
            this.cdr.markForCheck();
          },
          this.riskKind,
          this.socialFilter,
        );
      });
    if (!this.token || !this.mapContainerRef?.nativeElement) return;
    mapboxgl.accessToken = this.token;
    this.map = new mapboxgl.Map({
      container: this.mapContainerRef.nativeElement,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-73.55, 45.55],
      zoom: this.zoomLevel,
      attributionControl: false,
      touchPitch: false,
      dragRotate: false,
    });
    this.map.touchZoomRotate.disableRotation();
    this.map.on('zoom', () => this.syncZoomFromMap());
    this.map.on('load', () =>
      this.mapGeoJsonService.setupRiskZonesLayers(
        this.map!,
        this.riskBandFilter,
        this.scoreThreshold,
        () => {
          this.layersLoading = false;
          this.cdr.markForCheck();
        },
        this.riskKind,
        this.socialFilter,
      ),
    );
    this.map.on('mousemove', (e: MapMouseEvent) => this.onMapMouseMove(e));
    this.map.on('mouseleave', () => this.onMapMouseLeave());
    this.map.on('click', (e: MapMouseEvent) => this.onMapClick(e));
    window.addEventListener('resize', this.scheduleMapResize);
    window.addEventListener('orientationchange', this.scheduleMapResize);
    if (typeof visualViewport !== 'undefined' && visualViewport) {
      visualViewport.addEventListener('resize', this.scheduleMapResize);
    }
  }

  private readonly scheduleMapResize = (): void => {
    this.map?.resize();
  };

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['riskKind'] && this.map?.getSource('risk-zones')) {
      this.mapGeoJsonService.switchRiskKind(this.map, this.riskKind);
      this.mapGeoJsonService.setRiskBandFilter(
        this.map,
        this.riskBandFilter,
        this.scoreThreshold,
        this.socialFilter,
      );
      this.mapGeoJsonService.setSelectedZone(this.map, this.selectedFeatureId);
      return;
    }
    if (
      (changes['riskBandFilter'] || changes['scoreThreshold'] || changes['socialFilter']) &&
      this.map
    ) {
      this.mapGeoJsonService.setRiskBandFilter(
        this.map,
        this.riskBandFilter,
        this.scoreThreshold,
        this.socialFilter,
      );
    }
    if (changes['selectedFeatureId'] && this.map) {
      this.mapGeoJsonService.setSelectedZone(this.map, this.selectedFeatureId);
    }
  }

  ngOnDestroy(): void {
    window.removeEventListener('resize', this.scheduleMapResize);
    window.removeEventListener('orientationchange', this.scheduleMapResize);
    if (typeof visualViewport !== 'undefined' && visualViewport) {
      visualViewport.removeEventListener('resize', this.scheduleMapResize);
    }
    this.map?.remove();
    this.map = null;
  }

  onZoomSliderChange(): void {
    this.map?.zoomTo(this.zoomLevel);
  }

  onZoomStep(delta: number): void {
    if (!this.map) return;
    const z = Math.min(this.maxZoom, Math.max(this.minZoom, this.map.getZoom() + delta));
    this.map.zoomTo(z, { duration: 220 });
  }

  private hasRiskZonesLayer(): boolean {
    return !!this.map?.getLayer('risk-zones-fill');
  }

  private syncZoomFromMap(): void {
    if (this.map) {
      this.zoomLevel = this.map.getZoom();
      this.cdr.markForCheck();
    }
  }

  private onMapMouseMove(e: MapMouseEvent): void {
    if (!this.map || !this.hasRiskZonesLayer()) return;
    const features = this.map.queryRenderedFeatures(e.point, {
      layers: ['risk-zones-fill'],
    });
    this.hoverX = e.point.x;
    this.hoverY = e.point.y;
    if (features.length) {
      const lat = e.lngLat.lat;
      const lng = e.lngLat.lng;
      this.hoveredCityName = `Lat: ${lat.toFixed(4)}, Lng: ${lng.toFixed(4)}`;
      this.map.getCanvas().style.cursor = 'pointer';
    } else {
      this.hoveredCityName = null;
      this.map.getCanvas().style.cursor = '';
    }
    this.cdr.markForCheck();
  }

  private onMapMouseLeave(): void {
    this.hoveredCityName = null;
    if (this.map?.getCanvas().style) this.map.getCanvas().style.cursor = '';
    this.cdr.markForCheck();
  }

  private onMapClick(e: MapMouseEvent): void {
    if (!this.map) return;
    if (!this.hasRiskZonesLayer()) {
      this.mapClick.emit({
        point: { x: e.point.x, y: e.point.y },
        feature: null,
        featureId: null,
        bbox: null,
        centerLng: e.lngLat.lng,
        centerLat: e.lngLat.lat,
      });
      return;
    }
    const features = this.map.queryRenderedFeatures(e.point, {
      layers: ['risk-zones-fill'],
    });
    if (features.length) {
      const f = features[0];
      const bbox = this.getFeatureBounds(f);
      const centerLng = bbox ? (bbox[0] + bbox[2]) / 2 : e.lngLat.lng;
      const centerLat = bbox ? (bbox[1] + bbox[3]) / 2 : e.lngLat.lat;
      const featureId = (f.properties?.['adidu'] as string) ?? null;
      if (bbox) {
        this.map.fitBounds(bbox, { padding: 40, maxZoom: 14, duration: 0 });
      }
      this.panSelectedZoneToViewportCenter(centerLng, centerLat);
      this.mapClick.emit({
        point: { x: e.point.x, y: e.point.y },
        feature: f,
        featureId: Number(featureId),
        bbox,
        centerLng,
        centerLat,
      });
    } else {
      this.mapClick.emit({
        point: { x: e.point.x, y: e.point.y },
        feature: null,
        featureId: null,
        bbox: null,
        centerLng: e.lngLat.lng,
        centerLat: e.lngLat.lat,
      });
    }
    this.cdr.markForCheck();
  }

  private panSelectedZoneToViewportCenter(centerLng: number, centerLat: number): void {
    if (!this.map) return;
    const el = this.map.getContainer();
    const w = el.clientWidth;
    const h = el.clientHeight;
    const targetX = w * MAP_ZONE_VIEWPORT_FRACTIONS.SELECTED_ZONE_SCREEN_X;
    const targetY = h * MAP_ZONE_VIEWPORT_FRACTIONS.SELECTED_ZONE_SCREEN_Y;
    const p = this.map.project([centerLng, centerLat]);
    this.map.panBy([p.x - targetX, p.y - targetY], { duration: 0 });
  }

  private getFeatureBounds(f: mapboxgl.GeoJSONFeature): [number, number, number, number] | null {
    const geom = f.geometry;
    if (geom.type !== 'Polygon' && geom.type !== 'MultiPolygon') return null;
    const exteriorRings =
      geom.type === 'Polygon' ? [geom.coordinates[0]] : geom.coordinates.map((p) => p[0]);
    let minLng = Infinity,
      minLat = Infinity,
      maxLng = -Infinity,
      maxLat = -Infinity;
    for (const ring of exteriorRings) {
      for (const c of ring) {
        minLng = Math.min(minLng, c[0]);
        minLat = Math.min(minLat, c[1]);
        maxLng = Math.max(maxLng, c[0]);
        maxLat = Math.max(maxLat, c[1]);
      }
    }
    if (minLng === Infinity) return null;
    return [minLng, minLat, maxLng, maxLat];
  }
}
