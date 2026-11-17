# Environment Variables and Secrets Reference

This file defines runtime configuration and CI/CD secrets for:

- current SMS dev deployment, and
- extension to prod and future apps on the same VM pattern.

## 1) Backend `.env` Reference

Create `backend/.env` (or pass these via compose environment).

```dotenv
# App runtime
APP_MODULE=main:app
APP_PORT=8000
BACKEND_START_CMD=uvicorn main:app --host 0.0.0.0 --port 8000

# Database
DATABASE_URL=postgresql://sms_dev_user:REPLACE_WITH_STRONG_PASSWORD@global_postgres:5432/sms_dev

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in

# Auth/JWT
JWT_SECRET_KEY=REPLACE_WITH_64_CHAR_RANDOM_SECRET
ACCESS_TOKEN_EXPIRES_MINUTES=60
REFRESH_TOKEN_EXPIRES_DAYS=14
```

Notes:

- `DATABASE_URL` must target `global_postgres` over `app-network`.
- Use distinct DB user/database per app+env (`sms_prod`, `mandi_dev`, etc.).

## 2) Frontend `.env` Reference

Create `frontend/.env`:

```dotenv
# API base URL used by frontend service layer
VITE_API_BASE_URL=/api
```

For local direct backend testing (without host Nginx), this can be temporarily set to:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## 3) Root `.env` (Compose Defaults) Reference

At repository root:

```dotenv
APP_MODULE=main:app
APP_PORT=8000
DATABASE_URL=postgresql://admin:REPLACE_WITH_STRONG_PASSWORD@global_postgres:5432/sms_dev
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in
VITE_API_BASE_URL=/api
```

## 4) GitHub Actions Secrets (Current Workflow)

Current workflow file: `.github/workflows/deploy-dev.yml`

Required:

- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `DEPLOY_PATH`

Optional (supported by workflow):

- `VM_SSH_PORT` (defaults to `22` if not set)

## 5) Recommended Secret Naming for Multi-Env / Multi-App

To replicate this CI/CD model for prod and other apps, use environment-specific secrets and separate workflows (or a matrix strategy):

### SMS

- `SMS_DEV_VM_HOST`
- `SMS_DEV_VM_USER`
- `SMS_DEV_VM_SSH_KEY`
- `SMS_DEV_VM_SSH_PORT`
- `SMS_DEV_DEPLOY_PATH` (`/home/vm/apps/sms/dev`)
- `SMS_PROD_VM_HOST`
- `SMS_PROD_VM_USER`
- `SMS_PROD_VM_SSH_KEY`
- `SMS_PROD_VM_SSH_PORT`
- `SMS_PROD_DEPLOY_PATH` (`/home/vm/apps/sms/prod`)

### Mandi Management

- `MANDI_DEV_VM_HOST`
- `MANDI_DEV_VM_USER`
- `MANDI_DEV_VM_SSH_KEY`
- `MANDI_DEV_VM_SSH_PORT`
- `MANDI_DEV_DEPLOY_PATH` (`/home/vm/apps/mandi/dev`)
- `MANDI_PROD_VM_HOST`
- `MANDI_PROD_VM_USER`
- `MANDI_PROD_VM_SSH_KEY`
- `MANDI_PROD_VM_SSH_PORT`
- `MANDI_PROD_DEPLOY_PATH` (`/home/vm/apps/mandi/prod`)

### Business Tracker

- `BIZ_DEV_VM_HOST`
- `BIZ_DEV_VM_USER`
- `BIZ_DEV_VM_SSH_KEY`
- `BIZ_DEV_VM_SSH_PORT`
- `BIZ_DEV_DEPLOY_PATH` (`/home/vm/apps/biztracker/dev`)
- `BIZ_PROD_VM_HOST`
- `BIZ_PROD_VM_USER`
- `BIZ_PROD_VM_SSH_KEY`
- `BIZ_PROD_VM_SSH_PORT`
- `BIZ_PROD_DEPLOY_PATH` (`/home/vm/apps/biztracker/prod`)

## 6) Security Baselines

1. Never commit `.env` files or private keys.
2. Rotate `JWT_SECRET_KEY` and DB passwords per environment.
3. Use different SSH keys for dev vs prod deployments.
4. Keep DB credentials unique per app+environment.

