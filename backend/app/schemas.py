from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    host: str = Field(min_length=1, max_length=255)
    environment: str = Field(default="production", max_length=64)

    @field_validator("name", "host")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank")
        return value


class ServerResponse(BaseModel):
    id: str
    name: str
    host: str
    environment: str
    status: Literal["online", "offline"]
    last_seen: datetime | None = None
    hostname: str | None = None
    platform: str | None = None
    latest_metrics: dict | None = None
    created_at: datetime
    api_key: str | None = None


class HeartbeatPayload(BaseModel):
    agent_version: str = Field(default="1.0.0", max_length=32)
    hostname: str | None = Field(default=None, max_length=255)
    platform: str | None = Field(default=None, max_length=255)


class MetricsPayload(BaseModel):
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    disk_percent: float = Field(ge=0, le=100)
    nginx_active: bool | None = None
    model_config = ConfigDict(extra="forbid")


class AlertPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    severity: Literal["info", "warning", "critical"] = "warning"


class HealingPayload(BaseModel):
    issue: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=500)
    result: Literal["success", "failed", "skipped"]
    details: str | None = Field(default=None, max_length=2000)
