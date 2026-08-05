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
        # Les fichiers de sensibilité utilisent déjà des scores numériques 0-5
        # Pas besoin de mapping, juste normaliser si nécessaire
        scores = pd.Series(0.5, index=serie.index)
        
        # Pour les couches avec scores 0-5, normaliser sur 0-1
        if nom_couche in ['sens_terr_crues', 'sens_terr_pluies', 'sens_social_crues', 'sens_social_pluies']:
            # Scores déjà numériques (0-5), normaliser sur 0-1
            scores = serie / 5.0
        
        return scores
    
    def visualiser(self, fichier_sortie="carte_zones_inondation.html"):
        """Crée une carte interactive des zones à risque d'inondation"""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        
        print(f"\n🗺️  Création de la carte interactive...")
        print(f"   ⚠️  {len(self.zones_analysees)} zones détectées - optimisation nécessaire...")
        
        # Convertir en WGS84 d'abord (avant simplification)
        zones_wgs84 = self.zones_analysees.to_crs(epsg=4326)
        
        # Calculer le centre AVANT simplification (en projection correcte)
        zones_proj = self.zones_analysees.copy()
        centroid_x = zones_proj.geometry.centroid.x.mean()
        centroid_y = zones_proj.geometry.centroid.y.mean()
        # Convertir le centroïde en WGS84
        import geopandas as gpd
        from shapely.geometry import Point
        centroid_gdf = gpd.GeoDataFrame(
            geometry=[Point(centroid_x, centroid_y)], 
            crs=zones_proj.crs
        ).to_crs(epsg=4326)
        centre = [centroid_gdf.geometry.y[0], centroid_gdf.geometry.x[0]]
        
        # Créer la carte
        m = folium.Map(location=centre, zoom_start=12, tiles='OpenStreetMap')
        
        # Couleurs par niveau de risque
        couleurs = {
            'Faible': '#2ecc71',
            'Modéré': '#f39c12',
            'Élevé': '#e74c3c',
            'Critique': '#8b0000'
        }
        
        # OPTIMISATION : Fusionner les géométries par niveau de risque
        print(f"   🔧 Fusion des géométries par niveau de risque...")
        for niveau in ['Faible', 'Modéré', 'Élevé', 'Critique']:
            subset = zones_wgs84[zones_wgs84['niveau_risque'] == niveau].copy()
            
            if len(subset) > 0:
                print(f"   📍 Traitement {len(subset)} zones de risque {niveau}...")
                
                # OPTION 1 : Si trop de zones (>50k), fusionner en un seul polygone
                if len(subset) > 50000:
                    print(f"      ⚡ Fusion en un seul polygone multi-parties...")
                    # Dissoudre toutes les géométries en une seule
                    dissolved = subset.dissolve()
                    # Simplifier agressivement
                    dissolved['geometry'] = dissolved['geometry'].simplify(tolerance=0.0001, preserve_topology=True)
                    geojson_data = dissolved[['geometry']].to_json()
                    print(f"      ✓ Réduit à 1 polygone fusionné")
                
                # OPTION 2 : Si entre 10k et 50k zones, échantillonner
                elif len(subset) > 10000:
                    print(f"      ⚡ Échantillonnage à 10000 zones...")
                    subset_sample = subset.sample(n=10000, random_state=42)
                    subset_sample['geometry'] = subset_sample['geometry'].simplify(tolerance=0.0001)
                    geojson_data = subset_sample[['geometry']].to_json()
                    print(f"      ✓ Réduit à 10000 zones")
                
                # OPTION 3 : Sinon, simplifier modérément
                else:
                    print(f"      ⚡ Simplification des géométries...")
                    subset['geometry'] = subset['geometry'].simplify(tolerance=0.00005)
                    geojson_data = subset[['geometry']].to_json()
                
                # Créer le style
                style = {
                    'fillColor': couleurs[niveau],
                    'color': couleurs[niveau],
                    'weight': 1,
                    'fillOpacity': 0.5,
                    'opacity': 0.8
                }
                
                # Ajouter à la carte
                folium.GeoJson(
                    geojson_data,
                    name=f'Risque {niveau}',
                    style_function=lambda x, style=style: style,
                    tooltip=f'Risque {niveau}'
                ).add_to(m)
        
        # Ajouter le contrôle des couches
        folium.LayerControl().add_to(m)
        
        # Sauvegarder
        print(f"   💾 Sauvegarde de la carte...")
        m.save(fichier_sortie)
        print(f"   ✓ Carte sauvegardée : {fichier_sortie}")
        print(f"   ℹ️  La carte a été optimisée pour le navigateur")
        
        return m
    
    def exporter_resultats(self, fichier_sortie="zones_risque_inondation.geojson"):
        """Exporte les résultats en GeoJSON"""
        if self.zones_analysees is None:
            raise ValueError("Effectuez d'abord l'analyse avec analyser()")
        
        self.zones_analysees.to_file(fichier_sortie, driver='GeoJSON')
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
    print("�️  ANALYSE COMPLÈTE - RISQUE D'INONDATION PAR MINÉRALISATION")
    print("="*70)
    print("Système expert basé sur la minéralisation du territoire:")
    print("  • Carte de base : Taux de minéralisation par îlot")
    print("  • Zones de risque : minéralisation, crues, cuvettes, pluies, changements climatiques")
    print()
    
    # Initialiser le système
    systeme = SystemeExpertInondation()
    
    # Définir le chemin de base vers les données
    from pathlib import Path
    base_path = Path(__file__).parent.parent / "dataset"
    
    # Charger la grille territoriale de base : MINÉRALISATION par îlot
    # Cette couche contient le taux de végétalisation et minéralisation par îlot
    systeme.charger_grille_territoriale(
        str(base_path / 'vuln_sociales/lad_000b21a_f/lad_000b21a_f.shp')
    )
    
    # 1. MINÉRALISATION (facteur principal)
    # Taux de minéralisation : plus le territoire est minéralisé, plus le risque d'inondation est élevé
    # Les surfaces imperméables empêchent l'infiltration de l'eau
    # ⚠️ Colonne déjà présente dans la grille - utilisation directe
    systeme.ajouter_couche_risque(
        nom='mineralisation',
        chemin=str(base_path / 'vuln_territoriales/mineralisation/taux-vegetalisation-mineralisation-surfaces-ilots(1).geojson'),
        colonne_valeur='Min_Taux',  # Taux de minéralisation (%)
        poids=0.3,  # 30% du score total
        use_spatial_index=False  # Pas besoin, c'est la grille de base
    )
    
    # 2. VULNÉRABILITÉ AUX CRUES
    # Zones sensibles aux inondations par débordement de cours d'eau
    # Score de vulnérabilité aux crues (polygones simplifiés 2022)
    systeme.ajouter_couche_risque(
        nom='crues',
        chemin=str(base_path / 'vuln_territoriales/crues/vulnerabilite-crues-polygones-simplifies-2022.geojson'),
        colonne_valeur='CruesCl',  # Classe de vulnérabilité aux crues (0-5)
        poids=0.25,  # 25% du score total
        use_spatial_index=False
    )
    
    # 3. CUVETTES DE RÉTENTION D'EAU (zones d'accumulation)
    # Les cuvettes sont des zones topographiques qui retiennent l'eau de ruissellement
    # Zones à risque élevé d'inondation par accumulation
    systeme.ajouter_couche_risque(
        nom='cuvettes',
        chemin=str(base_path / 'vuln_territoriales/cuvettes/cuvettes-retention-eau-ruissellement-2021/cuvettes-retention-eau-ruissellement-2021.shp'),
        colonne_valeur='Classe',  # Classe de cuvette
        poids=0.2,  # 20% du score total
        use_spatial_index=True  # ⚡ Optimisation pour 410k géométries
    )
    
    # 4. VULNÉRABILITÉ AUX PLUIES INTENSES
    # Zones sensibles aux pluies abondantes (polygones simplifiés 2022)
    # Score de vulnérabilité aux événements pluvieux extrêmes
    systeme.ajouter_couche_risque(
        nom='pluies',
        chemin=str(base_path / 'vuln_territoriales/pluies/vulnerabilite-pluies-polygones-simplifies-2022.geojson'),
        colonne_valeur='PluiesCl',  # Classe de vulnérabilité aux pluies (0-5)
        poids=0.15,  # 15% du score total
        use_spatial_index=False  # Seulement 5 géométries, pas besoin d'optimisation
    )
    
    
     # ── COUCHE SOCIALE ────────────────────────────────────────────────────
    # Joint directement sur la géobase (DAs = géobase → pas d'overlay spatial)
    # Tous les indicateurs bruts + normalisés sont conservés dans le GeoJSON.
    systeme.ajouter_vulnerabilite_sociale(
        chemin_csv=str(base_path / 'montreal_indicateurs_census.csv'),
        poids=1,
    )

    
    # Effectuer l'analyse
    systeme.analyser()
    
    # Afficher les statistiques
    systeme.statistiques()
    
    # Créer la visualisation
    systeme.visualiser("carte_zones_inondation.html")
    
    # Exporter les résultats
    systeme.exporter_resultats("zones_risque_inondation.geojson")
    
    print("\n✅ Analyse terminée avec succès !")
    print(f"📂 Fichiers générés :")
    print(f"   • carte_zones_inondation.html")
    print(f"   • zones_risque_inondation.geojson")
    
    # Ouvrir la carte
    webbrowser.open("carte_zones_inondation.html")