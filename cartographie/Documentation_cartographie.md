
## Cartographie des risques climatiques à Montréal

### En bref

Cette documentation décrit comment le logiciel évalue, pour chaque petit secteur de Montréal, le **niveau de risque** associé à un aléa climatique (canicule, crues, pluies diluviennes). Pour chaque secteur, on combine trois familles d'informations :

1. **Vulnérabilités territoriales** — caractéristiques physiques du sol (chaleur, imperméabilité, cuvettes, canopée, etc.).
2. **Vulnérabilités sociales** — caractéristiques de la population qui y vit (âge, revenu, qualité du logement, inégalités).
3. **Vulnérabilités d'infrastructures** — réseaux et bâtiments critiques *(prévu, pas encore intégré au score)*.

Le résultat est une **note 0–100** par secteur, traduite en quatre niveaux : *Faible · Modéré · Élevé · Critique*.

> 💡 Tous les aléas n'utilisent pas les mêmes données. Par exemple, l'imperméabilité des sols sert pour les pluies diluviennes ou les crues, mais pas pour les canicules.

### Comment lire ce document

| Partie | Contenu |
| --- | --- |
| **Géobase et données** | D'où viennent les données et comment elles sont organisées |
| **Vulnérabilités territoriales** | Liste des couches géographiques utilisées |
| **Vulnérabilités sociales** | Indicateurs du recensement utilisés |
| **Pondérations par aléa** | Quelle couche pèse combien dans chaque carte |
| **Calcul du score** | Comment on passe des données brutes à un score 0–100 |
| **Guide d'utilisation** | Comment lancer une analyse, ajouter une donnée |

Le code source associé se trouve dans `server/app/cartographie/` :

| Fichier | Aléa | Classe principale |
| --- | --- | --- |
| `cartographie_canicule.py` | Canicule | `SystemeExpertCanicule` |
| `cartographie_crues.py` | Crues | `SystemeExpertInondation` |
| `cartographie_inondations.py` | Inondations / pluies | `SystemeExpertInondation` |
| `cartographie_sociale.py` | Sociale (seule) | `SystemeExpertCanicule` |
| `get_statCan_census_stats.py` | Préparation des indicateurs sociaux | *(script ETL)* |



## Géobase et données

### Qu'est-ce qu'une « géobase » ?

Une géobase, c'est tout simplement notre **manière de découper Montréal en petits secteurs**. Toutes les analyses se font à cette échelle : on calcule un score *par secteur*.

Nous utilisons les **aires de diffusion (AD)** de Statistique Canada. C'est le découpage le plus fin disponible publiquement : chaque AD compte **400 à 700 habitants**, ce qui permet d'aller chercher des contrastes très locaux (un pâté de maisons peut différer du suivant).

- Chaque AD est identifiée par un code unique : la colonne `ADIDU`.
- On filtre uniquement Montréal et Laval : codes commençant par `2466` ou `2465`.
- Fichier source : [aires de diffusion 2021 – Québec (StatCan)][geobase].

[geobase]: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lad_000b21a_f.zip
[carte-ref-statcan]: https://www12.statcan.gc.ca/census-recensement/2021/geo/maps-cartes/referencemaps-cartesdereference/cma_ca_ct-rmr_ar_sr/files-fichiers/2021-92146-421-00.pdf

> 📍 Voir une [carte de référence des aires de diffusion (PDF)][carte-ref-statcan].

### Pourquoi ce découpage et pas un autre ?

L'avantage de ces secteurs est double :
- ils sont **stables et publics**, donc les analyses sont reproductibles ;
- les indicateurs du recensement sont **directement attachés** à chaque AD via `ADIDU`, sans aucune interpolation.

L'inconvénient : les autres jeux de données (cartes des cuvettes, des îlots de chaleur…) ne suivent pas ce découpage. Le logiciel doit donc faire des **intersections géographiques** pour ramener chaque couche à l'échelle des AD. Ces intersections introduisent de petites approximations, documentées dans le code.

### Système de coordonnées

Deux systèmes coexistent :

- **EPSG:2950** (NAD83 / MTM zone 8) — utilisé en interne. C'est une projection en mètres, indispensable pour calculer correctement des **surfaces** et faire des intersections fiables.
- **EPSG:4326** (WGS84) — utilisé pour l'affichage final sur les cartes web (Folium, Leaflet, OpenStreetMap).

Toutes les couches chargées sont automatiquement reprojetées en `EPSG:2950` au chargement.



## Vulnérabilités territoriales

Ces couches décrivent le **terrain lui-même** : sa nature, sa température, sa capacité à absorber l'eau, sa végétation, etc. Toutes proviennent du portail [Données ouvertes – Ville de Montréal][donnees-mtl] (licence permettant un usage commercial).

[donnees-mtl]: https://donnees.montreal.ca/

### Vue d'ensemble

| Couche | À quoi ça sert | Aléas concernés |
| --- | --- | --- |
| Imperméabilisation (minéralisation) | Mesure la part de sol qui n'absorbe pas l'eau | Pluies, inondations |
| Cuvettes de rétention | Repère les creux où l'eau s'accumule | Pluies, inondations |
| Vulnérabilité aux pluies (Ville) | Indice synthétique pluies extrêmes | Pluies, inondations |
| Vulnérabilité aux crues (Ville) | Zones sujettes au débordement | Crues, inondations |
| Îlots de chaleur (satellite) | Zones plus chaudes que la moyenne | Canicule |
| Canopée — couche **protectrice** | Couvert végétal qui rafraîchit | Canicule |

### Détails par couche

Chaque couche est listée ci-dessous avec sa **source** (lien), le **fichier exact** consommé par le code, et la **colonne** lue comme valeur de risque.

#### 1. Imperméabilisation (minéralisation)

Plus le sol est minéralisé, moins il absorbe l'eau, plus l'eau ruisselle. C'est un facteur clé pour les pluies diluviennes.

- Source : [Taux de végétalisation et de minéralisation des surfaces][src-min]
- Fichier : `vuln_territoriales/mineralisation/taux-vegetalisation-mineralisation-surfaces-ilots(1).geojson`
- Colonne : `Min_Taux` (% de minéralisation)
- Pondération : **30 %** (inondations)

[src-min]: https://donnees.montreal.ca/dataset/taux-vegetalisation-mineralisation-surfaces

#### 2. Cuvettes de rétention

Les cuvettes sont des creux topographiques où l'eau de pluie s'accumule. Une zone qui contient beaucoup de cuvettes est plus à risque d'inondation localisée.

- Source : [Cuvettes de rétention d'eau de ruissellement][src-cuv]
- Fichier : `vuln_territoriales/cuvettes/cuvettes-retention-eau-ruissellement-2021/cuvettes-retention-eau-ruissellement-2021.shp`
- Colonne : `Classe`
- Pondération : **20 %** (inondations)
- ⚙️ ~410 000 polygones — l'**indexation R-Tree** (`use_spatial_index=True`) est obligatoire pour des temps de calcul raisonnables.

[src-cuv]: https://donnees.montreal.ca/dataset/cuvettes-retention-eau-ruissellement

#### 3. Vulnérabilité aux pluies (Ville de Montréal)

Indice synthétique calculé par la Ville pour les épisodes pluvieux extrêmes.

- Source : [Vulnérabilité aux changements climatiques][src-pluies]
- Fichier : `vuln_territoriales/pluies/vulnerabilite-pluies-polygones-simplifies-2022.geojson`
- Colonne : `PluiesCl` (classe 0–5)
- Pondération : **15 %** (inondations)

[src-pluies]: https://donnees.montreal.ca/dataset/vulnerabilite-changements-climatiques

#### 4. Vulnérabilité aux crues (Ville de Montréal)

Indice synthétique calculé par la Ville pour les débordements de cours d'eau.

- Source : [Vulnérabilité aux changements climatiques][src-pluies]
- Fichier : `vuln_territoriales/crues/vulnerabilite-crues-polygones-simplifies-2022.geojson`
- Colonne : `CruesCl` (classe 0–5)
- Pondération : **70 %** dans la carte des crues, **25 %** dans la carte des inondations.

#### 5. Îlots de chaleur

Issus d'images satellites, ces polygones identifient les zones plus chaudes que la moyenne urbaine.

- Source : [Îlots de chaleur 2023][src-cha]
- Fichier : `vuln_territoriales/ilots_chaleurs/ilots-de-chaleur-images-satellite-2023/ilots-de-chaleur-images-satellite-2023.shp`
- Colonne : `Temp_Class` (1–5)
- Pondération : **30 %** (canicule)

[src-cha]: https://donnees.montreal.ca/dataset/ilots-de-chaleur

#### 6. Canopée — couche **protectrice**

La canopée (couvert végétal vu du dessus) rafraîchit le sol. C'est la **seule couche dite « protectrice »** du système : elle **diminue** le score au lieu de l'augmenter.

- Source : [Indice de canopée][src-can]
- Fichier : `vuln_territoriales/canope-2019/canopee-2019.shp`
- Colonne : *(aucune — on ne regarde que la présence/absence)*
- Pondération : **20 %** (canicule)
- ⚙️ ~514 000 polygones — R-Tree obligatoire.

[src-can]: https://donnees.montreal.ca/dataset/indice-canopee

> 🌳 Concrètement : plus une AD est couverte par la canopée, **moins** elle contribue au risque canicule. La formule devient
> `contribution = val_norm × (1 − %_couverture) × poids`.



## Vulnérabilités sociales

### Pourquoi des indicateurs sociaux ?

Face à un même aléa, deux quartiers ne sont pas égaux. Une canicule frappe plus durement une population âgée ; une inondation pèse plus lourd sur des ménages à faible revenu, qui ont moins de marge pour réparer ou se reloger. Le score social tente de capturer ces inégalités.

### Source

Les données proviennent du **recensement 2021 de Statistique Canada** (les chiffres du recensement 2026 devraient être publiés en 2027).

- Fichier source brut : `dataset/vuln_sociales/98-401-X2021006_Quebec_fra_CSV/98-401-X2021006_Francais_CSV_data_Quebec.csv`
- Téléchargement : [profil du recensement Québec (CSV)][src-statcan]
- Licence : [Licence ouverte du Canada][licence-ca]

[src-statcan]: https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=F&FILETYPE=CSV&GEONO=006_Quebec
[licence-ca]: https://www.statcan.gc.ca/fr/avis/licence-ouverte

### Préparation des données

Le fichier brut couvre **tout le Québec** et pèse plusieurs Go. Le script `get_statCan_census_stats.py` :

1. filtre les lignes pour ne conserver que les **AD de Montréal** (`ADIDU` commençant par `2466`),
2. extrait une douzaine d'indicateurs utiles,
3. les pivote en colonnes (une ligne = une AD, une colonne = un indicateur),
4. exporte le résultat dans `dataset/montreal_indicateurs_census.csv`.

C'est ce CSV léger (~6 000 lignes) qui est ensuite chargé par les modules cartographiques.

### Indicateurs extraits

Tous les indicateurs ci-dessous sont extraits par le script et **conservés dans le GeoJSON final** (utiles pour les info-bulles, l'inspection, l'analyse).

| Colonne CSV | Description | ID StatCan |
| --- | --- | --- |
| `age_moyen` | Âge moyen de la population | 39 |
| `pop_65_plus` | Personnes de 65 ans et + (nb) | 24 |
| `pct_65_plus` | Personnes de 65 ans et + (%) | 37 |
| `pop_75_plus` | Personnes de 75 ans et + (nb, calculé) | 27+28+29 |
| `pop_vivant_seule` | Personnes vivant seules (nb) | 97 |
| `revenu_median_menage` | Revenu médian des ménages 2020 ($) | 243 |
| `revenu_moyen_menage` | Revenu moyen des ménages 2020 ($) | 252 |
| `gini` | Coefficient de Gini (inégalité) | 379 |
| `taux_chomage` | Taux de chômage (%) | 2230 |
| `logement_30pct_revenu` | Ménages dont ≥ 30 % du revenu va au logement | 1467 |
| `logement_reparations_majeures` | Logements à rénover (nb) | 1451 |
| `logement_taille_non_convenable` | Logements de taille non convenable (nb) | 1472 |

### Indicateurs utilisés dans le score

Sur cette douzaine d'indicateurs, **seuls 4** entrent dans le calcul du score social :

| Indicateur | Logique | Effet sur le risque |
| --- | --- | --- |
| `revenu_median_menage` | Bas revenu = moins de capacité à se remettre d'un sinistre | Inversé (bas → score haut) |
| `gini` | Inégalité élevée = vulnérabilité plus concentrée | Direct |
| `pct_65_plus` | Population âgée plus exposée (canicule, mobilité) | Direct |
| `logement_reparations_majeures` | Bâti dégradé = moins de protection face aux aléas | Direct |

**Méthode de calcul du `score_vuln_sociale`** :

1. Jointure directe `géobase ↔ CSV` sur `ADIDU`.
2. Chaque indicateur est normalisé sur **0–1** (min-max). Le revenu est inversé pour qu'un bas revenu donne un score élevé.
3. Le score social est la **moyenne équipondérée** des 4 indicateurs normalisés (chacun pèse 25 %).
4. Ce score est ensuite injecté dans le score global de l'aléa avec son propre poids (cf. tableau `Pondérations` plus bas).



## Vulnérabilités d'infrastructures

> ⚠️ Ces couches sont **prévues** mais **pas encore intégrées au calcul du score**. Le logiciel sait déjà *repérer* a posteriori les bâtiments et routes situés en zones critiques (méthode `identifier_infrastructures_risque`), mais la dimension « infrastructure » n'influence pas encore la note 0–100.

| Variable | Source envisagée | Indicateurs envisagés |
| --- | --- | --- |
| Réseau électrique | Hydro-Québec | Zones de fragilité, proximité des postes |
| Infrastructures d'eau | Plans directeurs municipaux | Âge des conduites, stations en zone inondable |
| Équipements critiques | OpenStreetMap / Google Places | CHSLD, hôpitaux, casernes |



## Pondérations par aléa

Chaque carte combine ses couches avec un poids spécifique. Voici la recette de chacune :

### Canicule (`cartographie_canicule.py`)

| Couche | Poids |
| --- | --- |
| Vulnérabilité sociale | 50 % |
| Îlots de chaleur (`Temp_Class`) | 30 % |
| Canopée (protectrice) | 20 % |

### Crues (`cartographie_crues.py`)

| Couche | Poids |
| --- | --- |
| Crues (`CruesCl`) | 70 % |
| Vulnérabilité sociale | 30 % |

### Inondations / pluies diluviennes (`cartographie_inondations.py`)

| Couche | Poids |
| --- | --- |
| Minéralisation (`Min_Taux`) | 30 % |
| Crues (`CruesCl`) | 25 % |
| Cuvettes (`Classe`) | 20 % |
| Pluies (`PluiesCl`) | 15 % |
| Vulnérabilité sociale | 100 %\* |

\* Les poids n'ont pas besoin de sommer à 1 : le score est ensuite divisé par la somme des poids (cf. formule). Un poids social de 1 dans un mélange de couches dont la somme dépasse 1 reste donc cohérent.

### Sociale seule (`cartographie_sociale.py`)

Une carte purement sociale, où seul le `score_vuln_sociale` est utilisé.



## Calcul du score de risque

### L'idée intuitive

Pour chaque secteur, on se pose trois questions par couche :

1. **Quelle gravité ?** — la valeur de la couche dans le secteur (ex. classe 4/5 d'îlot de chaleur).
2. **Quelle étendue ?** — la part de la surface du secteur qui est concernée.
3. **Quelle importance ?** — le poids attribué à cette couche dans la recette de l'aléa.

On multiplie ces trois facteurs pour obtenir la **contribution** de la couche, on additionne toutes les contributions, on normalise, et on obtient une note sur 100.

### Étape par étape

**1. Préparer chaque couche**

- Reprojection en `EPSG:2950` (mètres).
- Intersection géographique avec les AD (sauf si la couche est déjà alignée sur la géobase, comme le score social).
- Pour les gros fichiers (canopée, cuvettes), un **index R-Tree** accélère drastiquement les calculs.
- Si une AD est traversée par plusieurs polygones de classes différentes, on retient la **classe la plus sévère** (celle qui donne le pire score).

**2. Normaliser les valeurs sur 0–1**

| Type de donnée | Normalisation |
| --- | --- |
| Numérique continue (ex. `Min_Taux`) | `val / max(val)` |
| Catégorielle 0–5 (ex. `CruesCl`) | `val / 5` |
| Présence/absence (canopée) | `1` (seule la surface couverte compte) |
| Score social déjà 0–1 | utilisé tel quel |

**3. Calculer la contribution de chaque couche**

- Couche **de risque** :

```
contribution = val_norm × (% surface affectée / 100) × poids
```

- Couche **protectrice** (canopée) :

```
contribution = val_norm × (1 − % surface affectée / 100) × poids
```

**4. Additionner et normaliser**

```
score_brut    = somme des contributions
score_risque  = (score_brut / somme des poids) × 100
```

### Catégorisation finale

| Score (0–100) | Niveau | Couleur sur la carte |
| --- | --- | --- |
| 0 – 10 | Faible | Vert (`#2ecc71`) |
| 10 – 30 | Modéré | Orange (`#f39c12`) |
| 30 – 60 | Élevé | Rouge (`#e74c3c`) |
| 60 – 100 | Critique | Rouge foncé (`#8b0000`) |

### Exemple chiffré

Imaginons un secteur de **10 000 m²** analysé pour le risque inondation, avec deux couches seulement :

- **Crues** : 30 % de la surface en classe élevée (`val_norm = 0.8`, `poids = 0.5`)
- **Canopée** (protectrice) : 50 % de la surface couverte (`val_norm = 1`, `poids = 0.3`)

Calcul :

```
contribution_crues   = 0.8 × 0.30 × 0.5 = 0.12
contribution_canope  = 1.0 × (1 − 0.50) × 0.3 = 0.15
score_brut           = 0.12 + 0.15 = 0.27
score_risque         = (0.27 / (0.5 + 0.3)) × 100 ≈ 33.75
```

→ **Niveau Élevé**.



## Guide d'utilisation

> 🏙️ **Pour qui ?** Ce guide s'adresse aux personnes qui souhaitent **étendre le logiciel à une autre ville** que Montréal (par exemple Québec, Sherbrooke, Trois-Rivières, ou n'importe quelle municipalité canadienne). Les étapes décrivent comment retrouver les bons jeux de données équivalents, les organiser, puis lancer une nouvelle analyse. Pour Montréal, tout est déjà en place — il suffit de lancer les scripts (étape 3).

### Étape 1 — Récupérer les données

Les jeux de données ne sont **pas versionnés** dans le dépôt (volume trop important). Il faut les télécharger soi-même et les organiser dans `server/app/dataset/` selon cette arborescence :

```
server/app/dataset/
├── montreal_indicateurs_census.csv          (généré à l'étape 2)
├── vuln_sociales/
│   ├── lad_000b21a_f/                       (géobase Québec)
│   │   └── lad_000b21a_f.shp (+ .dbf .prj .shx)
│   └── 98-401-X2021006_Quebec_fra_CSV/
│       └── 98-401-X2021006_Francais_CSV_data_Quebec.csv
└── vuln_territoriales/
    ├── mineralisation/...geojson
    ├── cuvettes/...shp
    ├── ilots_chaleurs/...shp
    ├── canope-2019/canopee-2019.shp
    ├── crues/...geojson
    └── pluies/...geojson
```

Liens de téléchargement :

- [Aires de diffusion – StatCan][geobase]
- [Recensement 2021 – Québec (CSV)][src-statcan]
- [Données ouvertes – Ville de Montréal][donnees-mtl] (chercher chaque dataset listé plus haut)

### Étape 2 — Générer le CSV des indicateurs sociaux

Une seule fois (le résultat est mis en cache dans `/tmp/montreal_indicateurs.csv`) :

```bash
cd server/app/cartographie
python get_statCan_census_stats.py
```

Cela produit `server/app/dataset/montreal_indicateurs_census.csv`, prêt à être consommé par les modules cartographiques.

> ✏️ **Ajouter un nouvel indicateur social** : repérer son `ID_CARACTÉRISTIQUE` dans le dictionnaire `INDICATEURS` du script et y ajouter `{id: "nom_de_colonne"}`. Régénérer le CSV. Pour qu'il influence le score, l'ajouter aussi à `cols_utiles` et à la normalisation dans `ajouter_vulnerabilite_sociale()`.

### Étape 3 — Lancer une analyse

Chaque module est exécutable directement et produit deux fichiers dans le répertoire courant : une **carte HTML** interactive et un **GeoJSON** détaillé.

```bash
cd server/app/cartographie

python cartographie_canicule.py
python cartographie_crues.py
python cartographie_inondations.py
python cartographie_sociale.py
```

Le navigateur s'ouvre automatiquement sur la carte générée.

### Étape 4 — Intégrer un nouveau jeu de données géographique

Pour ajouter une couche territoriale supplémentaire (un nouveau GeoJSON ou Shapefile) :

```python
systeme.ajouter_couche_risque(
    nom='ma_couche',
    chemin=str(base_path / 'vuln_territoriales/.../mon_fichier.geojson'),
    colonne_valeur='NomColonne',     # ou None pour présence/absence
    poids=0.20,
    use_spatial_index=True,          # True si > ~10 000 polygones
    protective=False,                # True si la couche RÉDUIT le risque
)
```

Quelques recommandations pratiques :

- **CRS** — vérifier que le fichier source a un CRS défini (sinon erreur). Le code reprojette tout en `EPSG:2950`.
- **Colonne** — la repérer avec `gpd.read_file(...).columns` ou dans QGIS. Si elle est catégorielle non numérique, ajouter le mapping dans `_categoriser_valeurs()`.
- **Poids** — pas besoin que la somme fasse 1 ; le score divise par la somme des poids.
- **R-Tree** — l'activer dès que le fichier dépasse ~10 000 polygones, sinon les temps de calcul explosent.
- **Validation** — utiliser `systeme.statistiques()` pour voir la répartition Faible/Modéré/Élevé/Critique après ajout.

### Étape 5 — Récupérer le GeoJSON résultat

Le fichier exporté par `exporter_resultats(...)` contient, pour chaque AD :

- la **géométrie** (polygones, en WGS84 pour `cartographie_crues.py`, en EPSG:2950 pour les autres) ;
- l'identifiant `ADIDU` et les métadonnées de la géobase ;
- les **indicateurs bruts** (`revenu_median_menage`, `gini`, `pct_65_plus`, …) ;
- les **indicateurs normalisés** (`score_revenu`, `score_gini`, `score_age`, …, `score_vuln_sociale`) ;
- pour chaque couche `i` : `val_i`, `pct_i`, `surface_i_m2`, `poids_i` ;
- le score final `score_risque` (0–100) et le `niveau_risque`.

Ce fichier est directement utilisable par un front-end (Leaflet, Mapbox…) ou par un autre service du projet.

### Étape 6 — Repérer les infrastructures critiques *(optionnel)*

Une fois l'analyse effectuée :

```python
systeme.identifier_infrastructures_risque(
    couche_batiments='chemin/vers/batiments.shp',
    couche_routes='chemin/vers/routes.shp',
)
```

Renvoie le nombre de bâtiments et la longueur de routes (en km) situés dans les zones de niveau Élevé ou Critique. Disponible sur `SystemeExpertInondation` (modules crues / inondations).



## Outils utilisés en complément du code

Au-delà des bibliothèques Python (`geopandas`, `shapely`, `folium`, `pandas`), deux outils externes ont été particulièrement utiles pendant la préparation et la validation des jeux de données. Ils sont **gratuits** et n'ont pas besoin d'être installés sur le serveur — ils servent uniquement au travail d'exploration en amont.

### QGIS

[QGIS][qgis] est un **logiciel de cartographie open source** (gratuit, multiplateforme), équivalent libre à ArcGIS. Il permet d'ouvrir, de visualiser et d'inspecter des fichiers géographiques (Shapefile, GeoJSON, GeoPackage, raster, etc.) sans écrire une ligne de code.

[qgis]: https://qgis.org/

**Utilité dans ce projet** :

- Visualiser des couches **complexes ou volumineuses** (îlots de chaleur, canopée, cuvettes) avant de décider comment les intégrer dans le code.
- Vérifier la **structure attributaire** d'un fichier (noms de colonnes, valeurs possibles) pour configurer correctement `colonne_valeur` dans `ajouter_couche_risque(...)`.
- Contrôler le **système de coordonnées** (CRS) d'un nouveau jeu de données.
- Comparer plusieurs couches superposées (par exemple : croiser visuellement les îlots de chaleur avec la canopée pour vérifier que les zones rouges sont bien là où la végétation manque).
- Inspecter rapidement le résultat d'une analyse en ouvrant le `.geojson` exporté par les modules cartographiques.

### Mapshaper

[Mapshaper][mapshaper] est un **outil web** (sans installation, dans le navigateur) qui permet de **vérifier rapidement** un fichier géographique téléchargé : ses limites, sa table d'attributs, sa géométrie.

[mapshaper]: https://mapshaper.org/

**Utilité dans ce projet** :

- **Confirmer qu'un dataset téléchargé correspond bien à ce que l'on cherche** avant de l'intégrer (par exemple : vérifier que le fichier des aires de diffusion couvre bien le Québec entier, ou que tel GeoJSON couvre bien Montréal).
- Inspecter la **délimitation** d'un jeu de données (zone géographique réellement couverte).
- Faire des **simplifications** ou des **conversions de format** légères (Shapefile ↔ GeoJSON ↔ TopoJSON) pour les tests, sans avoir à lancer QGIS.
- Très utile lors du **portage à une nouvelle ville** : on glisse-dépose le shapefile candidat, on vérifie en quelques secondes que c'est le bon territoire avant de l'ajouter au pipeline.

### En résumé

| Outil | Rôle | Quand l'utiliser |
| --- | --- | --- |
| **QGIS** | Visualisation et analyse approfondie | Comprendre une couche, configurer son intégration |
| **Mapshaper** | Vérification rapide en ligne | Valider un téléchargement, contrôler une délimitation |
