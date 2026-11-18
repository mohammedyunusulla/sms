# School Management System (SMS) Monorepo

Unified repository for backend, frontend, containerization, and CI/CD deployment of the SMS dev environment.

- **Local path:** `C:\Users\moulla\Downloads\hobbies\SMS`
- **Target URL:** https://dev-sms.klopterz.in
- **VM deploy path:** `/home/vm/apps/sms/dev`

## Monorepo Layout

```text
SMS/
├─ .github/workflows/deploy-dev.yml
├─ .env.example
├─ docker-compose.yml
├─ backend/
│  ├─ Dockerfile
│  ├─ run.py
│  ├─ requirements.txt
│  ├─ app/api/homework.py
│  ├─ app/services/homework_service.py
│  ├─ app/services/homework_gemini_service.py
│  └─ app/models/tenant/Homework.py
└─ frontend/
   ├─ Dockerfile
   └─ src/modules/homework/
```

## Runtime Architecture

- Shared PostgreSQL service: `global_postgres` (`sms_dev`) on external network `app-network`.
- Backend: container `8000` -> host `127.0.0.1:8001`
- Frontend: container `3000` -> host `127.0.0.1:3001`
- Nginx on VM:
  - `dev-sms.klopterz.in` -> `127.0.0.1:3001`
  - `dev-sms.klopterz.in/api/` -> `127.0.0.1:8001`

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

## AI Homework & Efficiency Module

- API prefix: `/api/homework`
- Backend features:
  - QR sticker assignment and listing
  - Assignment creation/listing
  - Session start/pause-resume/hint/submit
  - Gemini Socratic hints (`gemini-2.5-flash`)
  - Gemini grading with JSON feedback + efficiency score
  - Assignment analytics (completion, time, accuracy, efficiency, mistakes)
- Frontend features:
  - Teacher assignment creation, sticker manager, analytics dashboard
  - Student scan-to-start, pause/resume, hint, scan-to-finish, image upload, report card

## Local Development

```bash
podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
podman-compose up -d --build
```

Fallback:

```bash
docker compose up -d --build
```

## CI/CD Workflow

Workflow: `.github/workflows/deploy-dev.yml`  
Trigger: push to `main`

Required secrets:

- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `DEPLOY_PATH` (`/home/vm/apps/sms/dev`)

Deployment flow:

1. Checkout repository.
2. Configure SSH and known hosts.
3. `rsync` code to `${DEPLOY_PATH}`.
4. Remote restart:
   - `podman-compose down` (fallback: `docker compose down`)
   - `podman-compose up -d --build` (fallback: `docker compose up -d --build`)
   - `podman image prune -f`
