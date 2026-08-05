def centroid_wgs84(geom: dict) -> tuple[float, float] | None:
    gtype = geom.get("type")
    coords = None
    if gtype == "Polygon":
        coords = geom["coordinates"][0]
    elif gtype == "MultiPolygon":
        coords = geom["coordinates"][0][0]
    if not coords:
        return None
    avg_lng = sum(c[0] for c in coords) / len(coords)
    avg_lat = sum(c[1] for c in coords) / len(coords)
    return (avg_lat, avg_lng)


def bounding_box(
    points: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    return min(lats), max(lats), min(lngs), max(lngs)


def build_regular_grid(
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    spacing_deg: float,
) -> list[tuple[float, float]]:
    lat_values: list[float] = []
    lat = min_lat
    while lat <= max_lat + spacing_deg:
        lat_values.append(lat)
        lat += spacing_deg

    lng_values: list[float] = []
    lng = min_lng
    while lng <= max_lng + spacing_deg:
        lng_values.append(lng)
        lng += spacing_deg

    return [(la, ln) for la in lat_values for ln in lng_values]
