# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo for the multi-tenant Institution Management System (SMS):

- `backend/` — Flask 2.3 + SQLAlchemy 2 REST API with Flask-SocketIO. See `backend/CLAUDE.md` for its details: the service-layer pattern, auth decorators, roles and `skid` scoping.
- `frontend/` — "Edusphere" React 19 + TypeScript + Vite 6 + Tailwind v4 + Zustand SPA. See `frontend/CLAUDE.md` for its details: routing, the permission system and the axios client.
- `edusphere-app/` — Expo (React Native) mobile app for all roles, talking to the same backend API (live bus map via Socket.IO, background GPS + QR check-in for bus staff). Not yet released ("coming soon" on the landing page). See `edusphere-app/CLAUDE.md`; install with `npm install --legacy-peer-deps`, run with `npx expo start`. It is not part of `docker-compose.yml` or the deploy workflow.
- `docker-compose.yml`, `.github/workflows/deploy-dev.yml`, `docs/` — deployment and ops runbooks for the shared dev VM.

Note: `docs/ARCHITECTURE.md` describes the backend as "FastAPI/Uvicorn". That is outdated. The backend is Flask, started with `python run.py` (`socketio.run`, `async_mode='threading'`).

## Commands

Full stack in containers (requires the external `app-network` and a `global_postgres` container on it):

```bash
podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
podman-compose up -d --build        # or: docker compose up -d --build
```
Backend → `127.0.0.1:8001`, frontend (nginx serving the Vite build) → `127.0.0.1:3001`.

Backend (from `backend/`):
```bash
pip install -r requirements.txt
python run.py                        # dev server; FLASK_PORT defaults to 5000 (8000 in container)
python create_admin.py               # interactive super-admin creation
```

Frontend (from `frontend/`):
```bash
npm install
npm run dev        # Vite dev server (:5173)
npm run build      # tsc -b && vite build — this is the type check
npm run lint       # eslint
```

There is no automated test suite in either project. Use `npm run build` (type check) and `npm run lint` to verify frontend changes.

## Architecture essentials

- **Naming: "institution", never "school".** EduSpyre serves schools, colleges and universities, so code, API, database and UI all say institution (`institutions` table, `institution_users`, `institution_id`, role code `INSTITUTION_ADMIN`, `/api/institution`, `/institutions` pages). Databases from before the rename are converted at start-up by `app/utils/institution_rename.py` (runs before `create_all`; a no-op once done). `skid` is intentionally unchanged. Institution databases are named `eduspyre_<skid>` (renamed from the old `skool_<skid>` at start-up by the same module). Use "school" only where it means actual schools, e.g. "schools, colleges and universities".

- **Database per tenant.** The main DB (`SUPER_ADMIN_DATABASE_URL`, e.g. `sms_dev`) holds `users`, `institutions` and `user_sessions` (`app/models/main/`). Each institution gets its own Postgres DB (`app/models/tenant/`), and requests are routed to it through `app/utils/tenant_db.py` / `db_manager.switch_to_institution_db(skid)`.
- **Schema creation is mostly automatic.** On startup, `create_app()` runs `_bootstrap_main_schema`, which does `db.create_all()` plus ad-hoc `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` backfills. Registering a new institution creates its DB through `BaseModelTenant.metadata.create_all`. The Alembic scripts (`run-*dbupgrade.*`, `tenant_migration.py`) point to `migrations_main/` and `migrations_tenant/`, but those directories are **not in the repo**. So for a new column on an existing table, you probably need a manual/bootstrap `ALTER`. `create_all` alone won't add it.
- **Auth.** JWTs carry a `session_token`. The `token_in_blocklist_loader` in `app/__init__.py` rejects any token whose `UserSession` is no longer active, so logging out invalidates tokens on the server side.
- **New API module.** Add the blueprint to `app/api/__init__.py` and register it with a `/api/...` prefix in `create_app()`. Add the matching frontend endpoint in `frontend/src/services/api/config.ts` (`API_ENDPOINTS`) and create a domain service in `frontend/src/services/modules/`.
- **Frontend routing.** `/` is the public landing page (`frontend/src/pages/Landing/`, self-contained components + `landing.css`); the login page is `/signin`, and all "send to login" redirects (ProtectedRoute, logout, forced logout in `services/api/client.ts`) target `/signin`. Contact/demo links (landing page + sign-in page) live in `frontend/src/config/contact.ts`.
- **Frontend ↔ backend.** In containers the frontend is built with `VITE_API_BASE_URL=/api`, and host nginx proxies `/api/*` to the backend.
- **AI homework module** (`/api/homework`): `homework.py`, `homework_service.py`, `homework_gemini_service.py` and the `Homework` tenant model. It needs `GEMINI_API_KEY`. Uploads go to `HOMEWORK_UPLOAD_DIR` (mounted from `backend/uploads/`, which is gitignored).

- **Leave** (`/api/leave`): `leave_service.py` + tenant model `LeaveRequest` (table `leave_requests`, created for existing institutions at start-up). Students apply for themselves, parents for a linked child, staff (Principal/Teacher/Clerk/Bus Staff) for themselves. Student leave is decided by the section's class teacher (`sections.teacher_id`), the Institution Admin or anyone with the `approve_leave` tick box; staff leave by the latter two; nobody decides their own. Approving turns Absent days into Leave, Mark Attendance starts those students as Leave, and no absence push goes out for an approved day. Pages: `/leave/my` (own / child's) and `/leave/requests` (approvers), in `pages/LeaveManagement/`.

- **Push notifications** (`/api/push`, web/PWA only): `push_service.py` (devices, sending in a background thread), `push_events.py` (which event notifies whom: announcements, assignments/homework, results published, absence) and the main-DB `PushSubscription` model (tied to the sign-in session; logout drops it, token refresh moves it). Frontend: `components/pwa/` (`pushClient.ts`, `NotificationsCard.tsx`) and `public/push-sw.js` (imported into the service worker). Needs `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` (generate with `backend/generate_vapid_keys.py`); without them it is a no-op. `pywebpush`/`py-vapid` are pinned to old versions because newer ones need `cryptography>=46`. They are installed on the server from `backend/wheels/` (`requirements-push.txt`), not `requirements.txt`: the dev server can't reach pypi.org, so **never change `backend/requirements.txt`** (it forces a full re-download and the deploy fails); bundle new Python packages in `backend/wheels/` instead.

## Deployment

Every push or merged PR to `main` triggers `deploy-dev.yml`. The workflow rsyncs the repo (with `--delete`) to the VM and runs `compose down && build && up -d` there. The target is https://dev-sms.klopterz.in. Merging to `main` therefore deploys immediately. Environment variables are listed in `.env.example`, and `docs/ENVIRONMENT_AND_SECRETS.md` covers secrets.
