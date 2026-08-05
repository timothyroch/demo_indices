import geopandas as gpd
import pandas as pd
import webbrowser
from pathlib import Path
import folium
from folium import plugins
from shapely.strtree import STRtree
from shapely.geometry import box
import numpy as np

class SystemeExpertInondation:
    """
    Système expert d'analyse de risques d'inondation par zones
    en croisant plusieurs couches de vulnérabilité territoriale
    """
    
    def __init__(self):
        self.grille_base = None  # Grille de découpage du territoire
        self.couches_risque = {}
        self.zones_analysees = None
        self.spatial_indices = {}  # Index spatiaux R-Tree pour chaque couche
        self._intersection_cache = {}  # Intersections brutes pour visualisation détaillée
        
    def charger_grille_territoriale(self, chemin):
        """
        Charge la grille de base du territoire (îlots, quartiers, etc.)
        Cette grille servira de base pour découper les zones à risque
        """
        print("📍 Chargement de la grille territoriale...")
        self.grille_base = gpd.read_file(chemin)
        
        # Harmoniser le CRS
        if self.grille_base.crs != "EPSG:2950":
            print(f"   Conversion de {self.grille_base.crs} vers EPSG:2950...")
            self.grille_base = self.grille_base.to_crs(epsg=2950)
        
        # Ajouter un identifiant unique stable pour les agrégations
        self.grille_base['zone_id'] = range(len(self.grille_base))
        
        # Calculer la surface de chaque zone
        self.grille_base['surface_m2'] = self.grille_base.geometry.area
        
        print(f"   ✓ {len(self.grille_base)} zones chargées")
        print(f"   ✓ Surface totale: {self.grille_base['surface_m2'].sum()/1_000_000:.2f} km²")
        return self
    
    def ajouter_couche_risque(self, nom, chemin, colonne_valeur, poids=1.0, seuil_critique=None, use_spatial_index=False):
        """
        Ajoute une couche de risque à analyser
        
        Args:
            nom: Identifiant de la couche (ex: 'crues', 'cuvettes', 'ruissellement')
            chemin: Chemin vers le fichier GeoJSON ou Shapefile
            colonne_valeur: Nom de la colonne contenant la valeur de risque
            poids: Pondération de cette couche (0-1)
            seuil_critique: Valeur au-dessus de laquelle le risque est critique
            use_spatial_index: Utiliser un index spatial R-Tree pour optimiser les requêtes (fichiers lourds)
        """
        print(f"📊 Chargement de la couche '{nom}'...")
        couche = gpd.read_file(chemin)
        
        # Harmoniser le CRS
        if couche.crs != "EPSG:2950":
            couche = couche.to_crs(epsg=2950)
        
        # Calculer la surface des zones à risque
        couche['surface_risque_m2'] = couche.geometry.area
        
        # Créer un index spatial si demandé (optimisation pour gros fichiers)
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
            'use_spatial_index': use_spatial_index
        }
        print(f"   ✓ {len(couche)} zones de risque chargées")
        print(f"   ✓ Surface totale à risque: {couche['surface_risque_m2'].sum()/1_000_000:.2f} km²")
        return self
    
    def analyser(self):
        """
        Analyse spatiale par zones :
        1. Pour chaque cellule de la grille, calcule le % de surface affectée par chaque risque
        2. Agrège les risques pour obtenir un score composite par zone
        3. Identifie les zones critiques (stationnements, bâtiments, etc.)
        """
        if self.grille_base is None:
            raise ValueError("Chargez d'abord la grille territoriale avec charger_grille_territoriale()")
        
        print("\n🔬 Analyse spatiale par zones en cours...")
        
        # Copier la grille de base
        resultat = self.grille_base.copy()
        
        # Pour chaque couche de risque
        for nom, config in self.couches_risque.items():
            print(f"\n   📍 Analyse de la couche '{nom}'...")
            couche = config['data']
            colonne = config['colonne']
            poids = config['poids']
            
            # Vérifier si la colonne existe déjà dans la grille (même fichier)
            if colonne in resultat.columns:
                print(f"      ℹ️  Colonne déjà présente - utilisation directe")
                resultat[f'val_{nom}'] = resultat[colonne]
                resultat[f'surface_{nom}_m2'] = resultat['surface_m2']  # 100% de la surface
                resultat[f'pct_{nom}'] = 100.0  # 100% affecté
                resultat[f'poids_{nom}'] = poids
                print(f"      ✓ {len(resultat)} zones analysées directement")
                continue
            
            # Sinon, faire une intersection spatiale optimisée
            if config.get('use_spatial_index', False):
                print(f"      ⚡ Intersection spatiale OPTIMISÉE avec R-Tree...")
                intersection = self._intersection_optimisee(resultat, couche, nom)
            else:
                print(f"      ⏳ Intersection spatiale en cours...")
                intersection = gpd.overlay(resultat, couche, how='intersection')
            
            if len(intersection) > 0:
                # Calculer la surface de l'intersection
                intersection['surface_intersection_m2'] = intersection.geometry.area
                
                # Grouper par zone de la grille pour agréger les risques
                # (une zone peut chevaucher plusieurs polygones de risque)
                
                if colonne in intersection.columns:
                    # Extraire les valeurs de risque
                    intersection[f'val_{nom}'] = intersection[colonne]

                    # Mettre en cache l'intersection brute (utile pour visualisation croisée)
                    self._intersection_cache[nom] = intersection.copy()
                    
                    # Calculer le pourcentage de surface affectée par zone
                    # Pour chaque cellule de grille, prendre la CLASSE LA PLUS SÉVÈRE
                    def max_severity(series):
                        """Retourne la classe la plus sévère (score le plus élevé)"""
                        # Convertir les valeurs catégorielles en scores
                        if pd.api.types.is_numeric_dtype(series):
                            return series.mean()
                        else:
                            # Utiliser le système de scoring pour obtenir la classe la plus sévère
                            scores = self._categoriser_valeurs(series, nom)
                            return series.loc[scores.idxmax()]
                    
                    agregation = intersection.groupby('zone_id').agg({
                        'surface_intersection_m2': 'sum',
                        f'val_{nom}': max_severity  # Classe la plus sévère (score max)
                    }).reset_index()
                    
                    # Fusionner avec le résultat
                    agregation.columns = ['zone_id', f'surface_{nom}_m2', f'val_{nom}']
                    resultat = resultat.merge(agregation, on='zone_id', how='left')
                    
                    # Calculer le % de surface affectée
                    resultat[f'pct_{nom}'] = (resultat[f'surface_{nom}_m2'] / resultat['surface_m2'] * 100).fillna(0)
                    resultat[f'poids_{nom}'] = poids
                    
                    print(f"      ✓ {len(intersection)} zones affectées")
                    print(f"      ✓ Surface totale affectée: {resultat[f'surface_{nom}_m2'].sum()/1_000_000:.2f} km²")
                else:
                    print(f"      ⚠ Colonne '{colonne}' non trouvée")
        
        self.zones_analysees = resultat
        
        # Calculer le score composite
        self._calculer_score_risque()
        
        print(f"\n✅ Analyse terminée : {len(self.zones_analysees)} zones analysées")
        return self
    
    def _calculer_score_risque(self):
        """
        Calcule le score de risque d'inondation composite par zone
        
        Formule : Score = Σ (valeur_risque × % surface affectée × poids) - Σ (valeur_protection × % surface protégée × poids)
        
        Exemple concret :
        Zone A (10 000 m²) :
        - 30% de sa surface (3000m²) est en zone de crue élevée (valeur=0.8, poids=0.5) → risque
        - 50% de sa surface (5000m²) a des grandes cuvettes (valeur=0.8, poids=0.3) → protection
        
        Score = (0.8 × 0.30 × 0.5) - (0.8 × 0.50 × 0.3) = 0.12 - 0.12 = 0 → protection compense le risque
        """
        if self.zones_analysees is None:
            return
        
        print("\n🎯 Calcul du score de risque d'inondation...")
        
        score = 0
        poids_total = 0
        
        for nom, config in self.couches_risque.items():
            col_val = f'val_{nom}'
            col_pct = f'pct_{nom}'
            
            if col_val in self.zones_analysees.columns and col_pct in self.zones_analysees.columns:
                valeurs = self.zones_analysees[col_val].fillna(0)
                pct_surface = self.zones_analysees[col_pct].fillna(0) / 100  # Convertir en 0-1
                
                # Normaliser les valeurs si numériques
                if pd.api.types.is_numeric_dtype(valeurs):
                    if valeurs.max() > 0:
                        val_norm = valeurs / valeurs.max()
                    else:
                        val_norm = valeurs
                else:
                    val_norm = self._categoriser_valeurs(valeurs, nom)
                
                poids = config['poids']
                
                # Score pondéré par la surface affectée
                score += val_norm * pct_surface * poids
                poids_total += poids
        
        # Score final normalisé entre 0 et 100
        if poids_total > 0:
            self.zones_analysees['score_risque'] = (score / poids_total) * 100
            
            # Catégoriser le risque
            self.zones_analysees['niveau_risque'] = pd.cut(
                self.zones_analysees['score_risque'],
                bins=[-0.01, 10, 30, 60, 100],
                labels=['Faible', 'Modéré', 'Élevé', 'Critique']
            )
            
            print(f"   ✓ Score calculé (min: {self.zones_analysees['score_risque'].min():.1f}, "
                  f"max: {self.zones_analysees['score_risque'].max():.1f})")
            
            # Identifier les zones critiques
            zones_critiques = self.zones_analysees[
                self.zones_analysees['niveau_risque'] == 'Critique'
            ]
            print(f"   ⚠️  {len(zones_critiques)} zones en risque CRITIQUE d'inondation")
    
    def ajouter_vulnerabilite_sociale(self, chemin_csv, poids=0.30):
        """
        Joint les données sociales du recensement directement sur la géobase
        (les aires de diffusion SONT la géobase, donc pas de jointure spatiale).

        4 indicateurs normalisés min-max sur 0–1 :
          • revenu_median_menage          — bas revenu → risque élevé  (inversé)
          • gini                          — inégalité élevée → risque élevé
          • pct_65_plus                   — proportion 65+ → risque élevé
          • logement_reparations_majeures — logements dégradés → risque élevé

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

        # Normalisation min-max 0–1
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

        # Enregistrer comme couche
        self.couches_risque['vuln_sociale'] = {
            'data'              : self.grille_base[['zone_id', 'geometry', 'score_vuln_sociale']],
            'colonne'           : 'score_vuln_sociale',
            'poids'             : poids,
            'seuil_critique'    : None,
            'use_spatial_index' : False,
        }
        return self

    def _intersection_optimisee(self, grille, couche, nom_couche):
        """
        Intersection spatiale optimisée avec R-Tree pour fichiers volumineux.
        Ne charge en mémoire que les polygones qui intersectent réellement chaque cellule.
        Inclut la validation et réparation automatique des géométries invalides.
        """
        spatial_index = self.spatial_indices.get(nom_couche)
        if spatial_index is None:
            # Fallback si pas d'index
            return gpd.overlay(grille, couche, how='intersection')
        
        intersections = []
        total_cells = len(grille)
        errors_count = 0
        
        for idx, cell in grille.iterrows():
            if idx % 100 == 0:  # Progress indicator
                print(f"         Traitement cellule {idx+1}/{total_cells}...")
            
            # Récupérer uniquement les polygones qui intersectent cette cellule
            cell_geom = cell.geometry
            
            # Valider et réparer la géométrie de la cellule si nécessaire
            if not cell_geom.is_valid:
                cell_geom = cell_geom.buffer(0)
            
            potential_matches_idx = spatial_index.query(cell_geom)
            
            if len(potential_matches_idx) == 0:
                continue
            
            # Vérifier l'intersection réelle et calculer la surface
            for match_idx in potential_matches_idx:
                poly_geom = couche.geometry.iloc[match_idx]
                
                # Valider et réparer la géométrie du polygone si nécessaire
                if not poly_geom.is_valid:
                    poly_geom = poly_geom.buffer(0)
                
                try:
                    if cell_geom.intersects(poly_geom):
                        inter_geom = cell_geom.intersection(poly_geom)
                        
                        if not inter_geom.is_empty:
                            # Créer une ligne de résultat avec les attributs des deux couches
                            result_row = cell.to_dict()
                            result_row.update(couche.iloc[match_idx].to_dict())
                            result_row['geometry'] = inter_geom
                            intersections.append(result_row)
                except Exception as e:
                    # En cas d'erreur topologique, passer à la suivante
                    errors_count += 1
                    if errors_count == 1:  # N'afficher qu'une fois
                        print(f"         ⚠️  Géométries invalides détectées - tentative de réparation automatique...")
                    continue
        
        if errors_count > 0:
            print(f"         ℹ️  {errors_count} intersections ignorées en raison de géométries invalides")
        
        if not intersections:
            return gpd.GeoDataFrame()
        
        return gpd.GeoDataFrame(intersections, crs=grille.crs)
    
    def _categoriser_valeurs(self, serie, nom_couche):
        """Convertit les valeurs catégorielles en scores numériques"""
        # Convertir en numérique (les "No data" et autres textes deviendront NaN)
        serie_num = pd.to_numeric(serie, errors='coerce')
        
        # Les zones "No data" ou NaN deviennent 0
        serie_num = serie_num.fillna(0)
        
        # Pour les couches avec scores 0-5, normaliser sur 0-1
        if nom_couche in ['crues', 'sens_terr_crues', 'sens_terr_pluies', 'sens_social_crues', 'sens_social_pluies']:
            scores = serie_num / 5.0
        else:
            # Normalisation par défaut si ce n'est pas une échelle sur 5
            max_val = serie_num.max()
            scores = serie_num / max_val if max_val > 0 else pd.Series(0.5, index=serie.index)
            
        return scores

    def visualiser(self, fichier_sortie="carte_zones_inondation.html"):
        """Crée une carte interactive choroplèthe des zones à risque de crues."""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        
        print(f"\n🗺️  Création de la carte interactive ({len(self.zones_analysees)} zones)...")
        
        couleurs = {
            'Faible':   '#2ecc71',
            'Modéré':   '#f39c12',
            'Élevé':    '#e74c3c',
            'Critique': '#8b0000',
        }

        cols_carte = ['zone_id', 'ADIDU', 'niveau_risque', 'score_risque',
                      'score_vuln_sociale', 'pct_65_plus', 'revenu_median_menage',
                      'gini', 'val_crues', 'geometry']
        cols_carte = [c for c in cols_carte if c in self.zones_analysees.columns]

        zones_wgs84 = (
            self.zones_analysees[cols_carte]
            .copy()
            .to_crs(epsg=4326)
        )
        zones_wgs84['geometry'] = zones_wgs84['geometry'].simplify(
            tolerance=0.00005, preserve_topology=True
        )
        zones_wgs84['niveau_risque'] = zones_wgs84['niveau_risque'].astype(str)

        centre = [
            zones_wgs84.geometry.centroid.y.mean(),
            zones_wgs84.geometry.centroid.x.mean(),
        ]
        
        m = folium.Map(location=centre, zoom_start=11, tiles='OpenStreetMap')

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
            name='Risque crues',
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=[f for f in
                        ['ADIDU', 'niveau_risque', 'score_risque',
                         'val_crues', 'score_vuln_sociale', 'pct_65_plus', 'revenu_median_menage']
                        if f in zones_wgs84.columns],
                aliases=[f for f, a in [
                    ('ADIDU',               'Aire de diffusion'),
                    ('niveau_risque',        'Niveau de risque'),
                    ('score_risque',         'Score (0-100)'),
                    ('val_crues',            'Classe crues'),
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
          <b>Risque inondation (crues)</b><br>
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
    
    def exporter_resultats(self, fichier_sortie="zones_risque_inondation.geojson"):
        """Exporte les résultats en GeoJSON."""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
            
        self.zones_analysees.to_crs(epsg=4326).to_file(fichier_sortie, driver='GeoJSON')
        print(f"\n💾 Résultats exportés : {fichier_sortie}")
    
    def statistiques(self):
        """Affiche des statistiques sur l'analyse"""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        
        print("\n📈 STATISTIQUES DE L'ANALYSE D'INONDATION")
        print("=" * 60)
        
        # Statistiques par niveau de risque
        stats = self.zones_analysees.groupby('niveau_risque').agg({
            'surface_m2': ['sum', 'count'],
            'score_risque': ['mean', 'min', 'max']
        }).round(2)
        
        print("\nRépartition des zones par niveau de risque:")
        print(stats)
        
        # Surface totale
        surface_totale = self.zones_analysees['surface_m2'].sum()
        print(f"\nSurface totale analysée: {surface_totale:,.0f} m² ({surface_totale/1_000_000:.2f} km²)")
        
        # Zones critiques
        zones_critiques = self.zones_analysees[
            self.zones_analysees['niveau_risque'].isin(['Élevé', 'Critique'])
        ]
        surface_critique = zones_critiques['surface_m2'].sum()
        pct_critique = (surface_critique / surface_totale) * 100
        
        print(f"\n⚠️  ZONES À RISQUE ÉLEVÉ/CRITIQUE:")
        print(f"   • Nombre: {len(zones_critiques)} zones")
        print(f"   • Surface: {surface_critique:,.0f} m² ({surface_critique/1_000_000:.2f} km²)")
        print(f"   • Pourcentage du territoire: {pct_critique:.1f}%")
    
    def identifier_infrastructures_risque(self, couche_batiments=None, couche_routes=None):
        """
        Identifie les infrastructures dans les zones à risque
        (stationnements, bâtiments municipaux, routes critiques)
        """
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        
        print("\n🏢 Identification des infrastructures à risque...")
        
        # Filtrer les zones à risque élevé/critique
        zones_dangereuses = self.zones_analysees[
            self.zones_analysees['niveau_risque'].isin(['Élevé', 'Critique'])
        ]
        
        resultats = {}
        
        if couche_batiments:
            batiments = gpd.read_file(couche_batiments)
            if batiments.crs != "EPSG:2950":
                batiments = batiments.to_crs(epsg=2950)
            
            # Intersection avec les zones dangereuses
            batiments_risque = gpd.sjoin(batiments, zones_dangereuses, how='inner', predicate='intersects')
            resultats['batiments'] = len(batiments_risque)
            print(f"   ⚠️  {len(batiments_risque)} bâtiments en zone à risque")
        
        if couche_routes:
            routes = gpd.read_file(couche_routes)
            if routes.crs != "EPSG:2950":
                routes = routes.to_crs(epsg=2950)
            
            # Intersection avec les zones dangereuses
            routes_risque = gpd.overlay(routes, zones_dangereuses, how='intersection')
            longueur_risque = routes_risque.geometry.length.sum()
            resultats['routes_km'] = longueur_risque / 1000
            print(f"   ⚠️  {longueur_risque/1000:.2f} km de routes en zone à risque")
        
        return resultats


# ============================================
# EXEMPLE D'UTILISATION - GESTION INONDATIONS
# ============================================

if __name__ == "__main__":
    print("="*70)
    print("🌊  ANALYSE COMPLÈTE - RISQUE D'INONDATION (CRUES) — GÉOBASE : AIRES DE DIFFUSION")
    print("="*70)
    print("Système expert basé sur les aires de diffusion:")
    print("  • Carte de base : Aires de diffusion")
    print("  • Zones de risque : crues, vulnérabilité sociale")
    print()
    
    # Initialiser le système
    systeme = SystemeExpertInondation()
    
    # Définir le chemin de base vers les données
    from pathlib import Path
    base_path = Path(__file__).parent.parent / "dataset"
    
    # Charger la grille territoriale de base : Aires de diffusion
    systeme.charger_grille_territoriale(
        str(base_path / "vuln_sociales/lad_000b21a_f/lad_000b21a_f.shp")
    )
    
    # 1. VULNÉRABILITÉ SOCIALE
    # Recensement 2021 — 4 indicateurs : revenu, gini, 65+, logements dégradés
    systeme.ajouter_vulnerabilite_sociale(
        chemin_csv=str(base_path / 'montreal_indicateurs_census.csv'),
        poids=0.30,  # 30% du score total
    )

    # 2. VULNÉRABILITÉ AUX CRUES
    # Zones sensibles aux inondations par débordement de cours d'eau
    # Score de vulnérabilité aux crues (polygones simplifiés 2022)
    systeme.ajouter_couche_risque(
        nom='crues',
        chemin=str(base_path / 'vuln_territoriales/crues/vulnerabilite-crues-polygones-simplifies-2022.geojson'),
        colonne_valeur='CruesCl',  # Classe de vulnérabilité aux crues (0-5)
        poids=0.70,  # 70% du score total
        use_spatial_index=False
    )

    # Effectuer l'analyse
    systeme.analyser()
    
    # Afficher les statistiques
    systeme.statistiques()
    
    # Créer la visualisation
    systeme.visualiser("carte_zones_crues.html")
    
    # Exporter les résultats
    systeme.exporter_resultats("zones_risque_crues.geojson")
    
    print("\n✅ Analyse terminée avec succès !")
    print(f"📂 Fichiers générés :")
    print(f"   • carte_zones_crues.html")
    print(f"   • zones_risque_crues.geojson")
    
    # Ouvrir la carte
    webbrowser.open("carte_zones_crues.html")