import geopandas as gpd
import pandas as pd
import subprocess
from pathlib import Path

DATASET_DIR = Path(__file__).parent.parent / "dataset" / "vuln_sociales"
CSV_PATH    = DATASET_DIR / "98-401-X2021006_Quebec_fra_CSV" / "98-401-X2021006_Francais_CSV_data_Quebec.csv"
MONTREAL_CD = "2466"
CACHE_PATH  = Path("/tmp/montreal_indicateurs.csv")

# Indicateurs à extraire  (ID_CARACTÉRISTIQUE → nom de colonne)
INDICATEURS = {
    24:   "pop_65_plus",                      # Personnes âgées de 65 ans et plus (nb)
    27:   "_pop_75_79",                        # 75 à 79 ans (nb) — intermédiaire pour calcul 75+
    28:   "_pop_80_84",                        # 80 à 84 ans (nb) — intermédiaire pour calcul 75+
    29:   "_pop_85_plus",                      # 85 ans et plus (nb) — intermédiaire pour calcul 75+
    37:   "pct_65_plus",                       # Personnes âgées de 65 ans et plus (%)
    39:   "age_moyen",                         # Âge moyen de la population
    97:   "pop_vivant_seule",                  # Personnes vivant seules (nb)
    243:  "revenu_median_menage",              # Revenu total médian des ménages en 2020 ($)
    252:  "revenu_moyen_menage",               # Revenu total moyen des ménages en 2020 ($)
    379:  "gini",                              # Coefficient de Gini sur le revenu total rajusté des ménages
    1451: "logement_reparations_majeures",     # Réparations majeures requises (nb logements)
    1467: "logement_30pct_revenu",             # 30 % ou plus du revenu consacré aux frais de logement (nb ménages)
    1472: "logement_taille_non_convenable",    # Logement de taille non convenable seulement (nb ménages)
    2230: "taux_chomage",                      # Taux de chômage (%)
}

# 1. Charger et filtrer le shapefile pour Montréal uniquement
print("Chargement du shapefile...")
gdf_qc = gpd.read_file(DATASET_DIR / "lad_000b21a_f" / "lad_000b21a_f.shp")
gdf = gdf_qc[gdf_qc["ADIDU"].str.startswith(MONTREAL_CD)].copy()
print(f"  → {len(gdf)} aires de diffusion de Montréal")

# Noms de colonnes du CSV source
col_names = pd.read_csv(CSV_PATH, encoding="latin-1", nrows=0).columns.tolist()

# 2. Extraire toutes les lignes utiles en un seul passage (double grep, avec cache)
ids_pattern = "|".join(str(i) for i in INDICATEURS.keys())
if not CACHE_PATH.exists():
    print("Extraction des indicateurs via double grep (peut prendre ~2-3 min)...")
    p1 = subprocess.Popen(
        ["grep", "-aP", f'"2466[0-9]{{4}}","Aire de diffusion"', str(CSV_PATH)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    p2 = subprocess.Popen(
        ["grep", "-aP", f'"[0-9]+",({ids_pattern}),"'],
        stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    p1.stdout.close()
    output, _ = p2.communicate()
    p1.wait()
    CACHE_PATH.write_bytes(output)
    print(f"  → Cache sauvegardé dans {CACHE_PATH}")
else:
    print(f"Cache trouvé : {CACHE_PATH}")

# 3. Charger le cache et pivoter (une ligne par AD, une colonne par indicateur)
df = pd.read_csv(CACHE_PATH, encoding="latin-1", names=col_names, header=None, low_memory=False)
print(f"  → {len(df)} lignes chargées")

col_code = next(c for c in df.columns if "CODE" in c.upper() and "ALT" in c.upper())
col_id   = next(c for c in df.columns if "CARACT" in c.upper() and "ID" in c.upper() and "NOM" not in c.upper())
col_val  = next(c for c in df.columns if c.startswith("C1_"))

df[col_code] = df[col_code].astype(str).str.strip()
df[col_id]   = pd.to_numeric(df[col_id], errors="coerce")
df[col_val]  = pd.to_numeric(df[col_val], errors="coerce")

pivot = (
    df[df[col_id].isin(INDICATEURS.keys())]
    [[col_code, col_id, col_val]]
    .pivot_table(index=col_code, columns=col_id, values=col_val, aggfunc="first")
)
pivot.index.name = "ADIDU"
pivot.reset_index(inplace=True)
pivot.columns.name = None
pivot.rename(columns=INDICATEURS, inplace=True)

# Calcul de pop_75_plus = somme des 75-79, 80-84 et 85+ ans
intermediaires = ["_pop_75_79", "_pop_80_84", "_pop_85_plus"]
presents = [c for c in intermediaires if c in pivot.columns]
if presents:
    pivot["pop_75_plus"] = pivot[presents].sum(axis=1, skipna=False)
    pivot.drop(columns=presents, inplace=True)

# 4. Jointure avec la géométrie
gdf["ADIDU"] = gdf["ADIDU"].astype(str).str.strip()
gdf_result = gdf.merge(pivot, on="ADIDU", how="left")

print("\nRésultat (5 premières ADs) :")
cols_display = ["ADIDU"] + [c for c in INDICATEURS.values() if c in gdf_result.columns]
print(gdf_result[cols_display].dropna(subset=["age_moyen"]).head(5).to_string(index=False))

print("\nStatistiques Montréal :")
labels = [
    ("age_moyen",                     "Âge moyen (ans)"),
    ("pop_65_plus",                    "Personnes 65 ans et plus (nb, moy/AD)"),
    ("pct_65_plus",                    "Personnes 65 ans et plus (%)"),
    ("pop_75_plus",                    "Personnes 75 ans et plus (nb, moy/AD)"),
    ("revenu_median_menage",           "Revenu médian des ménages ($)"),
    ("revenu_moyen_menage",            "Revenu moyen des ménages ($)"),
    ("gini",                           "Coefficient de Gini"),
    ("taux_chomage",                   "Taux de chômage (%)"),
    ("pop_vivant_seule",               "Personnes vivant seules (nb, moy/AD)"),
    ("logement_30pct_revenu",          "Ménages ≥30 % revenu en logement (nb)"),
    ("logement_reparations_majeures",  "Logements nécessitant réparations majeures (nb)"),
    ("logement_taille_non_convenable", "Logements de taille non convenable (nb)"),
]
for col, label in labels:
    if col in gdf_result.columns:
        val = gdf_result[col].mean()
        print(f"  {label:<50} : {val:.1f}" if not pd.isna(val) else f"  {label:<50} : N/A")

# 5. Export CSV
OUTPUT_CSV = Path(__file__).parent.parent / "dataset" / "montreal_indicateurs_census.csv"
cols_export = ["ADIDU"] + [c for c in [
    "age_moyen", "pop_65_plus", "pct_65_plus", "pop_75_plus",
    "pop_vivant_seule",
    "revenu_median_menage", "revenu_moyen_menage", "gini", "taux_chomage",
    "logement_30pct_revenu", "logement_reparations_majeures", "logement_taille_non_convenable",
] if c in gdf_result.columns]
gdf_result[cols_export].to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
print(f"\nCSV exporté : {OUTPUT_CSV}  ({len(gdf_result)} lignes)")