# School Management System (SMS) Monorepo

Unified repository for backend, frontend, containerization, and CI/CD deployment of the SMS dev environment.

- **Local path:** `C:\Users\moulla\Downloads\hobbies\SMS`
- **Target URL:** `https://dev-sms.klopterz.in`
- **VM deploy path:** `/home/vm/apps/sms/dev`

## Monorepo layout

```text
SMS/
├─ .github/workflows/deploy-dev.yml
├─ .gitignore
├─ .env.example
├─ docker-compose.yml
├─ school-management-backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ main.py
└─ school-management-frontend/
   ├─ Dockerfile
   ├─ nginx.conf
   ├─ package.json
   ├─ vite.config.js
   └─ src/
```

## Runtime architecture

- Shared DB container on external network `app-network`:
  - Host: `global_postgres`
  - DB: `sms_dev`
- Backend:
  - Internal port `8000`
  - Host binding `127.0.0.1:8001`
- Frontend:
  - Internal port `3000`
  - Host binding `127.0.0.1:3001`
- VM Nginx routes:
  - `dev-sms.klopterz.in` -> frontend (`127.0.0.1:3001`)
  - `dev-sms.klopterz.in/api/` -> backend (`127.0.0.1:8001`)

## Environment variables

Use `.env.example` as the baseline.

- `DATABASE_URL=postgresql://admin:ChangeThisStrongPassword123!@global_postgres:5432/sms_dev`
- `APP_MODULE=main:app`
- `APP_PORT=8000`
- `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in`
- `VITE_API_BASE_URL=/api`

## Local development

1. Ensure external network exists:
   ```bash
   podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
   ```
2. Build and start:
   ```bash
   podman-compose up -d --build
   ```
   or
   ```bash
   docker compose up -d --build
   ```
3. Stop:
   ```bash
   podman-compose down
   ```
   or
   ```bash
   docker compose down
   ```

## CI/CD workflow

Workflow file: `.github/workflows/deploy-dev.yml`

### Trigger

- Push to `main`
- PR merged into `main`

### Required GitHub Secrets

- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `VM_SSH_PORT` (optional, defaults to `22`)
- `DEPLOY_PATH` (`/home/vm/apps/sms/dev`)

### Deployment steps

1. Checkout code.
2. Configure SSH key + known hosts.
3. `rsync` repository contents to `${DEPLOY_PATH}`.
4. Run remote commands:
   - `podman-compose down` (fallback `docker compose down`)
   - `podman-compose up -d --build` (fallback `docker compose up -d --build`)
   - Image prune.
