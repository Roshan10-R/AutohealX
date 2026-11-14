# AutoHealX

**Monitor your Linux servers, spot infrastructure issues, and track recovery actions from one dashboard.**

AutoHealX is a self-hosted infrastructure monitoring starter with a FastAPI backend, MongoDB storage, a React dashboard, and a Linux agent managed by systemd.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Getting started](#getting-started)
- [Install a Linux agent](#install-a-linux-agent)
- [Agent behavior and recovery](#agent-behavior-and-recovery)
- [API overview](#api-overview)
- [Security notes](#security-notes)

## Features

- Email and password signup and login.
- Register and view servers in an auto-refreshing dashboard.
- Ingest authenticated agent heartbeats, metrics, alerts, and recovery logs.
- Track CPU, memory, and disk usage trends.
- Automatically mark servers offline when heartbeats time out.
- Configure alert thresholds and opt-in service recovery.
- View recent alerts and recovery actions by server.

## Architecture

| Component | Location | Purpose |
| --- | --- | --- |
| API | `backend/app/` | Authentication, server management, agent ingestion, dashboard data |
| Dashboard | `frontend/src/` | Login, server registration, fleet health, alerts, and recovery history |
| Linux agent | `agent/` | Collect host metrics, send heartbeats, report alerts, and run configured recovery actions |
| Database | MongoDB | Stores users, server metadata, metrics, alerts, and recovery logs |

## Requirements

- Python 3.10 or later
- Node.js 18 or later
- MongoDB 6 or later (local or hosted)
- Linux with systemd for installing and running the monitoring agent

## Getting started

### 1. Configure the backend

From the project root, create a Python environment and install the API dependencies:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```bash
# Linux or macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `backend/.env` with your MongoDB connection string and a unique JWT signing secret:

```dotenv
MONGO_URL=mongodb://localhost:27017
JWT_SECRET=replace-with-a-long-random-secret
```

For a hosted MongoDB deployment, use its connection string for `MONGO_URL`. You can generate a random JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`MONGODB_URI` can be used instead of `MONGO_URL`. If both are set, `MONGODB_URI` takes precedence. The backend loads `backend/.env` automatically. **Never commit real credentials or `.env` files.**

Optional backend settings:

| Variable | Default | Description |
| --- | --- | --- |
| `MONGODB_DATABASE` | `autohealx` | MongoDB database name |
| `JWT_TTL_HOURS` | `24` | Access token lifetime in hours |
| `HEARTBEAT_TIMEOUT_SECONDS` | `90` | Time without a heartbeat before a server is marked offline |

### 2. Run the API

From the `backend` directory, with the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`; the health check is at `http://localhost:8000/health`.

### 3. Run the dashboard

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173), create an account, and register a server. The frontend defaults to the API at `http://localhost:8000`; set `VITE_API_URL` before starting or building Vite to use a different API URL.

### 4. Register a server

In the dashboard, select **Add server** and provide a name, host, and environment. Copy the generated server ID and API key: the key is shown only once and is needed to configure its agent.

## Install a Linux agent

Copy the `agent/` directory to a Linux host you administer. From that directory, install the systemd service:

```bash
sudo ./install.sh
```

Edit `/opt/autohealx/config.json` with the server ID and API key from registration. Set `api_url` to the reachable API base URL without an `/api` suffix:

```json
{
  "api_url": "https://your-api-host.example",
  "server_id": "your-server-id",
  "api_key": "your-one-time-api-key"
}
```

Then start and inspect the agent:

```bash
sudo systemctl restart autohealx-agent
sudo systemctl status autohealx-agent
sudo journalctl -u autohealx-agent -f
```

The installer keeps an existing `/opt/autohealx/config.json` when run again, so updating agent credentials or settings does not overwrite the current configuration.

## Agent behavior and recovery

The Bash collector samples CPU, memory, root filesystem usage, and nginx service status. The Python wrapper sends metrics and heartbeats at the interval configured in `agent/config.json`. Servers that exceed the heartbeat timeout are shown as offline.

Thresholds, the critical-service list, and recovery options are configured in `agent/config.json`. A failed nginx service is restarted by default. CPU and memory service restarts are opt-in: configure explicit service names in `cpu_restart_services` or `memory_restart_services`. Disk pressure is reported, but automatic file deletion is disabled to avoid accidental data loss. Recovery attempts and skipped actions are recorded in the dashboard.

## API overview

Authenticated user endpoints require a bearer access token. Agent endpoints require both `X-Server-ID` and `X-API-Key` headers.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/auth/signup` | Create an account |
| `POST` | `/api/auth/login` | Sign in |
| `GET` | `/api/servers` | List the signed-in user's servers |
| `POST` | `/api/servers` | Register a server and create its agent key |
| `GET` | `/api/dashboard` | Get server health, trends, alerts, and recovery logs |
| `POST` | `/api/agent/heartbeat` | Update server liveness and agent metadata |
| `POST` | `/api/agent/metrics` | Store server metrics |
| `POST` | `/api/agent/alerts` | Record an alert |
| `POST` | `/api/agent/healings` | Record a recovery action |
| `GET` | `/health` | Check API availability |

## Security notes

- Keep `backend/.env` and agent `config.json` files private; they contain credentials.
- User passwords are salted and hashed. Server API keys are stored as hashes and returned only at registration.
- Use HTTPS or another trusted, encrypted connection between agents, the API, and the dashboard.
- The agent installer runs with root privileges so it can restart system services. Only enable recovery actions on hosts you administer, and configure only trusted services.

