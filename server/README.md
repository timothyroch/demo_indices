### Prerequisites

- Python
- Poetry

### Install dependencies:

```bash
   poetry install
```

## Running the project

Start the development server:

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation

Visit `http://localhost:8000/docs` to see and test all available endpoints.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   └── main.py          # API endpoints and logic
├── pyproject.toml       # Dependencies and project config
├── poetry.lock          # Locked dependency versions
└── README.md
```

## Adding Dependencies

To add a new package:

```bash
poetry add package-name
```

For dev-only packages:

```bash
poetry add --group dev package-name
```

## Lint

```bash
poetry run lint
```

## Environment Variables

Create a `.env` file in the server directory (or project root) for local configuration. Copy from `server/.env.example`:

- **JWT_SECRET**: Secret key for JWT signing (use a long random string in production).
- **ADMIN_USERNAME** / **ADMIN_PASSWORD**: First-run admin account. If no admin user exists at startup, this account is created. Change in production.
- **AUTH_DB_PATH** (optional): Path to SQLite file for user storage (default: `app/auth.db`).

### Journalisation planifiée des modèles (quotidienne)

Quand l’authentification est activée (`AUTH_DISABLED=false`), le serveur lance une tâche en arrière-plan qui **une fois par jour** (par défaut à **12:00**, fuseau `America/Montreal`) exécute les **quatre modèles** (pluvial, fluvial, canicule, neige) pour **chaque utilisateur** enregistré et écrit les résultats dans `user_action_journal` avec l’action `scheduled_model_fetch`. Cela garantit des entrées de journal même si personne n’ouvre l’application.

Variables d’environnement (voir aussi `server/.env.example`) :

- **SCHEDULED_MODEL_LOG_ENABLED** : `true` / `false` (défaut : `true` si auth activée)
- **SCHEDULED_MODEL_LOG_HOUR** / **SCHEDULED_MODEL_LOG_MINUTE** : heure locale du snapshot
- **SCHEDULED_MODEL_LOG_TZ** : fuseau IANA (ex. `America/Montreal`)
- **SCHEDULED_MODEL_SNAPSHOT_LAT** / **SCHEDULED_MODEL_SNAPSHOT_LNG** / **SCHEDULED_MODEL_ZONE_ID** : point et zone utilisés pour tous les calculs planifiés

**Note :** avec plusieurs processus `uvicorn` (`--workers` > 1), chaque worker exécuterait la tâche : désactive la fonctionnalité (`SCHEDULED_MODEL_LOG_ENABLED=false`) ou n’utilise qu’un seul worker, ou externalise le déclenchement (cron + script).

### Rapports structurés sur le journal (Outlines)

- **`POST /api/journal/reports/generate`** (utilisateur authentifié) : même corps que ci‑dessous, mais **uniquement les logs du compte connecté** (`user_id`).
- **`POST /api/admin/journal/reports/generate`** (admin) : agrège des entrées de **tous** les utilisateurs dans `user_action_journal` et produit un JSON **Pydantic** via [Outlines](https://github.com/dottxt-ai/outlines) (`JournalStructuredReport`).

Corps (les deux) : `log_date_from`, `log_date_to` (optionnels, `YYYY-MM-DD`), `max_entries` (10–2000, défaut 400).

- **`JOURNAL_REPORT_BACKEND=mock`** : aucun appel réseau (réponse factice).
- **`gemini`** : clé `GEMINI_API_KEY`, optionnel `GEMINI_MODEL`, optionnel `GEMINI_MAX_OUTPUT_TOKENS` (défaut 16384 ; augmenter si le JSON du rapport est tronqué).

Pour brancher un autre SIAG (Vertex, etc.), ajoute une classe dans `app/services/journal_reports/backends.py` et enregistre-la dans `factory.py`.

**Alertes multi-risques** : lors du chargement des zones pluviales calculées (`/api/flood-zones/computed`), le serveur évalue aussi crues, canicule et neige pour le point défini par les variables d’environnement `SCHEDULED_MODEL_SNAPSHOT_LAT`, `SCHEDULED_MODEL_SNAPSHOT_LNG` (et le modèle pluvial utilise en plus `SCHEDULED_MODEL_ZONE_ID`). Le score pluvial provient de la carte agrégée renvoyée au client.

### Authentication toggle (development)

**To toggle off login during development:**

- Set `authDisabled` to `true` in the Angular environment (e.g. `app/src/environments/environment.development.ts`).
- Set `AUTH_DISABLED=true` in the server `.env` file.

**To toggle on login during development:**

- Set `authDisabled` to `false` in the Angular environment.
- Set `AUTH_DISABLED=false` in the server `.env` file.

### Create a local DB with an admin user

From the project root:

```bash
cd server && poetry run python scripts/create_admin.py [USERNAME] [PASSWORD]
```

If you omit username/password, the script uses `ADMIN_USERNAME` and `ADMIN_PASSWORD` from your `.env`. If the user already exists, their password is updated and `is_admin` is set to `True`. Running the server with auth enabled also creates the DB and an admin on first startup if none exist.
