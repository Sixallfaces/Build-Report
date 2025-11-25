# Build-Report Project
Build-Report is an automatic deployment and reporting system for construction projects. It combines a FastAPI backend, SQLite storage, and a small static frontend to collect, verify, and publish daily work reports with photo evidence.

## Features
- **FastAPI backend** with modular routers for works, materials, reports, categories, foremen, and authentication endpoints.
- **SQLite database** initialized and migrated at startup, tracking works, materials, foremen, work reports, and access control.
- **Yandex Disk integration** to create and publish per-foreman folders for photo reports when credentials are provided.
- **Static frontend build pipeline** for the dashboard UI (HTML/CSS/JS) with minification/obfuscation via `build.sh`.
- **Telegram bot support** (see `apps/bot.py`) for delivering notifications and collecting data from chat.

## Project Structure
- `apps/main.py` – FastAPI entrypoint that configures CORS, mounts routers, and runs database setup.
- `apps/config.py` – Environment-driven settings (API host/port, database path, CORS origins, Yandex Disk tokens, bot configuration, VAT rate, logging).
- `apps/database.py` – Async SQLite connection helpers plus schema creation and upgrade routines executed on startup.
- `apps/routers/` – Route modules that expose CRUD operations for works, materials, categories, foremen, report submissions, and auth flows.
- `apps/static/` – Frontend assets (HTML, CSS, JS) used by the reporting dashboard; JavaScript is compiled/minified into `app.min.js` during builds.
- `build.sh` – Convenience script that minifies and obfuscates `apps/static/js/app.js` using `terser` and `javascript-obfuscator`.
- `systemd/` & `nginx/` – Deployment unit files and reverse-proxy configuration examples for production hosting.

## Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend build pipeline)
- SQLite (bundled with Python, used via `aiosqlite`)

## Installation
1. Create and activate a virtual environment.
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install Python dependencies.
   ```bash
   pip install -r requirements.txt
   ```
3. Install Node.js dev dependencies (for optional frontend build).
   ```bash
   npm install
   ```

## Configuration
All configuration is read from environment variables (see defaults in `apps/config.py`). Common settings include:
- `DATABASE_PATH` – Path to the SQLite database file (default: `/opt/stroykontrol/database/stroykontrol.db`).
- `API_HOST` / `API_PORT` – Bind address and port for the FastAPI server (defaults: `127.0.0.1:8000`).
- `CORS_ORIGINS` – Comma-separated list of allowed origins for the frontend (default: `https://build-report.ru`).
- `YANDEX_DISK_TOKEN`, `YANDEX_DISK_BASE_FOLDER`, `YANDEX_DISK_PEOPLE_REPORTS_FOLDER` – Credentials and base folders for publishing reports to Yandex Disk.
- `BOT_TOKEN`, `MANAGER_USER_IDS` – Telegram bot authentication and manager access control.
- `SECRET_KEY`, `VAT_RATE`, `LOG_LEVEL`, `TIMEZONE` – Security, financial, and logging defaults.

## Running the API Server
Start the FastAPI server locally with hot reload during development:
```bash
uvicorn apps.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup the app will initialize and migrate the SQLite schema automatically. Health checks are available at `/health`, and a simple root response at `/` reports the API status.

## Building Frontend Assets
If you edit `apps/static/js/app.js`, run the build script to generate the obfuscated bundle:
```bash
./build.sh
```
The script produces `apps/static/js/app.min.js` and leaves CSS/HTML editable without rebuilds.

## Testing
Run the Python test suite (pytest and async fixtures are included in `requirements.txt`):
```bash
pytest
```

## Deployment Notes
- Sample systemd unit files are provided in `systemd/` to run the API with uvicorn under a service account.
- Example Nginx configuration in `nginx/` demonstrates reverse proxy setup for TLS termination and static file serving.
- For production, set `LOG_LEVEL=INFO` (or higher) and ensure `SECRET_KEY`, `YANDEX_DISK_TOKEN`, and database paths are configured via environment variables before starting the service
