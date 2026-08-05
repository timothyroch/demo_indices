export interface MapClickEvent {
  point: { x: number; y: number };
  feature: mapboxgl.GeoJSONFeature | null;
  featureId: number | null;
  bbox: [number, number, number, number] | null;
  centerLng: number;
  centerLat: number;
}
