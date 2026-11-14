import hashlib
import hmac
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.database import db
from app.schemas import AlertPayload, HealingPayload, HeartbeatPayload, MetricsPayload
from app.utils import utc_now

router = APIRouter(prefix="/api/agent", tags=["agent"])


def authenticated_server(
    server_id: str = Header(alias="X-Server-ID"),
    api_key: str = Header(alias="X-API-Key"),
) -> dict:
    server = db.servers.find_one({"_id": server_id})
    provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
    if server is None or not hmac.compare_digest(server.get("api_key_hash", ""), provided_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid server credentials")
    return server


@router.post("/heartbeat")
def heartbeat(payload: HeartbeatPayload, server: dict = Depends(authenticated_server)):
    now = utc_now()
    updates = {"status": "online", "last_seen": now, "agent_version": payload.agent_version}
    if payload.hostname:
        updates["hostname"] = payload.hostname
    if payload.platform:
        updates["platform"] = payload.platform
    db.servers.update_one({"_id": server["_id"]}, {"$set": updates})
    return {"ok": True, "server_id": server["_id"], "received_at": now}


@router.post("/metrics", status_code=status.HTTP_201_CREATED)
def ingest_metrics(payload: MetricsPayload, server: dict = Depends(authenticated_server)):
    now = utc_now()
    metric = payload.model_dump()
    metric.update({"server_id": server["_id"], "owner_id": server["owner_id"], "recorded_at": now})
    db.metrics.insert_one(metric)
    db.servers.update_one({"_id": server["_id"]}, {"$set": {"latest_metrics": {**payload.model_dump(), "recorded_at": now}}})
    return {"ok": True, "recorded_at": now}


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
def ingest_alert(payload: AlertPayload, server: dict = Depends(authenticated_server)):
    alert = {
        "_id": uuid4().hex,
        "server_id": server["_id"],
        "server_name": server["name"],
        "owner_id": server["owner_id"],
        **payload.model_dump(),
        "created_at": utc_now(),
    }
    db.alerts.insert_one(alert)
    alert["id"] = alert.pop("_id")
    return alert


@router.post("/healings", status_code=status.HTTP_201_CREATED)
def ingest_healing(payload: HealingPayload, server: dict = Depends(authenticated_server)):
    log = {
        "_id": uuid4().hex,
        "server_id": server["_id"],
        "server_name": server["name"],
        "owner_id": server["owner_id"],
        **payload.model_dump(),
        "created_at": utc_now(),
    }
    db.healing_logs.insert_one(log)
    log["id"] = log.pop("_id")
    return log
