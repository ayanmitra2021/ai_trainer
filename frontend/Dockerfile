# syntax=docker/dockerfile:1
# Mastery Pulse — frontend (Vite + React, served by Nginx)
#
# Build:  docker build -t mastery-pulse-frontend ./frontend
# Run:    docker run -p 80:80 mastery-pulse-frontend
#
# The API base URL is baked in at build time via VITE_API_BASE_URL.
# Pass --build-arg VITE_API_BASE_URL=https://api.example.com if deploying
# the backend at a different origin (requires CORS to be configured).

FROM node:20-alpine AS build

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

WORKDIR /app

COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# ── Nginx serving stage ───────────────────────────────────────────────────────
FROM nginx:alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback — all paths serve index.html so React Router handles routing
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  location / { try_files $uri $uri/ /index.html; }\n}\n' \
    > /etc/nginx/conf.d/default.conf

EXPOSE 80
