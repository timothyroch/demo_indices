import json
from pathlib import Path

from ..constants.filenames import RISK_ZONE_FILES

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
W_IRIU = 0.25

_zone_scores_cache: dict[str, dict[str, float]] = {}
_zone_props_cache: dict[str, dict[str, dict]] = {}


def get_zone_score(adidu: str, hazard_name: str) -> float:
    if hazard_name not in _zone_scores_cache:
        _zone_scores_cache[hazard_name] = _load_zone_scores(hazard_name)
    return _zone_scores_cache[hazard_name].get(adidu, 0.0)


def get_zone_properties(adidu: str, hazard_name: str) -> dict:
    """Get all properties of a zone for a specific hazard."""
    if hazard_name not in _zone_props_cache:
        _zone_props_cache[hazard_name] = _load_zone_properties(hazard_name)
    return _zone_props_cache[hazard_name].get(adidu, {})


def _load_zone_properties(hazard_name: str) -> dict[str, dict]:
    """Load all properties for zones of a specific hazard."""
    zone_props: dict[str, dict] = {}

    city_files = RISK_ZONE_FILES.get(hazard_name, {})
    for _, filename in city_files.items():
        path = _DATA_DIR / filename
        if not path.exists():
            continue

        with open(path, encoding="utf-8") as f:
            features = json.load(f).get("features", [])

        for feat in features:
            props = feat.get("properties", {})
            fid = props.get("ADIDU")
            if fid is not None:
                zone_props[str(fid)] = props

    return zone_props


def combined_probability(risk_score: float, proba_model: float) -> float:
    if round(proba_model, 4) == 0:
        return 0.0

    score_norm = max(0.0, min(100.0, risk_score)) / 100.0
    return (1 - W_IRIU) * proba_model + W_IRIU * score_norm


def combined_humidex(risk_score: float, humidex: float) -> float:
    if humidex <= 0:
        return 0.0

    score_norm = max(0.0, min(100.0, risk_score)) / 100.0
    return humidex * (1 + W_IRIU * score_norm)


def _load_zone_scores(hazard_name: str) -> dict[str, float]:
    zone_scores: dict[str, float] = {}

    city_files = RISK_ZONE_FILES.get(hazard_name, {})
    for _, filename in city_files.items():
        path = _DATA_DIR / filename
        if not path.exists():
            print(f"[load_zone_scores] Missing file: {path}")
            continue

        with open(path, encoding="utf-8") as f:
            features = json.load(f).get("features", [])

        for feat in features:
            props = feat.get("properties", {})
            fid = props.get("ADIDU")
            if fid is not None:
                zone_scores[str(fid)] = float(props.get("score_risque") or 0.0)

    return zone_scores
