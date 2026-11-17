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
│  ├─ main.py
│  └─ app/modules/homework/
│     ├─ models.py
│     ├─ gemini_service.py
│     └─ router.py
└─ frontend/
   ├─ Dockerfile
   ├─ nginx.conf
   ├─ package.json
   ├─ vite.config.ts
   └─ src/modules/homework/
      ├─ api/homeworkApi.ts
      ├─ components/QrScannerInput.tsx
      ├─ pages/TeacherHomeworkPage.tsx
      ├─ pages/StudentHomeworkPage.tsx
      └─ pages/HomeworkHub.tsx
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
- `GEMINI_API_KEY=<your-google-gemini-api-key>`
- `HOMEWORK_UPLOAD_DIR=./uploads/homework` (optional)

## AI-Assisted Homework & Efficiency Tracking Module

New feature scope:

- **Backend module:** `backend/app/modules/homework/`
- **Frontend module:** `frontend/src/modules/homework/`
- **API prefix:** `/api/homework`

Key backend capabilities:

- Student QR sticker assignment and retrieval.
- Homework assignment creation/listing.
- Session lifecycle (start, pause/resume, submit).
- AI Socratic hints (`gemini-2.5-flash`) without direct answers.
- AI grading from uploaded notebook images with structured feedback JSON.
- Efficiency scoring based on accuracy, active time vs expected time, and hints used.
- Teacher analytics endpoint for assignment-level completion and performance insights.

Key frontend capabilities:

- Teacher workflow:
  - Create assignments with expected duration and optional rubric.
  - Generate/print student QR stickers.
  - View assignment analytics with efficiency indicators.
- Student workflow:
  - Scan sticker (camera/manual fallback) to start.
  - Live timer with pause/resume.
  - Ask AI for Socratic hints.
  - Scan-to-finish and upload multiple notebook images for instant report card.

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

Notes:

- Backend upload volume in compose:
  - Host: `./backend/uploads`
  - Container: `/app/uploads`
- Ensure `GEMINI_API_KEY` is present before using homework hint/grading endpoints.

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
