# Odoo saas-19.2 — Setup Guide

This repo contains the custom addons, Docker setup, and configuration for running
Odoo `saas-19.2`. Two installation paths are supported:

| Path | Best for |
|---|---|
| [Docker](#docker-installation) | Local dev, staging, quick spin-up |
| [Direct (VM / bare-metal)](#direct-installation-vm--bare-metal) | Production on a Linux server |

---

## Directory Structure

```
repo-root/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt          ← extra Python deps (Twilio, Stripe, etc.)
├── config/
│   └── odoo.conf.example     ← copy → odoo.conf and fill in secrets
├── odoo/                     ← Odoo saas-19.2 source (clone manually, gitignored)
├── enterprise/               ← enterprise addons (optional, gitignored)
└── addons/                   ← all custom modules live here
```

---

## Docker Installation

### Prerequisites
- [Docker](https://docs.docker.com/engine/install/) with the Compose plugin
- Git

### 1. Clone this repo

```bash
git clone <your-repo-url> odoo19.2
cd odoo19.2
```

### 2. Clone the Odoo saas-19.2 source

```bash
git clone --depth=1 --branch saas-19.2 https://github.com/odoo/odoo ./odoo
```

### 3. Clone enterprise addons (optional — requires Odoo partner access)

```bash
git clone --depth=1 --branch saas-19.2 https://github.com/odoo/enterprise ./enterprise
```

Leave `./enterprise` empty if you don't have access — it will still mount fine.

### 4. Create your odoo.conf

```bash
cp config/odoo.conf.example config/odoo.conf
# Edit config/odoo.conf — set admin_passwd and db_name at minimum
```

### 5. Build and start

```bash
docker compose build
docker compose up -d
```

The first build takes several minutes as it compiles all system and Python dependencies.

### 6. Open Odoo

Go to [http://localhost:8069](http://localhost:8069) and create your first database.

### Day-to-day commands

```bash
docker compose restart web          # restart after config or addon changes
docker compose logs -f web          # tail logs
docker compose down                 # stop everything
```

---

## Direct Installation (VM / Bare-metal)

Use this path for production on a Linux server (Ubuntu 22.04 / 24.04 recommended).

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- `wkhtmltopdf` (for PDF reports)
- `npm` + `rtlcss` (for RTL support)
- `git`

### 1. Install system dependencies

```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential libpq-dev postgresql-client \
    libxml2-dev libxslt1-dev libjpeg-dev libpng-dev libfreetype6-dev \
    libldap2-dev libsasl2-dev libssl-dev \
    fonts-dejavu-core fonts-font-awesome fonts-roboto-unhinted gsfonts \
    wkhtmltopdf npm git curl

sudo npm install -g rtlcss
```

### 2. Create the odoo system user

```bash
sudo useradd -ms /bin/bash odoo19
```

### 3. Clone the Odoo saas-19.2 source

```bash
sudo mkdir -p /opt/odoo19
sudo git clone --depth=1 --branch saas-19.2 https://github.com/odoo/odoo /opt/odoo19/odoo
sudo chown -R odoo19:odoo19 /opt/odoo19
```

### 4. Set up a Python virtual environment

```bash
sudo -u odoo19 python3 -m venv /opt/odoo19/venv
sudo -u odoo19 /opt/odoo19/venv/bin/pip install --upgrade pip
sudo -u odoo19 /opt/odoo19/venv/bin/pip install -r /opt/odoo19/odoo/requirements.txt
```

### 5. Install extra Python dependencies from this repo

```bash
sudo -u odoo19 /opt/odoo19/venv/bin/pip install -r /path/to/this-repo/requirements.txt
```

### 6. Clone this repo (custom addons)

```bash
sudo git clone <your-repo-url> /opt/odoo19/custom-addons
sudo chown -R odoo19:odoo19 /opt/odoo19/custom-addons
```

### 7. (Optional) Clone enterprise addons

```bash
sudo -u odoo19 git clone --depth=1 --branch saas-19.2 \
    https://github.com/odoo/enterprise /opt/odoo19/enterprise
```

### 8. Create the Odoo config file

```bash
sudo cp /opt/odoo19/custom-addons/config/odoo.conf.example /etc/odoo19.conf
sudo nano /etc/odoo19.conf   
# fill in db credentials, admin_passwd, addons_path
```

Key `addons_path` for a direct install:

```ini
addons_path = /opt/odoo19/odoo/addons,/opt/odoo19/custom-addons/addons,/opt/odoo19/enterprise
```

### 9. Set up PostgreSQL

```bash
sudo -u postgres createuser -s odoo19
sudo -u postgres psql -c "ALTER USER odoo19 WITH PASSWORD 'yourpassword';"
```

### 10. Create a systemd service

```bash
sudo nano /etc/systemd/system/odoo19.service
```

Paste:

```ini
[Unit]
Description=Odoo 19
After=network.target postgresql.service

[Service]
User=odoo19
ExecStart=/opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin \
    --config=/etc/odoo19.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now odoo19
sudo systemctl status odoo19
```

### 11. Open Odoo

Go to `http://<your-server-ip>:8069` and create your first database.

### Day-to-day commands

```bash
sudo systemctl restart odoo19                        # restart after Python/model changes

# Upgrade a module (no restart needed after)
sudo -u odoo19 /opt/odoo19/venv/bin/python3 /opt/odoo19/odoo/odoo-bin \
    -c /etc/odoo19.conf -d <db_name> -u <module_name> --stop-after-init

sudo journalctl -u odoo19 -f                         # tail logs
```

---

## Custom Addons

Place modules inside `./addons/`. Each module must have `__init__.py` and `__manifest__.py`:

```
addons/
└── my_module/
    ├── __init__.py
    ├── __manifest__.py
    └── ...
```

After adding a module, update the app list from **Settings → Apps → Update Apps List**
(or use `-u <module_name>` on the CLI).

---

## Configuration Reference

Key options in `config/odoo.conf.example`:

| Option | Description |
|---|---|
| `addons_path` | Comma-separated list of addon directories |
| `admin_passwd` | Master password for database management |
| `db_name` | Default database name |
| `dbfilter` | Regex filter — restrict which DBs are accessible |
| `list_db` | Set `False` in production to hide the DB list |
| `proxy_mode` | Set `True` when behind nginx/reverse proxy |
| `workers` | `0` = single-threaded (dev); set `4`+ for production |

---

## Useful Commands

```bash
# View logs
docker compose logs -f web

# Restart web only (picks up odoo.conf changes)
docker compose restart web

# Rebuild image after odoo source changes
docker compose build web
docker compose up -d

# Stop everything
docker compose down

# Stop and delete volumes (destroys database)
docker compose down -v
```

---

## Switching to Cloud SQL

To replace the local `db` container with Cloud SQL:

1. Add the Cloud SQL Auth Proxy as a service in `docker-compose.yml`:

```yaml
cloudsql-proxy:
  image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:latest
  command: --address 0.0.0.0 <PROJECT>:<REGION>:<INSTANCE>
  volumes:
    - ./service-account.json:/config/service-account.json:ro
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS=/config/service-account.json
```

2. Update `odoo.conf`:

```ini
db_host = cloudsql-proxy
db_user = <cloud-sql-user>
db_password = <cloud-sql-password>
```

3. Remove the `db` service and `odoo-db-data-19-2` volume from `docker-compose.yml`.
