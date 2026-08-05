
## Modèles d'aléas climatiques

### En bref

Cette documentation décrit comment le logiciel **prédit le risque, jour par jour**, qu'un événement climatique survienne dans une zone donnée de Montréal. Quatre aléas sont actuellement pris en charge :

1. **Inondations pluviales** — quand la pluie elle-même cause des accumulations, des refoulements d'égouts ou des sous-sols inondés.
2. **Crues fluviales** — quand un cours d'eau (le fleuve, une rivière) déborde.
3. **Canicules** — épisodes prolongés de chaleur extrême.
4. **Neige** — chutes de neige importantes ou cumulées sur plusieurs jours.

Pour chaque aléa, le logiciel donne :

- un **niveau de risque** clair : *aucun · modéré · élevé* ;
- une **prévision sur 7 jours** (jour par jour) ;
- une **explication** : quels facteurs ont fait monter ou baisser le risque ;
- un **score combiné** qui mélange la météo *et* la vulnérabilité du terrain (cf. doc cartographie).

> 💡 La cartographie évalue **le terrain** : à quel point un secteur est fragile en soi (chaleur, imperméabilité, population âgée, etc.).
> Les modèles décrits ici évaluent **la météo** : à quel point les conditions des prochains jours sont dangereuses.
> On combine ensuite les deux pour obtenir un risque réaliste.

### Comment lire ce document

| Section | De quoi ça parle |
| --- | --- |
| **Comment ça marche** | Le pipeline en 4 étapes, en termes simples |
| **Score combiné** | Comment on mélange météo et terrain |
| **Sources météo** | D'où viennent les prévisions et l'historique |
| **Inondations pluviales** | Description, seuils, méthode |
| **Crues fluviales** | Description, seuils, méthode |
| **Canicules** | Description, seuils, méthode |
| **Neige** | Description, seuils, méthode |
| **Récap des seuils** | Tous les chiffres clés en un coup d'œil |

### Où se trouve quoi dans le code

| Fichier | Aléa | Approche |
| --- | --- | --- |
| `models/pluvial_floods_model.py` | Inondations pluviales | Modèle entraîné sur des événements passés |
| `models/fluvial_floods_model.py` | Crues fluviales | Modèle pondéré (poids hérités, méthodologie d'entraînement à confirmer) |
| `risk_assessors/heatwave.py` | Canicules | Règles officielles (Gold Standard) |
| `risk_assessors/snow.py` | Neige | Règles basées sur les chutes attendues |
| `providers/open_meteo.py` | *(toutes)* | Récupération des prévisions météo |
| `services/water_levels_service.py` | Crues | Récupération des niveaux des rivières |
| `utils/scoring.py` | *(toutes)* | Combinaison météo + vulnérabilité du terrain |



## Comment ça marche

### Le pipeline en 4 étapes

À chaque prédiction, le logiciel suit toujours la même logique :

1. **Aller chercher les données** — prévisions météo des 7 prochains jours, plus l'historique des derniers jours.
2. **Préparer les chiffres** — calculer les cumuls (par exemple, *combien de pluie est tombée ces 7 derniers jours*), les variations (par exemple, *de combien le niveau du fleuve a-t-il monté en 3 jours*), la saison, etc.
3. **Estimer le risque météo** — soit en consultant un modèle entraîné sur le passé, soit en appliquant des règles officielles.
4. **Mélanger avec le risque du terrain** — un quartier fragile « amplifie » la note ; un quartier robuste l'atténue.

### Trois familles d'approches

Le logiciel utilise trois philosophies différentes selon l'aléa :

| Approche | Aléas concernés | Idée |
| --- | --- | --- |
| **Modèle appris sur le passé** | Inondations pluviales | On a montré au modèle des centaines de journées « avec et sans inondation » ; il a appris à reconnaître les configurations à risque. |
| **Modèle pondéré** | Crues fluviales | Combinaison linéaire de quelques variables clés avec des poids fixes (provenance des poids à confirmer, voir aléa 2). |
| **Règles d'expert** | Canicule, neige | On a codé directement les seuils officiels (par exemple les critères de canicule de Santé publique). C'est transparent et facile à auditer. |

L'avantage des modèles est qu'ils captent des combinaisons subtiles entre plusieurs variables. L'avantage des règles est qu'elles sont **directement explicables** et alignées avec les standards officiels.



## Score combiné — météo + terrain

### Pourquoi mélanger les deux ?

Une pluie de 50 mm n'a pas le même effet partout :
- dans un quartier ultra-minéralisé du centre-ville, l'eau ruisselle sans pouvoir s'infiltrer ;
- dans une zone arborée du West Island, le sol absorbe et la canopée ralentit le ruissellement.

À l'inverse, le quartier le plus fragile au monde n'a aucun problème… s'il ne pleut pas.

Le logiciel calcule donc **deux notes**, puis les fusionne :

- une note de **terrain** (`risk_score`, 0 à 100) — issue de la cartographie statique ;
- une note de **météo** (la probabilité ou l'intensité prévue par le modèle).

### La règle de mélange

La météo pèse **75 %** et le terrain **25 %** dans la note finale. Cette répartition est fixée par la constante `W_IRIU = 0.25` dans `utils/scoring.py`.

En clair :

```
note_finale = 25 % × note_terrain  +  75 % × note_météo
```

C'est délibéré : à court terme, ce qui se passe dehors (la météo) compte plus que la fragilité moyenne du quartier. Mais le terrain reste un facteur d'aggravation important, d'où les 25 %.

### Les trois bandes de risque

La note finale (sur 100) est ensuite traduite en **3 niveaux** affichés à l'utilisateur :

| Note finale | Niveau | Couleur |
| --- | --- | --- |
| 0 – 20 | Faible | Vert |
| 20 – 50 | Modéré | Orange |
| 50 – 100 | Élevé | Rouge |



## Sources de données météo

### Open-Meteo

Toutes les prévisions et tous les historiques météo proviennent du service **[Open-Meteo][openmeteo]**, un agrégateur libre et gratuit qui combine plusieurs modèles météorologiques internationaux.

[openmeteo]: https://open-meteo.com/

Le logiciel utilise deux endpoints :

- **prévisions** (jusqu'à 7 jours à venir) ;
- **archives** (historiques passés, utiles pour les modèles entraînés et pour calculer les cumuls).

Toutes les requêtes sont faites avec le fuseau **`America/Montreal`**.

### Variables récupérées par aléa

| Aléa | Ce qu'on demande à Open-Meteo |
| --- | --- |
| Pluvial | Température moyenne, pluie cumulée |
| Fluvial | Idem (combiné avec les niveaux d'eau du fleuve, voir aléa 2) |
| Canicule | Température max, température min, humidité, point de rosée |
| Neige | Température, neige attendue (cm), précipitation, humidité |

### Couches affichées sur les cartes (en plus)

Indépendamment des modèles, le logiciel affiche aussi des **couches météo officielles d'Environnement Canada** en surimpression sur les cartes. Elles servent à la visualisation, pas au calcul du risque :

| Variable | Couche utilisée |
| --- | --- |
| Température | `GDPS.ETA_TT` (modèle global GDPS) |
| Précipitations 24 h | `RDPA.24F_PR` (analyse régionale) |
| Humidité | `GDPS.ETA_HR` |



## Aléa 1 — Inondations pluviales

### Description

Une **inondation pluviale** survient quand la pluie tombe plus vite que le sol et les égouts ne peuvent l'évacuer : eau qui stagne dans les rues, refoulements, sous-sols inondés. Le cours d'eau n'est pas en cause — c'est le ruissellement urbain qui dépasse les capacités d'absorption.

### Quand parle-t-on d'inondation pluviale ?

Il n'y a **pas de seuil simple** du type « au-delà de X mm de pluie ». L'expérience montre que ça dépend aussi de :

- la **pluie tombée les jours précédents** (un sol déjà saturé déborde plus vite) ;
- la **saison** (un orage d'été n'a pas le même effet qu'une pluie d'automne) ;
- l'**intensité** (50 mm en 30 min ≠ 50 mm en 12 h) ;
- la **température** (gel = surface imperméable).

Le modèle répond à la question « **est-ce qu'on est dans une configuration similaire à des journées qui ont historiquement causé des inondations ?** » et renvoie une **probabilité de 0 à 100 %**.

### Comment le modèle a été entraîné

C'est le point clé pour comprendre la fiabilité des prédictions.

- On a **dépouillé manuellement la presse locale** des **25 dernières années** pour les villes de **Montréal et Laval**, en relevant chaque inondation pluviale médiatisée (sous-sols, refoulements, rues inondées, déclarations d'urgence localisées).
- Pour chaque journée d'événement identifiée, on a **récupéré les données météo correspondantes** (pluie tombée le jour même, mais aussi cumul des jours précédents, température, saison).
- Le modèle a ensuite **appris à reconnaître les configurations météo associées à un événement** et à les distinguer des journées « ordinaires ».

Cette approche reste imparfaite : tous les sous-sols inondés ne sont pas médiatisés, et la médiatisation dépend aussi de la zone (un quartier central est davantage couvert qu'un quartier périphérique). On suit donc les évolutions du modèle dans le temps pour le réajuster.

### Ce que regarde le modèle

| Variable | Ce qu'elle mesure |
| --- | --- |
| Température moyenne du jour | Conditions générales |
| Pluie cumulée 1 jour | Intensité immédiate |
| Pluie cumulée 3 jours | Saturation à court terme |
| Pluie cumulée 5 jours | Saturation à moyen terme |
| Pluie cumulée 7 jours | Saturation profonde |
| Variation de température 2 j | Détecte les fronts d'orage |
| Saison | Influence la nature des pluies |
| Intensité instantanée | Distingue averses brèves et pluies longues |
| Gel oui/non | Sol gelé = surface imperméable |

### Ce que le logiciel renvoie

- Une **probabilité d'inondation** (combinée avec le terrain).
- Une **prévision détaillée** sur 7 jours.
- Une **explication** : pour chaque jour, quelles variables ont le plus contribué (par exemple : *« pluie cumulée 3 jours : forte influence à la hausse »*).
- Une **mesure de confiance** (à quel point le modèle est sûr de lui).
- Un **libellé d'intensité de pluie** (faible · modérée · forte).



## Aléa 2 — Crues fluviales

### Description

Une **crue** est le **débordement d'un cours d'eau** : le fleuve Saint-Laurent, la rivière des Prairies ou la rivière des Mille-Îles débordent de leur lit habituel. Les causes typiques sont les pluies abondantes en amont, la fonte des neiges au printemps, et les embâcles de glace.

### Quand parle-t-on de crue ?

Là encore, pas de seuil simple : le modèle évalue la **probabilité** que le niveau d'eau atteigne un seuil critique dans les jours à venir.

Deux conditions structurelles sont vérifiées **avant** d'appeler le modèle :

1. La zone analysée doit **se trouver dans une zone d'aléa de crue** identifiée par la cartographie. Si on est sur le mont Royal, le modèle ne s'exécute pas — pas de cours d'eau à proximité.
2. Le modèle s'appuie sur les **niveaux d'eau réels** mesurés dans la rivière la plus proche, pas seulement sur la pluie.

### Comment le modèle a été obtenu

> ⚠️ **Honnêteté méthodologique.** Contrairement aux inondations pluviales, le code source ne documente pas la procédure d'entraînement du modèle de crues. Ce qu'on sait avec certitude (parce que c'est lisible dans le code) :
>
> - le modèle est une **combinaison linéaire** de 4 variables avec des **poids fixes** (61 %, 21 %, 15 %, 3 % — voir tableau ci-dessous) ;
> - il s'appuie sur un **scaler** sauvegardé (`fluvial_scaler_V2.pkl`) pour normaliser ces variables avant le calcul.
>
> En revanche, **on ne dispose pas, à ce stade, d'une trace des données qui ont servi à fixer ces poids** : ils ont pu être appris par régression logistique sur un historique de niveaux d'eau, repris de la littérature, ou ajustés à dire d'expert. **À documenter / vérifier auprès de l'équipe.**

Ce qui est sûr, c'est que le modèle utilise au moment de la prédiction :
- les **niveaux d'eau réels** mesurés dans la rivière la plus proche (via `services/water_levels_service.py`) ;
- les **données météo récentes** (pluie cumulée, température) issues d'Open-Meteo.

### Ce que regarde le modèle (et avec quelle importance)

Le modèle s'appuie sur 4 variables, et les poids fixés à l'intérieur du modèle sont très inégaux :

| Variable | Poids dans le modèle | Lecture |
| --- | --- | --- |
| Niveau d'eau actuel | **61 %** | De loin le facteur dominant |
| Pluie cumulée 7 jours | **21 %** | Annonce les futures montées |
| Variation du niveau sur 3 jours | **15 %** | Détecte une tendance haussière |
| Température moyenne 5 jours | **3 %** | Effet marginal (capter les fontes) |

> 📊 **Ce qu'il faut retenir** : ce qui compte avant tout, c'est le **niveau actuel** du cours d'eau, suivi de la **pluie tombée la semaine passée**. La température n'a qu'un effet marginal, surtout utile au printemps pour détecter les fontes massives.

### Ce que le logiciel renvoie

- Une **probabilité de crue** (combinée avec le terrain).
- Une **prévision détaillée** sur 7 jours, avec le niveau d'eau attendu chaque jour.
- Une **explication** : quelles variables ont le plus poussé le risque à la hausse (*forte · modérée · faible influence*) et dans quel sens (à la hausse ou à la baisse).



## Aléa 3 — Canicules

### Description

Une **canicule** est un épisode prolongé de chaleur extrême, dangereux pour la santé : déshydratation, coups de chaleur, surmortalité chez les personnes âgées et fragiles. À Montréal, le danger est aggravé par les **îlots de chaleur urbains** (zones très minéralisées qui retiennent la chaleur la nuit).

### Quand parle-t-on de canicule ?

Contrairement aux inondations, on a ici un **seuil clair**, choisi à l'issue d'une étude comparative (détaillée plus bas). Une canicule est déclarée si, **pendant 2 jours consécutifs au minimum**, l'une des deux conditions suivantes est remplie :

| Critère | Seuil |
| --- | --- |
| Température max **et** température min | Tmax ≥ 32 °C **et** Tmin ≥ 20 °C |
| Humidex (chaleur ressentie) | Humidex ≥ 41 |
| Durée minimale | 2 jours consécutifs |

> 🌡️ L'**humidex** est un indice canadien qui combine la température et l'humidité pour refléter la **chaleur ressentie**. Une journée à 30 °C avec 80 % d'humidité est plus pénible qu'une journée à 30 °C en air sec — l'humidex traduit cette différence.

### D'où vient ce seuil ? La méthodologie

Le seuil retenu n'a pas été choisi au hasard : il vient d'une **étude comparative** menée sur les données de la station **McTavish (centre-ville de Montréal)** entre 2000 et 2025. Voici le raisonnement, étape par étape.

#### 1. Choix de la station : McTavish plutôt que l'aéroport (YUL)

Deux stations étaient candidates : **YUL** (Montréal-Trudeau, en zone dégagée) et **McTavish** (centre-ville). On a comparé les deux sur 25 ans :

| Constat | Différence McTavish − YUL |
| --- | --- |
| Tmax (jours partagés) | ~ 0 °C (essentiellement égales) |
| **Tmin (jours partagés)** | **+ 1.06 °C** |

→ McTavish est **systématiquement plus chaud la nuit** d'environ 1 °C : c'est la signature de l'**îlot de chaleur urbain**. Comme le danger sanitaire d'une canicule se joue surtout sur la **chaleur nocturne** (le corps ne peut plus récupérer), McTavish reflète mieux le risque réel à Montréal que l'aéroport.

> ⚠️ Limite connue : McTavish ne fournit pas la pluie totale ni la visibilité ; ces variables sont donc exclues quand on travaille avec cette station.

#### 2. Constitution d'une liste d'événements de référence

On a recensé **16 vagues de chaleur historiques** repérables dans les médias et bulletins entre 2001 et 2025 (par exemple : juillet 2010, juin 2018, juin 2024, juin/juillet 2025…). Cette liste sert de **« vérité terrain »** pour évaluer chaque seuil candidat.

Quatre de ces 16 événements (2005, 2006, 2019, 2022) se sont avérés être en réalité des **crises de smog/ozone** ou des **alertes de début de saison** plutôt que de la chaleur extrême au sens strict. Les retirer laisse une **liste « Gold Standard » de 12 vrais événements**, sur laquelle on peut juger objectivement les seuils.

#### 3. Comparaison de plusieurs seuils candidats

Quatre formules ont été testées sur les 12 événements. Pour chaque option on regarde :
- la **capture** : combien d'événements parmi les 12 sont effectivement détectés ;
- les **jours-positifs** : combien de journées au total sont étiquetées « canicule » (plus ce nombre est petit à capture égale, plus le seuil est précis).

| Option | Formule (sur 2 jours sauf mention) | Jours-positifs | Capture | Verdict |
| --- | --- | --- | --- | --- |
| 1. INSPQ stricte | Tmax ≥ 33 & Tmin ≥ 20 (sur **3 j**) | 40 | 6/12 | Trop sévère : rate la moitié des vrais événements. |
| 2. Humidex pur | Humidex ≥ 40 | 144 | 12/12 | Excellent, mais un peu lâche. |
| **3. Combiné strict (retenu)** | **(Tmax ≥ 32 & Tmin ≥ 20) OU Humidex ≥ 41** | **122** | **12/12** | Capture 100 % avec ~ 20 jours-positifs en moins que l'option 2. |
| 4. ECCC complet | (Tmax ≥ 30 & Tmin ≥ 20) OU Humidex ≥ 40 | 277 | 12/12 | Trop large : balaie presque tout l'été. |

→ **L'option 3 est retenue** : elle attrape **les 12 événements de référence sans exception**, tout en restant la plus précise (le moins de « faux positifs »).

#### 4. Pourquoi l'humidex pèse autant

Tous les vrais événements de la liste atteignent un **humidex de pointe ≥ 41**. Autrement dit, **l'humidité combinée à la température explique mieux les vraies canicules** que la température sèche seule. C'est pour cela que la formule combine un critère « température » **et** un critère humidex en `OU` : l'un attrape les chaleurs sèches intenses, l'autre les épisodes lourds et étouffants.

### Trois niveaux de réponse

| Niveau | Quand ? |
| --- | --- |
| Aucun | Aucune fenêtre de 2 jours consécutifs ne remplit les critères |
| Modéré | Au moins une fenêtre remplit les critères |
| Élevé | Au moins une fenêtre avec un humidex de pointe très élevé |

Un **message** lisible est généré pour chaque cas, par exemple :
> « Canicule sévère prévue à partir du *18 juillet* (Humidex *45*). »

### Données utilisées

Open-Meteo fournit, pour chaque jour des 7 prochains :

- la température max et la température min ;
- l'humidité relative max ;
- le point de rosée (utilisé pour calculer l'humidex localement).



## Aléa 4 — Neige

### Description

Le module **neige** évalue le risque associé à des **chutes de neige importantes** : perturbations de la circulation, accidents, surcharge des toitures, déneigement débordé. L'enjeu est moins « est-ce qu'il va neiger ? » que « est-ce que la quantité prévue va causer des problèmes ? »

### Quand parle-t-on de risque de neige ?

Le calcul démarre avec un **score de base lié au terrain**, puis ajoute des **incréments** selon ce que la météo annonce. Plus la chute attendue est importante, plus l'incrément est gros.

Les seuils d'incrément sont basés sur les **quartiles historiques d'enneigement à Montréal** :

| Chute attendue dans une journée | Quartile | Incrément ajouté au score |
| --- | --- | --- |
| > 20.5 cm | 4ᵉ (extrême) | + 0.20 |
| 12.9 – 20.5 cm | 3ᵉ (forte) | + 0.15 |
| 8.3 – 12.8 cm | 2ᵉ (modérée) | + 0.05 |
| 0 – 8.2 cm | 1ᵉʳ (faible) | + 0.02 |
| Petite chute le jour suivant une grosse chute | (persistance) | + 0.0008 |

À cela s'ajoutent des modulations selon la température (très froid → impacts aggravés, trop chaud → improbable).

### Trois niveaux de réponse

| Niveau | Quand ? |
| --- | --- |
| Aucun | Aucun jour n'atteint 20 % de probabilité |
| Modéré | Au moins un jour ≥ 20 % |
| Élevé | Au moins un jour > 50 % |

### Mois ignorés

L'analyse est désactivée pendant les mois d'été (juin, juillet, août, septembre) — pas de neige attendue.

### Données utilisées

Open-Meteo fournit, pour chaque jour :

- température moyenne et minimale ;
- précipitation totale ;
- **chute de neige attendue (cm)** ;
- humidité.



## Récapitulatif des seuils

### Les seuils qui déclenchent un événement

| Aléa | Critère | Seuil |
| --- | --- | --- |
| Canicule | Température sur 2 jours consécutifs | Tmax ≥ 32 °C **et** Tmin ≥ 20 °C |
| Canicule | Humidex sur 2 jours consécutifs | Humidex ≥ 41 |
| Neige (modéré) | Probabilité jour | ≥ 20 % |
| Neige (élevé) | Probabilité jour | > 50 % |
| Neige | Chute critique en 24 h | > 20.5 cm |
| Pluvial / Fluvial | *(probabilité continue, pas de seuil binaire)* | (voir bandes ci-dessous) |

### Les bandes de risque combiné (tous aléas confondus)

Une fois la météo et le terrain mélangés, la note finale est répartie sur 3 niveaux :

| Note finale (sur 100) | Niveau | Couleur |
| --- | --- | --- |
| 0 – 20 | Faible | Vert |
| 20 – 50 | Modéré | Orange |
| 50 – 100 | Élevé | Rouge |

### La pondération météo / terrain

| Composante | Poids |
| --- | --- |
| Météo (probabilité du modèle) | 75 % |
| Terrain (vulnérabilité issue de la cartographie) | 25 % |



## Récapitulatif par aléa

| Aléa | Approche | Données principales | Sortie |
| --- | --- | --- | --- |
| Inondations pluviales | Modèle appris sur 25 ans d'événements + météo | Pluie cumulée, saison, intensité | Probabilité + explication par variable |
| Crues fluviales | Modèle pondéré (poids fixes, méthodo à confirmer) | Niveau du cours d'eau, pluie cumulée | Probabilité + explication par variable |
| Canicules | Règles « Gold Standard » dérivées d'une étude sur McTavish | Tmax, Tmin, humidex sur 2 jours | Niveau aucun / modéré / élevé + fenêtres |
| Neige | Règles avec quartiles historiques | Chute attendue, température | Score + détail jour par jour |



## Glossaire

- **ADIDU** — Identifiant unique d'un secteur (aire de diffusion de Statistique Canada). Voir la doc cartographie.
- **Bande de risque** — Tranche de couleur (vert / orange / rouge) attribuée selon la note finale.
- **Combiné (score)** — Note qui mélange la prévision météo et la vulnérabilité du terrain.
- **Explication (par variable)** — Pour chaque prédiction, on indique quelles variables ont le plus contribué et dans quel sens. Cela évite l'effet « boîte noire ».
- **Gold Standard (canicule)** — Liste de 12 vraies vagues de chaleur historiques à Montréal (2001–2025), utilisée comme « vérité terrain » pour calibrer le seuil canicule.
- **Humidex** — Indice canadien qui exprime la chaleur ressentie en combinant température et humidité.
- **Îlot de chaleur urbain (UHI)** — Phénomène par lequel un centre-ville reste plus chaud (surtout la nuit) que les zones périurbaines, à cause du béton, de l'asphalte et du manque de végétation.
- **McTavish / YUL** — Stations météo. McTavish est au centre-ville de Montréal et capte mieux l'îlot de chaleur urbain que YUL (aéroport).
- **Quartile** — Tranche statistique. Pour la neige, on a calculé les seuils 8.2, 12.8 et 20.5 cm à partir de 25 ans d'historique de chutes de neige à Montréal.
- **Score de terrain (`risk_score`)** — Note 0–100 issue de la cartographie statique, indépendante de la météo.
