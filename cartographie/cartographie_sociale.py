import geopandas as gpd
import pandas as pd
import webbrowser
from pathlib import Path
import folium
from folium import plugins
from shapely.strtree import STRtree
from shapely.geometry import box
import numpy as np

class SystemeExpertCanicule:
    """
    Système expert d'analyse de risques de canicule par zones.

    Géobase     : Aires de diffusion (Statistics Canada lad_000b21a_f)
    Couches territoriales :
      - Îlots de chaleur 2023  (températures satellite)
      - Canopée 2019           (couche protectrice — réduction du risque)
    Couche sociale :
      - Vulnérabilité sociale  (recensement 2021 — 4 indicateurs)

    Tous les indicateurs individuels sont conservés dans l'export GeoJSON.
    """

    def __init__(self):
        self.grille_base = None        # Géobase : aires de diffusion (DAs)
        self.couches_risque = {}
        self.zones_analysees = None
        self.spatial_indices = {}      # Index spatiaux R-Tree pour chaque couche volumineuse

    # ------------------------------------------------------------------
    # Chargement de la grille de base
    # ------------------------------------------------------------------

    def charger_grille_territoriale(self, chemin):
        """
        Charge la grille de base du territoire (îlots de minéralisation).
        Cette grille servira de base pour découper toutes les autres couches.
        """
        print("📍 Chargement de la grille territoriale...")
        self.grille_base = gpd.read_file(chemin)

        # Harmoniser le CRS
        if self.grille_base.crs != "EPSG:2950":
            print(f"   Conversion de {self.grille_base.crs} vers EPSG:2950...")
            self.grille_base = self.grille_base.to_crs(epsg=2950)

        # Identifiant unique stable pour les agrégations
        self.grille_base['zone_id'] = range(len(self.grille_base))

        # Surface de chaque zone (m²)
        self.grille_base['surface_m2'] = self.grille_base.geometry.area

        print(f"   ✓ {len(self.grille_base)} zones chargées")
        print(f"   ✓ Surface totale: {self.grille_base['surface_m2'].sum()/1_000_000:.2f} km²")
        return self

    # ------------------------------------------------------------------
    # Ajout d'une couche de risque
    # ------------------------------------------------------------------

    def ajouter_couche_risque(
        self,
        nom,
        chemin,
        colonne_valeur,
        poids=1.0,
        seuil_critique=None,
        use_spatial_index=False,
        protective=False,
    ):
        """
        Ajoute une couche de risque (ou de protection) à analyser.

        Args:
            nom              : Identifiant de la couche (ex: 'chaleur', 'canope')
            chemin           : Chemin vers le fichier GeoJSON ou Shapefile
            colonne_valeur   : Nom de la colonne contenant la valeur de risque,
                               ou None pour une couche présence/absence (ex: canopée)
            poids            : Pondération de cette couche (0-1)
            seuil_critique   : Valeur seuil pour le niveau critique (optionnel)
            use_spatial_index: Utiliser un index spatial R-Tree (recommandé pour gros fichiers)
            protective       : Si True, la couche RÉDUIT le risque (ex: canopée).
                               Contribution = val_norm × (1 - pct_surface) × poids
        """
        print(f"📊 Chargement de la couche '{nom}'...")
        couche = gpd.read_file(chemin)

        # Harmoniser le CRS
        if couche.crs != "EPSG:2950":
            couche = couche.to_crs(epsg=2950)

        # Surface des entités de la couche
        couche['surface_risque_m2'] = couche.geometry.area

        # Index spatial R-Tree si demandé
        spatial_index = None
        if use_spatial_index:
            print(f"   🔍 Création de l'index spatial R-Tree pour optimisation...")
            spatial_index = STRtree(couche.geometry)
            self.spatial_indices[nom] = spatial_index
            print(f"   ✓ Index spatial créé avec {len(couche)} géométries")

        self.couches_risque[nom] = {
            'data': couche,
            'colonne': colonne_valeur,
            'poids': poids,
            'seuil_critique': seuil_critique,
            'use_spatial_index': use_spatial_index,
            'protective': protective,
        }
        print(f"   ✓ {len(couche)} entités chargées")
        if protective:
            print(f"   ✓ Couche PROTECTRICE — réduit le risque de canicule")
        print(f"   ✓ Surface totale: {couche['surface_risque_m2'].sum()/1_000_000:.2f} km²")
        return self

    # ------------------------------------------------------------------
    # Vulnérabilité sociale (jointure aires de diffusion ↔ CSV recensement)
    # ------------------------------------------------------------------

    def ajouter_vulnerabilite_sociale(self, chemin_csv, poids=0.50):
        """
        Joint les données sociales du recensement directement sur la géobase
        (les aires de diffusion SONT la géobase, donc pas de jointure spatiale).

        4 indicateurs normalisés min-max sur 0–1 :
          • revenu_median_menage          — bas revenu → risque élevé  (inversé)
          • gini                          — inégalité élevée → risque élevé
          • pct_65_plus                   — proportion 65+ → risque élevé
          • logement_reparations_majeures — logements dégradés → risque élevé

        Tous les indicateurs bruts ET normalisés sont gardés dans la géobase
        pour export dans le GeoJSON final.

        Args:
            chemin_csv : Chemin vers montreal_indicateurs_census.csv
            poids      : Poids de la couche dans le score composite
        """
        if self.grille_base is None:
            raise ValueError("Chargez d'abord la grille avec charger_grille_territoriale()")

        print("📊 Chargement de la couche 'vuln_sociale'...")

        cols_utiles = [
            'ADIDU', 'revenu_median_menage', 'gini',
            'pct_65_plus', 'logement_reparations_majeures',
        ]
        df = pd.read_csv(chemin_csv, usecols=cols_utiles)

        # Harmoniser les types pour la jointure
        self.grille_base['ADIDU'] = self.grille_base['ADIDU'].astype(str).str.strip()
        df['ADIDU'] = df['ADIDU'].astype(str).str.strip()

        # Jointure attributaire directe (DAs = géobase)
        # inner join : on filtre immédiatement aux DAs de Montréal qui ont des données
        indicateurs = ['revenu_median_menage', 'gini', 'pct_65_plus', 'logement_reparations_majeures']
        df = df.dropna(subset=indicateurs)
        avant = len(self.grille_base)
        self.grille_base = self.grille_base.merge(df, on='ADIDU', how='inner')
        # Recalculer zone_id et surface_m2 après le filtre
        self.grille_base = self.grille_base.reset_index(drop=True)
        self.grille_base['zone_id'] = range(len(self.grille_base))
        self.grille_base['surface_m2'] = self.grille_base.geometry.area
        print(f"   ✓ {len(self.grille_base)}/{avant} aires de diffusion conservées (Montréal)")
        print(f"   📊 Indicateurs sociaux — moyennes Montréal :")
        print(f"      • revenu_median_menage              : {self.grille_base['revenu_median_menage'].mean():>10,.0f} $")
        print(f"      • gini                              : {self.grille_base['gini'].mean():>10.3f}")
        print(f"      • pct_65_plus                       : {self.grille_base['pct_65_plus'].mean():>10.1f} %")
        print(f"      • logement_reparations_majeures (nb): {self.grille_base['logement_reparations_majeures'].mean():>10.1f}")

        # ── Normalisation min-max 0–1 (sur les DAs avec données) ──
        def _norm(serie, inverser=False):
            vmin, vmax = serie.min(), serie.max()
            scaled = (serie - vmin) / (vmax - vmin + 1e-9)
            return (1.0 - scaled) if inverser else scaled

        self.grille_base['score_revenu']   = _norm(self.grille_base['revenu_median_menage'], inverser=True)
        self.grille_base['score_gini']     = _norm(self.grille_base['gini'])
        self.grille_base['score_age']      = _norm(self.grille_base['pct_65_plus'])
        self.grille_base['score_logement'] = _norm(self.grille_base['logement_reparations_majeures'])

        # Score composite social : moyenne équipondérée
        self.grille_base['score_vuln_sociale'] = (
            self.grille_base['score_revenu'] +
            self.grille_base['score_gini']   +
            self.grille_base['score_age']    +
            self.grille_base['score_logement']
        ) / 4.0

        score_valides = self.grille_base['score_vuln_sociale'].dropna()
        print(f"   ✓ Score social calculé "
              f"(min: {score_valides.min():.3f}, "
              f"moy: {score_valides.mean():.3f}, "
              f"max: {score_valides.max():.3f})")

        # ── Enregistrer comme couche (colonne déjà sur la grille → Cas 1 dans analyser) ──
        # On passe un GeoDataFrame factice — analyser() utilisera la colonne directement
        self.couches_risque['vuln_sociale'] = {
            'data'              : self.grille_base[['zone_id', 'geometry', 'score_vuln_sociale']],
            'colonne'           : 'score_vuln_sociale',
            'poids'             : poids,
            'seuil_critique'    : None,
            'use_spatial_index' : False,
            'protective'        : False,
        }
        return self

    # ------------------------------------------------------------------
    # Analyse spatiale principale
    # ------------------------------------------------------------------

    def analyser(self):
        """
        Analyse spatiale par zone :
          1. Pour chaque cellule de la grille, calcule le % de surface affectée
             par chaque couche de risque (ou de protection).
          2. Agrège les contributions pour obtenir un score composite par zone.
        """
        if self.grille_base is None:
            raise ValueError(
                "Chargez d'abord la grille territoriale avec charger_grille_territoriale()"
            )

        print("\n🔬 Analyse spatiale par zones en cours...")

        resultat = self.grille_base.copy()

        for nom, config in self.couches_risque.items():
            print(f"\n   📍 Analyse de la couche '{nom}'...")
            couche = config['data']
            colonne = config['colonne']
            poids = config['poids']
            protective = config.get('protective', False)

            # ── Cas 1 : colonne déjà dans la grille (fichier identique à la base) ──
            if colonne is not None and colonne in resultat.columns:
                print(f"      ℹ️  Colonne déjà présente — utilisation directe")
                resultat[f'val_{nom}'] = resultat[colonne]
                resultat[f'surface_{nom}_m2'] = resultat['surface_m2']
                resultat[f'pct_{nom}'] = 100.0
                resultat[f'poids_{nom}'] = poids
                print(f"      ✓ {len(resultat)} zones analysées directement")
                continue

            # ── Intersection spatiale ──
            if config.get('use_spatial_index', False):
                print(f"      ⚡ Intersection spatiale OPTIMISÉE avec R-Tree...")
                intersection = self._intersection_optimisee(resultat, couche, nom)
            else:
                print(f"      ⏳ Intersection spatiale en cours...")
                intersection = gpd.overlay(resultat, couche, how='intersection')

            if len(intersection) == 0:
                print(f"      ℹ️  Aucune intersection trouvée pour '{nom}'")
                continue

            # Surface de l'intersection
            intersection['surface_intersection_m2'] = intersection.geometry.area

            # ── Cas 2 : couche présence/absence (colonne=None, ex: canopée) ──
            if colonne is None:
                # On utilise uniquement le % de surface couverte pour quantifier la protection
                agregation = (
                    intersection
                    .groupby('zone_id')['surface_intersection_m2']
                    .sum()
                    .reset_index()
                )
                agregation.columns = ['zone_id', f'surface_{nom}_m2']
                resultat = resultat.merge(agregation, on='zone_id', how='left')
                resultat[f'surface_{nom}_m2'] = resultat[f'surface_{nom}_m2'].fillna(0)
                resultat[f'pct_{nom}'] = (
                    resultat[f'surface_{nom}_m2'] / resultat['surface_m2'] * 100
                ).fillna(0)
                resultat[f'val_{nom}'] = 1.0   # Valeur unitaire (présence = 1)
                resultat[f'poids_{nom}'] = poids
                nb_zones = (resultat[f'pct_{nom}'] > 0).sum()
                print(f"      ✓ {nb_zones} zones avec couverture canopée")
                print(f"      ✓ Surface couverte: {resultat[f'surface_{nom}_m2'].sum()/1_000_000:.2f} km²")
                continue

            # ── Cas 3 : couche avec une colonne de valeur ──
            if colonne in intersection.columns:
                intersection[f'val_{nom}'] = intersection[colonne]

                def max_severity(series):
                    if pd.api.types.is_numeric_dtype(series):
                        return series.mean()
                    scores = self._categoriser_valeurs(series, nom)
                    return series.loc[scores.idxmax()]

                agregation = (
                    intersection
                    .groupby('zone_id')
                    .agg({
                        'surface_intersection_m2': 'sum',
                        f'val_{nom}': max_severity,
                    })
                    .reset_index()
                )
                agregation.columns = ['zone_id', f'surface_{nom}_m2', f'val_{nom}']
                resultat = resultat.merge(agregation, on='zone_id', how='left')

                resultat[f'pct_{nom}'] = (
                    resultat[f'surface_{nom}_m2'] / resultat['surface_m2'] * 100
                ).fillna(0)
                resultat[f'poids_{nom}'] = poids

                print(f"      ✓ {len(intersection)} zones affectées")
                print(
                    f"      ✓ Surface totale affectée: "
                    f"{resultat[f'surface_{nom}_m2'].sum()/1_000_000:.2f} km²"
                )
            else:
                print(f"      ⚠  Colonne '{colonne}' non trouvée dans la couche '{nom}'")

        self.zones_analysees = resultat

        # Score composite
        self._calculer_score_risque()

        print(f"\n✅ Analyse terminée : {len(self.zones_analysees)} zones analysées")
        return self

    # ------------------------------------------------------------------
    # Score de risque
    # ------------------------------------------------------------------

    def _calculer_score_risque(self):
        """
        Calcule le score de risque de canicule composite par zone.

        Formule :
            score = Σ risk_i + Σ protection_j
        où
            risk_i       = val_norm_i × (pct_i / 100) × poids_i
            protection_j = val_norm_j × (1 - pct_j / 100) × poids_j   ← couche protective

        Score final normalisé sur 0-100, puis catégorisé en Faible/Modéré/Élevé/Critique.
        """
        if self.zones_analysees is None:
            return

        print("\n🎯 Calcul du score de risque de canicule...")

        score = pd.Series(0.0, index=self.zones_analysees.index)
        poids_total = 0

        for nom, config in self.couches_risque.items():
            col_val = f'val_{nom}'
            col_pct = f'pct_{nom}'
            protective = config.get('protective', False)

            if col_val not in self.zones_analysees.columns:
                continue
            if col_pct not in self.zones_analysees.columns:
                continue

            valeurs = self.zones_analysees[col_val].fillna(0)
            pct_surface = self.zones_analysees[col_pct].fillna(0) / 100  # 0→1

            # Normaliser les valeurs numériques sur 0–1
            if pd.api.types.is_numeric_dtype(valeurs):
                vmax = valeurs.max()
                val_norm = valeurs / vmax if vmax > 0 else valeurs
            else:
                val_norm = self._categoriser_valeurs(valeurs, nom)

            poids = config['poids']

            if protective:
                # La canopée RÉDUIT le risque : absence de canopée = risque
                score += val_norm * (1 - pct_surface) * poids
            else:
                score += val_norm * pct_surface * poids

            poids_total += poids

        # Normaliser sur 0-100
        if poids_total > 0:
            self.zones_analysees['score_risque'] = (score / poids_total) * 100

            self.zones_analysees['niveau_risque'] = pd.cut(
                self.zones_analysees['score_risque'],
                bins=[-0.01, 10, 30, 60, 100],
                labels=['Faible', 'Modéré', 'Élevé', 'Critique'],
            )

            print(
                f"   ✓ Score calculé (min: {self.zones_analysees['score_risque'].min():.1f}, "
                f"max: {self.zones_analysees['score_risque'].max():.1f})"
            )
            zones_critiques = self.zones_analysees[
                self.zones_analysees['niveau_risque'] == 'Critique'
            ]
            print(f"   ⚠️  {len(zones_critiques)} zones en risque CRITIQUE de canicule")

    # ------------------------------------------------------------------
    # Intersection optimisée (R-Tree)
    # ------------------------------------------------------------------

    def _intersection_optimisee(self, grille, couche, nom_couche):
        """
        Intersection spatiale optimisée avec R-Tree pour fichiers volumineux.
        Inclut validation et réparation automatique des géométries invalides.
        """
        spatial_index = self.spatial_indices.get(nom_couche)
        if spatial_index is None:
            return gpd.overlay(grille, couche, how='intersection')

        intersections = []
        total_cells = len(grille)
        errors_count = 0

        for idx, cell in grille.iterrows():
            if idx % 500 == 0:
                print(f"         Traitement cellule {idx+1}/{total_cells}...")

            cell_geom = cell.geometry
            if not cell_geom.is_valid:
                cell_geom = cell_geom.buffer(0)

            potential_matches_idx = spatial_index.query(cell_geom)
            if len(potential_matches_idx) == 0:
                continue

            for match_idx in potential_matches_idx:
                poly_geom = couche.geometry.iloc[match_idx]
                if not poly_geom.is_valid:
                    poly_geom = poly_geom.buffer(0)

                try:
                    if cell_geom.intersects(poly_geom):
                        inter_geom = cell_geom.intersection(poly_geom)
                        if not inter_geom.is_empty:
                            result_row = cell.to_dict()
                            result_row.update(couche.iloc[match_idx].to_dict())
                            result_row['geometry'] = inter_geom
                            intersections.append(result_row)
                except Exception:
                    errors_count += 1
                    if errors_count == 1:
                        print(
                            "         ⚠️  Géométries invalides détectées — "
                            "tentative de réparation automatique..."
                        )
                    continue

        if errors_count > 0:
            print(
                f"         ℹ️  {errors_count} intersections ignorées "
                "(géométries invalides)"
            )

        if not intersections:
            return gpd.GeoDataFrame()

        return gpd.GeoDataFrame(intersections, crs=grille.crs)

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _categoriser_valeurs(self, serie, nom_couche):
        """Convertit les valeurs catégorielles en scores numériques 0-1."""
        scores = pd.Series(0.5, index=serie.index)
        # Les fichiers de sensibilité utilisent des scores 0-5 → normaliser
        if nom_couche in [
            'chaleur', 'secheresses',
            'sens_terr_crues', 'sens_terr_pluies',
            'sens_social_crues', 'sens_social_pluies',
        ]:
            scores = serie / 5.0
        return scores

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def visualiser(self, fichier_sortie="carte_canicule.html"):
        """Crée une carte interactive choroplèthe des zones à risque de canicule.
        Chaque aire de diffusion est colorée selon son niveau de risque.
        """
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")

        print(f"\n🗺️  Création de la carte interactive ({len(self.zones_analysees)} zones)...")

        couleurs = {
            'Faible':   '#2ecc71',
            'Modéré':   '#f39c12',
            'Élevé':    '#e74c3c',
            'Critique': '#8b0000',
        }

        # Colonnes à inclure dans le GeoJSON de la carte (tooltip)
        cols_carte = ['zone_id', 'ADIDU', 'niveau_risque', 'score_risque',
                      'score_vuln_sociale', 'pct_65_plus', 'revenu_median_menage',
                      'gini', 'geometry']
        cols_carte = [c for c in cols_carte if c in self.zones_analysees.columns]

        zones_wgs84 = (
            self.zones_analysees[cols_carte]
            .copy()
            .to_crs(epsg=4326)
        )
        # Simplifier légèrement pour alléger le HTML
        zones_wgs84['geometry'] = zones_wgs84['geometry'].simplify(
            tolerance=0.00005, preserve_topology=True
        )
        # niveau_risque est de type Categorical → convertir en str pour JSON
        zones_wgs84['niveau_risque'] = zones_wgs84['niveau_risque'].astype(str)

        # Centre de la carte
        centre = [
            zones_wgs84.geometry.centroid.y.mean(),
            zones_wgs84.geometry.centroid.x.mean(),
        ]

        m = folium.Map(location=centre, zoom_start=11, tiles='OpenStreetMap')

        # Un seul layer GeoJson — chaque feature est colorée par son niveau de risque
        print(f"   🎨 Application du style choroplèthe par aire de diffusion...")

        def style_function(feature):
            niveau = feature['properties'].get('niveau_risque', 'Modéré')
            couleur = couleurs.get(niveau, '#999999')
            return {
                'fillColor': couleur,
                'color': '#333333',
                'weight': 0.4,
                'fillOpacity': 0.65,
            }

        folium.GeoJson(
            zones_wgs84.__geo_interface__,
            name='Risque canicule',
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=[f for f in
                        ['ADIDU', 'niveau_risque', 'score_risque',
                         'score_vuln_sociale', 'pct_65_plus', 'revenu_median_menage']
                        if f in zones_wgs84.columns],
                aliases=[f for f, a in [
                    ('ADIDU',               'Aire de diffusion'),
                    ('niveau_risque',        'Niveau de risque'),
                    ('score_risque',         'Score (0-100)'),
                    ('score_vuln_sociale',   'Score social'),
                    ('pct_65_plus',          '65+ (%)'),
                    ('revenu_median_menage', 'Revenu médian ($)'),
                ] if f in zones_wgs84.columns],
                localize=True,
            ),
        ).add_to(m)

        # Légende manuelle
        legende_html = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                    background:white;padding:10px 14px;border-radius:6px;
                    border:1px solid #aaa;font-size:13px;line-height:1.8;">
          <b>Risque canicule</b><br>
          <span style="background:#2ecc71;display:inline-block;width:14px;height:14px;margin-right:6px;"></span>Faible<br>
          <span style="background:#f39c12;display:inline-block;width:14px;height:14px;margin-right:6px;"></span>Modéré<br>
          <span style="background:#e74c3c;display:inline-block;width:14px;height:14px;margin-right:6px;"></span>Élevé<br>
          <span style="background:#8b0000;display:inline-block;width:14px;height:14px;margin-right:6px;"></span>Critique
        </div>"""
        m.get_root().html.add_child(folium.Element(legende_html))

        folium.LayerControl().add_to(m)

        print(f"   💾 Sauvegarde de la carte...")
        m.save(fichier_sortie)
        print(f"   ✓ Carte sauvegardée : {fichier_sortie}")
        return m

    # ------------------------------------------------------------------
    # Export & statistiques
    # ------------------------------------------------------------------

    def exporter_resultats(self, fichier_sortie="zones_risque_canicule.geojson"):
        """Exporte les résultats en GeoJSON."""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        self.zones_analysees.to_file(fichier_sortie, driver='GeoJSON')
        print(f"\n💾 Résultats exportés : {fichier_sortie}")

    def statistiques(self):
        """Affiche des statistiques sur l'analyse de canicule."""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")

        print("\n📈 STATISTIQUES DE L'ANALYSE DE CANICULE")
        print("=" * 60)

        stats = self.zones_analysees.groupby('niveau_risque').agg({
            'surface_m2': ['sum', 'count'],
            'score_risque': ['mean', 'min', 'max'],
        }).round(2)
        print("\nRépartition des zones par niveau de risque :")
        print(stats)

        surface_totale = self.zones_analysees['surface_m2'].sum()
        print(f"\nSurface totale analysée : {surface_totale:,.0f} m²  ({surface_totale/1_000_000:.2f} km²)")

        zones_critiques = self.zones_analysees[
            self.zones_analysees['niveau_risque'].isin(['Élevé', 'Critique'])
        ]
        surface_critique = zones_critiques['surface_m2'].sum()
        pct_critique = (surface_critique / surface_totale) * 100 if surface_totale > 0 else 0

        print(f"\n⚠️  ZONES À RISQUE ÉLEVÉ / CRITIQUE :")
        print(f"   • Nombre  : {len(zones_critiques)} zones")
        print(f"   • Surface : {surface_critique:,.0f} m²  ({surface_critique/1_000_000:.2f} km²)")
        print(f"   • Part du territoire : {pct_critique:.1f} %")


# ============================================================
# EXEMPLE D'UTILISATION — ANALYSE RISQUE CANICULE MONTRÉAL
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🌡️  ANALYSE RISQUE CANICULE — GÉOBASE : AIRES DE DIFFUSION")
    print("=" * 70)
    print("Géobase      : Aires de diffusion Statistics Canada (lad_000b21a_f)")
    print("Couches      : îlots de chaleur · canopée 2019 (protectrice)")
    print("              · vulnérabilité sociale (4 indicateurs recensement 2021)")
    print("Pondération  : îlots chaleur 30 % · canopée 20 % · social 50 %")
    print()

    systeme = SystemeExpertCanicule()

    base_path = Path(__file__).parent.parent / "dataset"

    # ── GÉOBASE : aires de diffusion ──────────────────────────────────────
    systeme.charger_grille_territoriale(
        str(base_path / 'vuln_sociales/lad_000b21a_f/lad_000b21a_f.shp')
    )

    # ── COUCHE SOCIALE ────────────────────────────────────────────────────
    # Joint directement sur la géobase (DAs = géobase → pas d'overlay spatial)
    # Tous les indicateurs bruts + normalisés sont conservés dans le GeoJSON.
    systeme.ajouter_vulnerabilite_sociale(
        chemin_csv=str(base_path / 'montreal_indicateurs_census.csv'),
        poids=1,
    )


    # ── ANALYSE & EXPORTS ────────────────────────────────────────────────
    systeme.analyser()
    systeme.statistiques()
    systeme.visualiser("carte_sociale.html")
    systeme.exporter_resultats("zones_risque_sociale.geojson")

    print("\n✅ Analyse terminée avec succès !")
    print("📂 Fichiers générés :")
    print("   • carte_sociale.html")
    print("   • zones_risque_sociale.geojson  (tous indicateurs inclus)")

    webbrowser.open("carte_sociale.html")
