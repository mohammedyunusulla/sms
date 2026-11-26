# Institution Management System (SMS) Monorepo

Unified repository for backend, frontend, containerization, and CI/CD deployment.

- **Target URL:** https://dev-sms.klopterz.in
- **VM deploy path:** `/home/vm/apps/sms/dev`

## Runtime Architecture

- Shared PostgreSQL container: `global_postgres` on `app-network`
- Main auth DB: `sms_dev` (`users`, `institutions`, `user_sessions`)
- Tenant institution DBs: `eduspyre_<skid>`
- Backend: `127.0.0.1:8001 -> 8000`
- Frontend: `127.0.0.1:3001 -> 3000`

## Environment Variables

Use `.env.example` as baseline.

- `SUPER_ADMIN_DATABASE_URL=postgresql://admin:ChangeThisStrongPassword123!@global_postgres:5432/sms_dev`
- `POSTGRES_HOST=global_postgres`
- `POSTGRES_PORT=5432`
- `POSTGRES_USER=admin`
- `POSTGRES_PASSWORD=ChangeThisStrongPassword123!`
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in`
- `APP_PORT=8000`
- `VITE_API_BASE_URL=/api`
- `GEMINI_API_KEY=<your-google-gemini-api-key>`
- `HOMEWORK_UPLOAD_DIR=/app/uploads/homework` (optional)

## AI Homework Module

- API prefix: `/api/homework`
- Backend files:
  - `backend/app/api/homework.py`
  - `backend/app/services/homework_service.py`
  - `backend/app/services/homework_gemini_service.py`
  - `backend/app/models/tenant/Homework.py`

## Local Development

```bash
podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
podman-compose up -d --build
```

Fallback:

```bash
docker compose up -d --build
```
