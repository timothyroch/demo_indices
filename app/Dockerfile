# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM oven/bun:1.3.6-slim AS builder

WORKDIR /app

# Copy package manifests first (layer cache)
COPY package.json bun.lock ./

RUN bun install

COPY . .

# MAPBOX_API_KEY must be present at Angular build time — injected via --build-arg
ARG MAPBOX_API_KEY
RUN echo "MAPBOX_API_KEY=${MAPBOX_API_KEY}" > .env

# Production build uses environment.prod.ts (apiUrl: '/api') via angular.json fileReplacements
RUN bun run build --configuration=production

# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/app.conf

COPY --from=builder /app/dist/app/browser/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
