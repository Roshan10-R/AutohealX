from pymongo import ASCENDING, DESCENDING, MongoClient

from app.config import MONGODB_DATABASE, MONGODB_URI

_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = _client[MONGODB_DATABASE]


def ensure_indexes() -> None:
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.servers.create_index([("owner_id", ASCENDING)])
    db.servers.create_index([("last_seen", DESCENDING)])
    db.metrics.create_index([("server_id", ASCENDING), ("recorded_at", DESCENDING)])
    db.alerts.create_index([("owner_id", ASCENDING), ("created_at", DESCENDING)])
    db.healing_logs.create_index([("owner_id", ASCENDING), ("created_at", DESCENDING)])
