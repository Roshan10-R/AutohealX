# AutoHealX

AutoHealX is a lightweight Linux infrastructure monitoring and recovery starter: a FastAPI + MongoDB API, a React/Vite dashboard, and a systemd-managed Linux agent.

## Requirements

- Python 3.10+
- Node.js 18+
- MongoDB 6+ (local or hosted)
- Linux host for the monitoring agent; `systemd` is used for installation and recovery actions

## Run locally

### 1. Start MongoDB

For a local MongoDB installation, start its service and leave it listening at `mongodb://localhost:27017`. For a hosted database, put its connection string in `backend/.env` as `MONGO_URL` or `MONGODB_URI`; the backend loads that file automatically. Do not commit the connection string.

### 2. Start the API

From the repository root, in a terminal:

```bash
cd backend
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set a long, unique `JWT_SECRET` in `backend/.env` before starting the API. Generate one with:

```bash
python -c 'import secrets; print(secrets.token_hex(32))'
```

Add the generated value as `JWT_SECRET=...` alongside your MongoDB URL in `backend/.env`. Alternatively, export `JWT_SECRET` in the shell before starting the API. The API is at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`. Optional environment variables: `MONGODB_DATABASE`, `JWT_TTL_HOURS`, and `HEARTBEAT_TIMEOUT_SECONDS` (default 90).

Start the API from the `backend` directory:

```bash
uvicorn app.main:app --reload
```

### 3. Start the dashboard

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, create an account, and register a server. For a non-default API URL, set `VITE_API_URL` before starting or building Vite.

### 4. Install an agent on a Linux server

Register a server in the dashboard and copy its server ID and one-time API key. On the Linux host, copy the `agent/` directory, then:

```bash
cd agent
sudo ./install.sh
sudo nano /opt/autohealx/config.json
sudo systemctl restart autohealx-agent
sudo systemctl status autohealx-agent
journalctl -u autohealx-agent -f
```

Set `api_url` to the reachable API base URL (no `/api` suffix), then fill in `server_id` and `api_key`. Keep the API key private. The installer preserves an existing config on subsequent runs.

## Agent checks and recovery behavior

The Bash collector samples CPU, memory, root filesystem usage, and nginx service state. The Python wrapper sends heartbeats and metrics, and reports threshold alerts. The dashboard considers a server offline when its last heartbeat is older than `HEARTBEAT_TIMEOUT_SECONDS`.

Thresholds and the critical-service list are configured in `agent/config.json`. A failed nginx service is restarted by default. CPU and memory recovery is opt-in: add specific, trusted systemd service names to `cpu_restart_services` or `memory_restart_services`. Disk pressure is alerted but cleanup is intentionally not automated; automatic deletion can cause data loss. Recovery attempts and skipped actions are recorded in the dashboard.

The agent needs root privileges for systemd restarts, so only install this agent on hosts you administer. Server credentials are sent in headers and should only be used over a trusted network or TLS-enabled API endpoint.

## API outline

- `POST /api/auth/signup`, `POST /api/auth/login`
- `GET /api/servers`, `POST /api/servers` (authenticated)
- `GET /api/dashboard` (authenticated; includes servers, recent alerts/recoveries, and up to 24 trend points per server)
- `POST /api/agent/heartbeat`, `/metrics`, `/alerts`, `/healings` (`X-Server-ID` and `X-API-Key` headers)
- `GET /health`

MongoDB indexes are initialized at API startup. User passwords are salted and hashed; server API keys are stored as SHA-256 hashes and only returned once at registration.
