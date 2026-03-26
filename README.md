# Odoo saas-19.2 — Docker Setup

Runs Odoo `saas-19.2` from source using Docker Compose. The Odoo source is baked into
the image at build time; custom addons and enterprise addons are mounted at runtime.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) (with the Compose plugin)
- Git

## Directory Structure

```
odoo19.2/
├── Dockerfile
├── docker-compose.yml
├── odoo.conf
├── odoo/               ← saas-19.2 source (cloned below)
├── enterprise/         ← enterprise addons (optional)
└── addons/             ← your custom addons go here
```

## Installation

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

If you don't have enterprise access, the `./enterprise` directory can stay empty.

### 4. Fix permissions on addon directories

```bash
chmod -R o+rX ./addons ./enterprise
```

### 5. Build and start

```bash
docker compose build
docker compose up -d
```

The first build takes several minutes as it installs all Python and system dependencies.

### 6. Open Odoo

Navigate to [http://localhost:8069](http://localhost:8069) (or whichever port is set in
`docker-compose.yml`) and create your first database.

---

## Custom Addons

Place your custom modules inside `./addons/`:

```
addons/
└── my_module/
    ├── __init__.py
    ├── __manifest__.py
    └── ...
```

No rebuild is needed — the directory is mounted directly. After adding a module,
restart the container and update the app list from **Settings → Apps → Update Apps List**.

```bash
docker compose restart web
```

---

## Configuration

All Odoo settings are in `odoo.conf`. Key options:

| Option           | Default   | Description                                          |
| ---------------- | --------- | ---------------------------------------------------- |
| `db_host`        | `db`      | Postgres host (Docker service name)                  |
| `db_user`        | `odoo`    | Postgres user                                        |
| `db_password`    | `odoo`    | Postgres password                                    |
| `http_interface` | `0.0.0.0` | Listen on all interfaces                             |
| `workers`        | `0`       | `0` = single-threaded (dev); increase for production |

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
