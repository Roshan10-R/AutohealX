from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import db
from app.utils import refresh_offline_servers, server_public

router = APIRouter(prefix="/api", tags=["dashboard"])


def serialize_event(event: dict) -> dict:
    result = dict(event)
    result["id"] = str(result.pop("_id"))
    return result


@router.get("/dashboard")
def dashboard(user: dict = Depends(get_current_user)):
    refresh_offline_servers()
    servers = list(db.servers.find({"owner_id": user["_id"]}).sort("created_at", -1))
    server_ids = [server["_id"] for server in servers]
    trends = {}
    for server_id in server_ids:
        points = list(
            db.metrics.find({"server_id": server_id}, {"_id": 0, "recorded_at": 1, "cpu_percent": 1, "memory_percent": 1, "disk_percent": 1})
            .sort("recorded_at", -1)
            .limit(24)
        )
        trends[server_id] = list(reversed(points))
    alerts = list(db.alerts.find({"owner_id": user["_id"]}).sort("created_at", -1).limit(50))
    healings = list(db.healing_logs.find({"owner_id": user["_id"]}).sort("created_at", -1).limit(50))
    return {
        "servers": [server_public(server) for server in servers],
        "trends": trends,
        "alerts": [serialize_event(item) for item in alerts],
        "healing_logs": [serialize_event(item) for item in healings],
        "summary": {
            "total": len(servers),
            "online": sum(server.get("status") == "online" for server in servers),
            "offline": sum(server.get("status") != "online" for server in servers),
            "active_alerts": len(alerts),
        },
    }
