# Database Operations Runbook (`global_postgres`)

This runbook manages the shared PostgreSQL container:

- Container: `global_postgres`
- Image: `postgres:16-alpine`
- Host bind: `127.0.0.1:5432`
- Network: `app-network`

Use isolated DB/user per app+environment (`sms_dev`, `sms_prod`, etc.).

## 1) Connect to PostgreSQL

```bash
podman exec -it global_postgres psql -U admin -d postgres
```

List databases/users:

```sql
\l
\du
```

## 2) Create New Isolated Database + User

Example for a new environment `mandi_dev`:

```sql
CREATE USER mandi_dev_user WITH PASSWORD 'ReplaceWithStrongPassword!';
CREATE DATABASE mandi_dev OWNER mandi_dev_user;
GRANT ALL PRIVILEGES ON DATABASE mandi_dev TO mandi_dev_user;
```

Application `DATABASE_URL` format:

```text
postgresql://<db_user>:<db_password>@global_postgres:5432/<db_name>
```

Example:

```text
postgresql://mandi_dev_user:ReplaceWithStrongPassword!@global_postgres:5432/mandi_dev
```

## 3) Migrations Inside Backend Container

Run migrations from the backend app container for the target env stack.

### 3.1 Enter backend container

```bash
podman exec -it sms_backend_dev sh
```

### 3.2 Run migration command

If project uses Alembic:

```bash
alembic upgrade head
```

If project uses framework-specific migration scripts, run that command instead.

> Current SMS backend bootstraps tables at app startup via SQLAlchemy metadata. If/when Alembic is added, treat `alembic upgrade head` as mandatory during deployment.

## 4) Daily Automated Backups (`pg_dump` via cron)

Create backup directory:

```bash
mkdir -p /home/vm/backups/postgres
```

Create script `/home/vm/scripts/pg_backup_daily.sh`:

```bash
mkdir -p /home/vm/scripts
cat >/home/vm/scripts/pg_backup_daily.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/home/vm/backups/postgres"
DATE_TAG="$(date +%F_%H%M%S)"

# Add all managed databases here
DBS=(
  "sms_dev"
  "sms_prod"
  "mandi_dev"
  "mandi_prod"
  "biztracker_dev"
  "biztracker_prod"
)

mkdir -p "$BACKUP_DIR"

for DB in "${DBS[@]}"; do
  podman exec global_postgres pg_dump -U admin -d "$DB" -F c -f "/tmp/${DB}_${DATE_TAG}.dump"
  podman cp "global_postgres:/tmp/${DB}_${DATE_TAG}.dump" "$BACKUP_DIR/${DB}_${DATE_TAG}.dump"
  podman exec global_postgres rm -f "/tmp/${DB}_${DATE_TAG}.dump"
done

# Keep last 14 days
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +14 -delete
EOF

chmod +x /home/vm/scripts/pg_backup_daily.sh
```

Add daily cron entry (2:30 AM):

```bash
crontab -l > /tmp/current_cron 2>/dev/null || true
grep -q "pg_backup_daily.sh" /tmp/current_cron || echo "30 2 * * * /home/vm/scripts/pg_backup_daily.sh >> /home/vm/backups/postgres/backup.log 2>&1" >> /tmp/current_cron
crontab /tmp/current_cron
rm -f /tmp/current_cron
```

## 5) Restore a Single Database Safely

Example restoring `sms_dev` from one dump file:

### 5.1 Put app in maintenance window

```bash
cd /home/vm/apps/sms/dev
podman-compose down
```

### 5.2 Recreate target DB

```bash
podman exec -it global_postgres psql -U admin -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='sms_dev';"
podman exec -it global_postgres psql -U admin -d postgres -c "DROP DATABASE IF EXISTS sms_dev;"
podman exec -it global_postgres psql -U admin -d postgres -c "CREATE DATABASE sms_dev OWNER admin;"
```

### 5.3 Copy and restore dump

```bash
podman cp /home/vm/backups/postgres/sms_dev_YYYY-MM-DD_HHMMSS.dump global_postgres:/tmp/restore.dump
podman exec -it global_postgres pg_restore -U admin -d sms_dev --clean --if-exists /tmp/restore.dump
podman exec -it global_postgres rm -f /tmp/restore.dump
```

### 5.4 Bring app back

```bash
cd /home/vm/apps/sms/dev
podman-compose up -d --build
```

## 6) Health Checks

Container and DB availability:

```bash
podman ps --filter name=global_postgres
podman exec -it global_postgres psql -U admin -d postgres -c "\l"
```

