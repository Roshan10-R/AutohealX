from datetime import datetime, timedelta, timezone

from app.config import HEARTBEAT_TIMEOUT_SECONDS
from app.database import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def refresh_offline_servers() -> None:
    cutoff = utc_now() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
    db.servers.update_many(
        {"status": "online", "last_seen": {"$lt": cutoff}},
        {"$set": {"status": "offline"}},
    )


def server_public(server: dict, include_key: str | None = None) -> dict:
    result = {
        "id": server["_id"],
        "name": server["name"],
        "host": server["host"],
        "environment": server["environment"],
        "status": server.get("status", "offline"),
        "last_seen": server.get("last_seen"),
        "hostname": server.get("hostname"),
        "platform": server.get("platform"),
        "latest_metrics": server.get("latest_metrics"),
        "created_at": server["created_at"],
    }
    if include_key is not None:
        result["api_key"] = include_key
    return result
