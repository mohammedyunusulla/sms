# Ubuntu/Linux Deployment Guide
# School Management System Backend

## Prerequisites Installation

### 1. Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Python 3.10+ and pip
```bash
sudo apt install python3 python3-pip python3-venv -y
python3 --version  # Should be 3.10 or higher
```

### 3. Install PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 4. Configure PostgreSQL
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, run:
CREATE DATABASE skool_main;
CREATE USER postgres WITH PASSWORD 'postgres';
ALTER USER postgres WITH SUPERUSER;
GRANT ALL PRIVILEGES ON DATABASE skool_main TO postgres;
\q
```

### 5. Install Git (if not installed)
```bash
sudo apt install git -y
```

---

## Application Setup

### 1. Clone or Transfer Project
```bash
# If using git
git clone <repository-url>
cd school-management-backend

# Or upload files to server
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Edit .env file
nano .env

# Update these values:
# POSTGRES_HOST=127.0.0.1
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=postgres
# POSTGRES_PORT=5432
```

### 5. Make Scripts Executable
```bash
chmod +x init_db.sh
chmod +x run.sh
chmod +x run-production.sh
chmod +x run-main_dbupgrade.sh
chmod +x run-tenant_dbupgrade.sh
chmod +x run-dbupgrade.sh
```

### 6. Initialize Database
```bash
./init_db.sh
```

This will:
- Create database migrations
- Apply migrations to main database
- Create super admin user (username: admin, password: admin123)

---

## Running the Application

### Development Mode
```bash
./run.sh
# Or manually:
source venv/bin/activate
python3 run.py
```

### Production Mode (Gunicorn)
```bash
./run-production.sh
# Or manually:
source venv/bin/activate
gunicorn --workers 4 --bind 0.0.0.0:5000 "app:create_app()"
```

---

## Database Migrations

### Upgrade Main Database
```bash
./run-main_dbupgrade.sh
# Or manually:
source venv/bin/activate
alembic -c migrations_main/alembic_main.ini revision --autogenerate -m "Update"
alembic -c migrations_main/alembic_main.ini upgrade head
```

### Upgrade Tenant Databases
```bash
./run-tenant_dbupgrade.sh
# Or manually:
source venv/bin/activate
alembic -c migrations_tenant/alembic_tenant.ini revision --autogenerate -m "Update"
alembic -c migrations_tenant/alembic_tenant.ini upgrade head
```

---

## Setting Up as System Service (Production)

### 1. Create systemd service file
```bash
sudo nano /etc/systemd/system/school-management.service
```

### 2. Add this configuration:
```ini
[Unit]
Description=School Management System Backend
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/school-management-backend
Environment="PATH=/path/to/school-management-backend/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/path/to/school-management-backend/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile /path/to/school-management-backend/logs/access.log \
    --error-logfile /path/to/school-management-backend/logs/error.log \
    "app:create_app()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Enable and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable school-management
sudo systemctl start school-management
sudo systemctl status school-management
```

### 4. Service management commands
```bash
sudo systemctl start school-management     # Start
sudo systemctl stop school-management      # Stop
sudo systemctl restart school-management   # Restart
sudo systemctl status school-management    # Check status
sudo journalctl -u school-management -f    # View logs
```

---

## Nginx Setup (Reverse Proxy)

### 1. Install Nginx
```bash
sudo apt install nginx -y
```

### 2. Create Nginx configuration
```bash
sudo nano /etc/nginx/sites-available/school-management
```

### 3. Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Serve static files (if any)
    location /static {
        alias /path/to/school-management-backend/static;
        expires 30d;
    }
}
```

### 4. Enable site and restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/school-management /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### 5. Setup SSL with Let's Encrypt (Optional)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL (if external access needed)
sudo ufw allow 5432/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## Monitoring and Logs

### View Application Logs
```bash
# If running as service
sudo journalctl -u school-management -f

# Manual logs
tail -f logs/app.log
tail -f logs/access.log
tail -f logs/error.log
```

### PostgreSQL Logs
```bash
sudo tail -f /var/log/postgresql/postgresql-*.log
```

---

## Backup and Maintenance

### Backup Main Database
```bash
pg_dump -U postgres -h 127.0.0.1 skool_main > backup_main_$(date +%Y%m%d).sql
```

### Backup All Tenant Databases
```bash
# List all databases starting with skool_
psql -U postgres -h 127.0.0.1 -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'skool_%';" | while read dbname; do
    if [ ! -z "$dbname" ]; then
        pg_dump -U postgres -h 127.0.0.1 "$dbname" > "backup_${dbname}_$(date +%Y%m%d).sql"
    fi
done
```

### Restore Database
```bash
psql -U postgres -h 127.0.0.1 skool_main < backup_main_20250102.sql
```

---

## Troubleshooting

### Check if PostgreSQL is running
```bash
sudo systemctl status postgresql
```

### Check if port 5000 is in use
```bash
sudo lsof -i :5000
```

### Test database connection
```bash
psql -U postgres -h 127.0.0.1 -d skool_main -c "SELECT version();"
```

### Check Python environment
```bash
source venv/bin/activate
pip list
python3 -c "import flask; print(flask.__version__)"
```

### Permission issues
```bash
# Fix ownership
sudo chown -R www-data:www-data /path/to/school-management-backend

# Fix permissions
chmod -R 755 /path/to/school-management-backend
chmod +x *.sh
```

---

## Performance Tuning

### PostgreSQL Configuration
Edit `/etc/postgresql/*/main/postgresql.conf`:
```ini
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 8MB
min_wal_size = 1GB
max_wal_size = 4GB
max_connections = 100
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## Security Checklist

- [ ] Change default admin password
- [ ] Update SECRET_KEY and JWT_SECRET_KEY in .env
- [ ] Configure firewall (ufw)
- [ ] Setup SSL certificate
- [ ] Disable PostgreSQL remote access (if not needed)
- [ ] Regular database backups
- [ ] Keep system and packages updated
- [ ] Monitor logs regularly
- [ ] Use strong passwords for database users

---

## Quick Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Start development server
./run.sh

# Start production server
./run-production.sh

# Initialize database (first time)
./init_db.sh

# Upgrade main database
./run-main_dbupgrade.sh

# Check application status (if service)
sudo systemctl status school-management

# View logs
sudo journalctl -u school-management -f

# Restart application
sudo systemctl restart school-management

# Backup database
pg_dump -U postgres -h 127.0.0.1 skool_main > backup.sql
```

---

For more information, refer to the main README.md file.
