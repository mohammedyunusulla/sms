# VM Readiness Runbook (Ubuntu 26.04 LTS on Azure)

This runbook provisions a fresh VM for the SMS dev stack using:

- VM size: `Standard_B2als_v2`
- OS: Ubuntu 26.04 LTS
- Runtime: rootless Podman + podman-compose
- Reverse proxy: host Nginx + Certbot SSL

The steps below are written to be reproducible end-to-end.

## 0) Prerequisites

- DNS A record for `dev-sms.klopterz.in` points to VM public IP.
- Inbound ports open in NSG/firewall: `22`, `80`, `443`.
- A non-root deploy user exists on VM (examples below use user `vm`).

## 1) Update System + Configure 4 GB Swap

```bash
sudo apt update
sudo apt -y upgrade

sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

swapon --show
free -h
```

## 2) Install Podman, podman-compose, Nginx, Certbot

```bash
sudo apt install -y podman podman-compose nginx certbot python3-certbot-nginx

podman --version
podman-compose --version
nginx -v
certbot --version
```

## 3) Enable Lingering for Rootless Podman

This keeps user services/containers alive after SSH logout.

```bash
sudo loginctl enable-linger vm
loginctl show-user vm | grep Linger
```

Expected output includes:

```text
Linger=yes
```

## 4) Configure Docker Hub as Default Unqualified Registry

Create `/etc/containers/registries.conf.d/00-dockerhub.conf`:

```bash
sudo mkdir -p /etc/containers/registries.conf.d
cat <<'EOF' | sudo tee /etc/containers/registries.conf.d/00-dockerhub.conf
unqualified-search-registries = ["docker.io"]
EOF
```

## 5) Create Shared Network + Central PostgreSQL

### 5.1 Create shared bridge network

Run as deploy user (`vm`), not root:

```bash
podman network inspect app-network >/dev/null 2>&1 || podman network create app-network
podman network ls
```

### 5.2 Start central postgres container

```bash
podman volume create global_postgres_data

podman run -d \
  --name global_postgres \
  --network app-network \
  -p 127.0.0.1:5432:5432 \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD='ChangeThisStrongPassword123!' \
  -e POSTGRES_DB=sms_dev \
  -v global_postgres_data:/var/lib/postgresql/data \
  --restart=always \
  postgres:16-alpine
```

Validate:

```bash
podman ps --filter name=global_postgres
podman logs --tail 100 global_postgres
```

### 5.3 (Optional) Create additional isolated databases for other apps/envs

```bash
podman exec -it global_postgres psql -U admin -d postgres
```

Then in `psql`:

```sql
CREATE DATABASE sms_prod;
CREATE DATABASE another_app_dev;
```

## 6) Configure Nginx Reverse Proxy + SSL

### 6.1 Create vhost

```bash
sudo tee /etc/nginx/sites-available/dev-sms.klopterz.in >/dev/null <<'EOF'
server {
    listen 80;
    server_name dev-sms.klopterz.in;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/dev-sms.klopterz.in /etc/nginx/sites-enabled/dev-sms.klopterz.in
sudo nginx -t
sudo systemctl reload nginx
```

### 6.2 Issue Let's Encrypt certificate

```bash
sudo certbot --nginx -d dev-sms.klopterz.in
```

Verify renewal timer:

```bash
systemctl list-timers | grep certbot
```

## 7) Prepare App Directory + GitHub Actions SSH Access

### 7.1 Create deploy directory structure

```bash
mkdir -p /home/vm/apps/sms/dev
```

### 7.2 Configure SSH key auth for GitHub Actions

On VM (user `vm`):

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Append GitHub Actions public key:

```bash
echo "<YOUR_GITHUB_ACTIONS_PUBLIC_KEY>" >> ~/.ssh/authorized_keys
```

## 8) GitHub Repository Secret Mapping

Set these secrets in GitHub repo:

- `VM_HOST` = VM public DNS/IP
- `VM_USER` = `vm`
- `VM_SSH_KEY` = private key matching the public key in `authorized_keys`
- `VM_SSH_PORT` = `22` (or custom port)
- `DEPLOY_PATH` = `/home/vm/apps/sms/dev`

## 9) First Deploy Verification

After merging/pushing to `main`, verify:

```bash
cd /home/vm/apps/sms/dev
podman-compose ps
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl -I http://127.0.0.1:3001
curl -I http://127.0.0.1:8001
```

Then from browser:

- `https://dev-sms.klopterz.in/`
- `https://dev-sms.klopterz.in/api/`

