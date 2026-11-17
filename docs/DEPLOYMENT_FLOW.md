# Deployment Flow (GitHub Actions -> Azure VM)

This repo deploys SMS dev from `main` using:

- Workflow: `.github/workflows/deploy-dev.yml`
- Deploy target: `/home/vm/apps/sms/dev`
- Runtime on VM: `podman-compose` (fallback to `docker compose`)

## 1) Trigger Conditions

The workflow runs when:

1. A push lands on `main`, or
2. A pull request targeting `main` is merged (`pull_request.closed` + `merged == true`)

This behavior is enforced by both `on:` filters and the deploy job `if` condition.

## 2) Required Secrets

Set these repository secrets:

- `VM_HOST`
- `VM_USER`
- `VM_SSH_KEY`
- `VM_SSH_PORT` (optional, defaults to `22`)
- `DEPLOY_PATH` (for this environment: `/home/vm/apps/sms/dev`)

## 3) Job Steps (Current Workflow)

### Step A: Checkout

- Uses `actions/checkout@v4` to pull current repository content in runner.

### Step B: SSH Setup

- Writes `${{ secrets.VM_SSH_KEY }}` to `~/.ssh/id_rsa`.
- Sets strict file permissions.
- Adds VM host key via `ssh-keyscan`.

### Step C: Sync Files to VM

- Uses `rsync -az --delete` over SSH.
- Excludes `.git/`.
- Synchronizes repo contents into `${DEPLOY_PATH}/`.

### Step D: Remote Rebuild/Restart

Runs remote shell script over SSH:

1. `cd "$DEPLOY_PATH"`
2. Detect compose runtime:
   - prefer `podman-compose`
   - fallback: `docker compose`
3. Execute:
   - `down || true`
   - `up -d --build`
4. Prune old images:
   - `podman image prune -f` (or docker fallback)

## 4) CI/CD Lifecycle (ASCII Sequence)

```text
Developer          GitHub                GitHub Actions Runner             Azure VM
    |                |                             |                         |
    | push/merge --> |                             |                         |
    |                | -- trigger workflow ------> |                         |
    |                |                             | checkout repo            |
    |                |                             | setup SSH key            |
    |                |                             | rsync repo ------------> |
    |                |                             | ssh remote command ----> |
    |                |                             |                          | compose down
    |                |                             |                          | compose up -d --build
    |                |                             |                          | image prune
    |                | <------ workflow result ----|                         |
```

## 5) Troubleshooting and Manual Operations

SSH into VM first:

```bash
ssh -p 22 vm@<VM_HOST>
cd /home/vm/apps/sms/dev
```

### Container status

```bash
podman ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

### Logs

```bash
podman logs --tail 200 sms_backend_dev
podman logs --tail 200 sms_frontend_dev
```

### Manual rebuild/restart

```bash
podman-compose down
podman-compose up -d --build
```

Docker fallback:

```bash
docker compose down
docker compose up -d --build
```

### Verify localhost bindings used by host Nginx

```bash
ss -ltnp | grep -E "3001|8001|5432"
```

Expected:

- `127.0.0.1:3001` (frontend)
- `127.0.0.1:8001` (backend)
- `127.0.0.1:5432` (global postgres)

