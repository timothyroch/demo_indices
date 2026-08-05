# Ville IA

**Ville IA** est une plateforme d’aide à la décision sur les risques naturels. Ce prototype web permet d’explorer des indicateurs (inondations pluviales, crues, canicules, chutes de neige) sur une carte, de consulter des prévisions et de suivre l’activité via la journalisation.

Ce fichier est le **point d’entrée documentaire** pour Ville IA : il résume **comment utiliser la plateforme** et indique où trouver le détail technique (autres fichiers `.md`).

**Déploiement actuel :** [http://51.79.101.90/](http://51.79.101.90/)

---

## Guide d’utilisation

### Démarrer une session

1. Ouvrez **Ville IA** en local à l’adresse [http://localhost:4200](http://localhost:4200), ou sur l’instance déployée : [http://51.79.101.90/](http://51.79.101.90/).
2. Si la connexion est activée, connectez-vous avec vos identifiants. En développement, l’authentification peut être désactivée selon la configuration (voir [server/README.md](server/README.md), section *Authentication toggle*).

### Carte et sélection

- **Naviguez** sur la carte (zoom, déplacement).
- **Cliquez** sur la carte pour sélectionner une **aire de diffusion** et faire apparaître le panneau latéral de prévisions.
- Utilisez les **filtres** (bandes de risque, seuil de score, filtres sociaux le cas échéant) pour mettre en évidence les zones qui vous intéressent.

### Types de risque (onglets)

L’interface propose des vues par famille de risque, par exemple :

| Onglet        | Rôle principal |
|---------------|----------------|
| Inondations pluviales | Prévisions et indicateurs liés aux précipitations / ruissellement. |
| Crues | Niveaux et prévisions liés aux cours d’eau. |
| Canicules | Indicateurs de chaleur et prévisions associées. |
| Chutes de neige | Neige prévue (cm) et niveau de risque dérivé des prévisions météo. |

Pour chaque onglet, le **panneau latéral** affiche les détails de la zone ou du point sélectionné (données, graphiques ou tableaux selon l’écran).

### Comparaison (deux panneaux)

Sur **grand écran**, vous pouvez **ouvrir un second panneau** pour comparer deux lieux ou deux contextes côte à côte. Cette fonctionnalité est **désactivée sur mobile et tablette** (écran trop étroit).

### Journalisation et rapports

- Les **actions** pertinentes (navigation et prévisions) sont **enregistrées dans le journal** côté serveur.
- Les **rapports structurés** sur cette activité sont générés via l’API (utilisateur ou administrateur selon les droits). Le comportement exact (données réelles vs mode test) dépend des variables d’environnement du serveur; voir [server/README.md](server/README.md), section *Rapports structurés sur le journal*.

### Alertes et paramètres

- Les **paramètres d’alertes** (activation, seuils) se configurent dans l’écran dédié lorsqu’il est disponible.
- Les notifications par **courriel** ou **SMS** utilisent l’**adresse courriel** et le **numéro de téléphone** associés au **compte utilisateur**.
- L’envoi effectif (fournisseurs, clés API, etc.) dépend de la configuration **backend**.

---

## Documentation technique (fichiers `.md`)

| Document | Contenu |
|----------|---------|
| [server/README.md](server/README.md) | API FastAPI, variables d’environnement, authentification, journalisation planifiée, rapports Gemini, création d’un admin local, doc interactive `/docs`. |
| [app/README.md](app/README.md) | Frontend Angular : installation, développement, build, lint. |
| [deployment.md](deployment.md) | Déploiement (Docker, images, transfert, variables sur le serveur, dépannage CORS / nginx). |

---

## Lancer l’application en local

Il faut faire tourner le **backend** (API sur le port **8000**) et le **frontend** (interface sur le port **4200**). L’interface est ensuite disponible à **[http://localhost:4200](http://localhost:4200)**.

### Prérequis

- **Backend** : Python et [Poetry](https://python-poetry.org/) (voir [server/README.md](server/README.md)).
- **Frontend** : [Bun](https://bun.sh/) et Node.js 22.12+ (voir [app/README.md](app/README.md)).

### Configuration

1. À la racine du dépôt et/ou dans `server/`, copiez les exemples d’environnement vers `.env` (voir `.env.example` et `server/.env.example`) et renseignez au minimum ce dont vous avez besoin (JWT, optionnel : auth désactivée en dev, clés externes, etc.).

### Commandes (deux terminaux)

**Terminal 1: API**

```bash
cd server
poetry install
poetry run uvicorn app.main:app --reload
```

L’API écoute sur `http://localhost:8000` (documentation interactive : `http://localhost:8000/docs`).

**Terminal 2: Ville IA (Angular)**

```bash
cd app
bun install
bun run start
```

Le navigateur peut s’ouvrir automatiquement; sinon allez sur **[http://localhost:4200](http://localhost:4200)**.

### Docker

Pour lancer toute la stack avec Docker, voir [deployment.md](deployment.md) et le fichier `docker-compose.yml` à la racine.

### Secrets

Les secrets (JWT, clés cartographiques, Gemini, Twilio, etc.) ne doivent **pas** être commités ; gardez-les uniquement dans vos fichiers `.env` locaux.

---
