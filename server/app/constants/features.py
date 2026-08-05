PLUVIAL_FLOODS_FEATURES = [
    "Temp moy.(°C)",
    "rain_1d",
    "rain_3d",
    "rain_5d",
    "rain_7d",
    "Temp_diff_2d",
    "Season",
    "rain_intensity",
    "is_freezing",
]

FLUVIAL_FLOODS_FEATURES = ["Water_Level", "WL_change_3d", "Rain_7d", "Temp_5d_mean"]
# ============================================================================
# RISK TYPES & ZONE MAPPINGS
# ============================================================================

RISK_TYPES = {
    "pluvial": "zones_risque_inondation",
    "crues": "zones_risque_crues",
    "canicules": "zones_risque_canicule",
    "neige": "zones_risque_sociale",
}

MAP_TYPES = ["pluvial", "crues", "canicules", "neige", "sociale"]


# ============================================================================
# RISK THRESHOLDS & BANDS
# ============================================================================

RISK_THRESHOLDS = {
    "vert": (0, 20),  # Vert: 0-20%
    "orange": (20, 50),  # Orange: 20-50%
    "rouge": (50, 100),  # Rouge: 50-100%
}

RISK_BANDS = ["vert", "orange", "rouge"]

# ============================================================================
# SOCIAL RISK TYPES
# ============================================================================

SOCIAL_RISK_KINDS = ["canicules", "crues", "neige", "sociale"]

# ============================================================================
# SOCIAL FILTER RANGES & DEFAULTS
# ============================================================================

SOCIAL_FILTER_RANGES = {
    "pct_65_plus": {"min": 0, "max": 100},
    "revenu_median_menage": {"min": 0, "max": 500000},
    "gini": {"min": 0, "max": 1},
    "logement_reparations_majeures": {"min": 0, "max": 100},
}

ISLAND_AVERAGES = {
    "pct_65_plus": 17.06,
    "revenu_median_menage": 75809,
    "gini": 0.3233,
    "logement_reparations_majeures": 23.78,
}
