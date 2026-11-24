# Multi-App Port Registry

This registry reserves host ports, container names, database names, and deploy paths to prevent collisions on the shared VM.

## Rules

1. Bind app containers only to `127.0.0.1` (host Nginx is the public entrypoint).
2. Keep each app+environment on unique backend/frontend ports.
3. Keep each app+environment on its own PostgreSQL database.
4. Store each deployment in `/home/vm/apps/<app>/<env>`.

## Reserved Allocation Matrix

| App | Env | Backend Host Port | Frontend Host Port | Backend Container | Frontend Container | PostgreSQL DB | Deploy Path | Subdomain |
|---|---|---|---|---|---|---|---|---|
| Institution Management System (`sms`) | dev | `127.0.0.1:8001` | `127.0.0.1:3001` | `sms_backend_dev` | `sms_frontend_dev` | `sms_dev` | `/home/vm/apps/sms/dev` | `dev-sms.klopterz.in` |
| Institution Management System (`sms`) | prod | `127.0.0.1:8002` | `127.0.0.1:3002` | `sms_backend_prod` | `sms_frontend_prod` | `sms_prod` | `/home/vm/apps/sms/prod` | `sms.klopterz.in` |
| Mandi Management (`mandi`) | dev | `127.0.0.1:8003` | `127.0.0.1:3003` | `mandi_backend_dev` | `mandi_frontend_dev` | `mandi_dev` | `/home/vm/apps/mandi/dev` | `dev-mandi.klopterz.in` |
| Mandi Management (`mandi`) | prod | `127.0.0.1:8004` | `127.0.0.1:3004` | `mandi_backend_prod` | `mandi_frontend_prod` | `mandi_prod` | `/home/vm/apps/mandi/prod` | `mandi.klopterz.in` |
| Business Tracker (`biztracker`) | dev | `127.0.0.1:8005` | `127.0.0.1:3005` | `biztracker_backend_dev` | `biztracker_frontend_dev` | `biztracker_dev` | `/home/vm/apps/biztracker/dev` | `dev-biztracker.klopterz.in` |
| Business Tracker (`biztracker`) | prod | `127.0.0.1:8006` | `127.0.0.1:3006` | `biztracker_backend_prod` | `biztracker_frontend_prod` | `biztracker_prod` | `/home/vm/apps/biztracker/prod` | `biztracker.klopterz.in` |

## Host-Level Shared Services

| Service | Host Binding | Purpose |
|---|---|---|
| `global_postgres` (`postgres:16-alpine`) | `127.0.0.1:5432` | Central PostgreSQL hosting isolated per-app/per-env DBs |
| Host Nginx | `0.0.0.0:80`, `0.0.0.0:443` | TLS termination + reverse proxy to localhost app ports |

## Port Ownership Summary

| Range | Reserved For |
|---|---|
| `127.0.0.1:8001-8006` | Backend APIs (FastAPI/Uvicorn, one per app+env) |
| `127.0.0.1:3001-3006` | Frontend web containers (Nginx-served SPA, one per app+env) |

## Change Management

When adding a new app/environment:

1. Reserve the next free backend and frontend pair in this file.
2. Reserve a unique DB name in `global_postgres`.
3. Add matching Nginx vhost routing to selected localhost ports.
4. Create matching deploy path under `/home/vm/apps/`.
5. Update app README and CI/CD docs with the new allocation.

