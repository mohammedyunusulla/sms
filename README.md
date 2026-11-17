# School Management System (SMS) Monorepo

Unified repository for backend, frontend, containerization, and CI/CD deployment of the SMS dev environment.

- **Local path:** `C:\Users\moulla\Downloads\hobbies\SMS`
- **Target URL:** https://dev-sms.klopterz.in
- **VM deploy path:** `/home/vm/apps/sms/dev`

## Monorepo Layout

```text
SMS/
├─ .github/workflows/deploy-dev.yml
├─ .gitignore
├─ .env.example
├─ docker-compose.yml
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ main.py
└─ frontend/
   ├─ Dockerfile
   ├─ nginx.conf
   ├─ package.json
   ├─ vite.config.js
   └─ src/
```

## Runtime Architecture

Shared DB container on external network `app-network`:

- Host: `global_postgres`
- DB: `sms_dev`

Backend:

- Internal port: `8000`
- Host binding: `127.0.0.1:8001`

Frontend:

- Internal port: `3000`
- Host binding: `127.0.0.1:3001`

VM Nginx Routes:

- `dev-sms.klopterz.in` -> Frontend (`127.0.0.1:3001`)
- `dev-sms.klopterz.in/api/` -> Backend (`127.0.0.1:8001`)

## Environment Variables

Use `.env.example` as the baseline.

- `DATABASE_URL=postgresql://admin:ChangeThisStrongPassword123!@global_postgres:5432/sms_dev`
- `APP_MODULE=main:app`
- `APP_PORT=8000`
- `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in`
- `VITE_API_BASE_URL=/api`

## Local Development

Ensure external network exists:

```bash
podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
```

Build and start:

```bash
podman-compose up -d --build
```

Or:

```bash
docker compose up -d --build
```

Stop:

```bash
podman-compose down
```

Or:

```bash
docker compose down
```

## CI/CD Workflow

Workflow file: `.github/workflows/deploy-dev.yml`

Trigger: Push to `main` (or merge into `main`)

### Required GitHub Secrets

- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `DEPLOY_PATH` (`/home/vm/apps/sms/dev`)

### Deployment Steps

1. Checkout code.
2. Configure SSH key + known hosts.
3. `rsync` repository contents to `${DEPLOY_PATH}`.
4. Execute remote commands on VM:
   - `podman-compose down` (fallback: `docker compose down`)
   - `podman-compose up -d --build` (fallback: `docker compose up -d --build`)
   - Container image prune.
