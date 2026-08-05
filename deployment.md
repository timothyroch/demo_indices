# Deployment Guide — OVH Instance

**Server:** `ubuntu@51.79.101.90`
**Production directory:** `/home/ubuntu/prod`

> OVH blocks many registries (ghcr.io, npmjs, etc.), so we **build images locally** and transfer them.

---

## Prerequisites

- Docker installed locally and on the OVH instance
- SSH access: `ssh ubuntu@51.79.101.90`
- Project checked out on the `deploy2` branch

---

## 1. Build Images Locally

From the project root:

```bash
# Frontend (Angular + Nginx)
docker build \
  --build-arg MAPBOX_API_KEY=YOUR_MAPBOX_TOKEN \
  -t poly-app:latest \
  ./app

# Backend (FastAPI + Python)
docker build \
  -t poly-server:latest \
  ./server
```

## 2. Test Locally (Optional)

```bash
docker compose up -d
```

To test frontend only (no backend):

```bash
docker run --rm -p 8080:80 poly-app:latest
# visit http://localhost:8080
```

Stop everything:

```bash
docker compose down
```

---

## 3. Save Images to Tarballs

```bash
docker save poly-app:latest | gzip > poly-app.tar.gz
docker save poly-server:latest | gzip > poly-server.tar.gz
```

---

## 4. Transfer to OVH

```bash
scp poly-app.tar.gz poly-server.tar.gz ubuntu@51.79.101.90:~/prod/
```

If models have changed, also transfer them:

```bash
scp -r models ubuntu@51.79.101.90:~/prod/models
```

---

## 5. Load & Run on OVH

```bash
ssh ubuntu@51.79.101.90
cd ~/prod

# Load images
docker load < poly-app.tar.gz
docker load < poly-server.tar.gz

# Start services
docker compose up -d
```

The app is now live at **http://51.79.101.90**.

---

## 6. Useful Commands (on OVH)

```bash
# View logs (follow)
docker compose logs -f

# View logs for one service
docker compose logs -f backend
docker compose logs -f frontend

# Restart everything
docker compose down
docker compose up -d

# Restart one service
docker compose restart backend

# Check status
docker compose ps

# Clean up old images
docker image prune -f
```

---

## Environment Variables (see .env.example)

All secrets live in `/home/ubuntu/prod/.env` on the server. Key variables:

| Variable                            | Purpose                                          |
| ----------------------------------- | ------------------------------------------------ |
| `MAPBOX_API_KEY`                    | Mapbox tiles (baked into frontend at build time) |
| `JWT_SECRET`                        | Auth token signing                               |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Initial admin account                            |
| `TWILIO_*`                          | SMS alerts                                       |
| `SENDGRID_API_KEY`                  | Email alerts                                     |
| `GEMINI_API_KEY`                    | Journal report generation                        |
| `CORS_ORIGINS`                      | Allowed frontend origins                         |

---

---

## Troubleshooting

**Seeing "Welcome to nginx" instead of the app?**
The Angular build output wasn't copied correctly. Check that `app/Dockerfile` has:

```dockerfile
COPY --from=builder /app/dist/app/browser/ /usr/share/nginx/html/
```

Rebuild the image.

**API calls returning CORS errors?**
Update `CORS_ORIGINS` in `.env` to include the server IP:

```
CORS_ORIGINS="http://localhost http://51.79.101.90"
```

Then `docker compose restart backend`.
