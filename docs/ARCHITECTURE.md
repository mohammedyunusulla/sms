# SMS Architecture (Dev Environment)

This repository is a unified SMS monorepo with:

- `backend/` (FastAPI/Uvicorn runtime)
- `frontend/` (Vite/React build, served by Nginx in container)
- root deployment orchestration (`docker-compose.yml`) and CI/CD workflow

> Note: earlier naming used `school-management-backend` and `school-management-frontend`. Current live structure is `backend` and `frontend`.

## 1) Monorepo and Environment Strategy

The VM hosts multiple environments and apps on one machine using isolated app folders and localhost port bindings.

- Current SMS dev path: `/home/vm/apps/sms/dev`
- Domain: `https://dev-sms.klopterz.in`
- Environment model:
  - **dev** and **prod** are isolated by directory, compose stack, and host port bindings.
  - same VM can host additional apps/environments by reusing the same pattern:
    - `/home/vm/apps/<app>/<env>`
    - unique localhost ports
    - dedicated Nginx vhost + SSL

## 2) Container and Network Architecture

- Runtime: **rootless Podman** + **podman-compose** (docker compose fallback supported in workflow).
- Shared bridge network: **`app-network`** (external network referenced by compose).
- Central database container (`global_postgres`) is shared infrastructure on the same network.

`docker-compose.yml` in this repo defines:

- `sms_backend_dev` built from `./backend`
- `sms_frontend_dev` built from `./frontend`
- both attached to `app-network`
- both bound only to loopback (`127.0.0.1`) for host-level Nginx proxying

## 3) Service and Port Mapping

| Layer | Container / Service | Image / Build | Internal Port | Host Binding | Notes |
|---|---|---|---:|---|---|
| DB (shared infra) | `global_postgres` | `postgres:16-alpine` | `5432` | `127.0.0.1:5432` | Hosts isolated DBs (`sms_dev`, others) |
| API | `sms_backend_dev` | build `./backend` | `8000` | `127.0.0.1:8001` | FastAPI/Uvicorn |
| Web | `sms_frontend_dev` | build `./frontend` | `3000` (nginx listen) | `127.0.0.1:3001` | Vite static build served by Nginx |

## 4) Runtime Configuration Alignment

From current codebase:

- Backend compose env:
  - `DATABASE_URL=postgresql://admin:ChangeThisStrongPassword123!@global_postgres:5432/sms_dev`
  - `APP_MODULE=main:app`
  - `APP_PORT=8000`
  - `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in`
- Frontend build arg:
  - `VITE_API_BASE_URL=/api`
- Frontend API config fallback:
  - `import.meta.env.VITE_API_BASE_URL || '/api'`

This matches host Nginx `/api/` reverse-proxy routing.

## 5) Reverse Proxy and SSL

Host-level Nginx terminates TLS and routes to localhost-bound containers:

- `https://dev-sms.klopterz.in/` -> `127.0.0.1:3001` (frontend)
- `https://dev-sms.klopterz.in/api/` -> `127.0.0.1:8001` (backend)

SSL is provisioned with Certbot (Let's Encrypt) on the VM.

## 6) Request Flow (ASCII Diagram)

```text
User Browser
    |
    | HTTPS :443 (Let's Encrypt cert)
    v
VM Host Nginx (dev-sms.klopterz.in)
    |------------------------------\
    | /                            | /api/*
    v                              v
127.0.0.1:3001                 127.0.0.1:8001
sms_frontend_dev               sms_backend_dev
(Nginx serves Vite build)      (FastAPI/Uvicorn :8000)
                                   |
                                   | app-network
                                   v
                           global_postgres:5432
                               DB: sms_dev
```

