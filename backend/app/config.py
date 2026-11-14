import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URL") or "mongodb://localhost:27017"
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "autohealx")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "24"))
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "90"))

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set to a long, random value.")
