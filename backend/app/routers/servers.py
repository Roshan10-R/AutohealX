import hashlib
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from app.auth import get_current_user
from app.database import db
from app.schemas import ServerCreate
from app.utils import refresh_offline_servers, server_public, utc_now

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("")
def list_servers(user: dict = Depends(get_current_user)):
    refresh_offline_servers()
    servers = db.servers.find({"owner_id": user["_id"]}).sort("created_at", -1)
    return [server_public(server) for server in servers]


@router.post("", status_code=status.HTTP_201_CREATED)
def register_server(payload: ServerCreate, user: dict = Depends(get_current_user)):
    server_id = str(uuid4())
    api_key = secrets.token_urlsafe(32)
    server = {
        "_id": server_id,
        "owner_id": user["_id"],
        "name": payload.name.strip(),
        "host": payload.host.strip(),
        "environment": payload.environment.strip() or "production",
        "api_key_hash": hashlib.sha256(api_key.encode()).hexdigest(),
        "status": "offline",
        "last_seen": None,
        "created_at": utc_now(),
    }
    db.servers.insert_one(server)
    return server_public(server, include_key=api_key)
