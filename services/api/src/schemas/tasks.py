# services/api/src/schemas/tasks.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.configs import ConfigInput


TestKind = Literal[
    "performance",
    "stability",
    "compliance",
    "security_basic",
    "security_adv",
]


class TaskCreate(BaseModel):
    user_telegram_id: int = Field(..., ge=1, description="Telegram user id (int64)")
    username: str | None = Field(None, max_length=64)
    config: ConfigInput
    tests: list[TestKind] = Field(..., min_length=1)
    consent_required: bool = Field(False, description="If any advanced tests are requested")


class TaskRead(BaseModel):
    id: uuid.UUID
    status: Literal["pending", "running", "done", "failed", "cancelled"]
    created_at: datetime
    updated_at: datetime
    label: str | None

    class Config:
        from_attributes = True


class TaskStatus(BaseModel):
    id: uuid.UUID
    status: Literal["pending", "running", "done", "failed", "cancelled"]


class ResultRead(BaseModel):
    task_id: uuid.UUID
    score: float | None
    summary: dict
    created_at: datetime

    class Config:
        from_attributes = True
