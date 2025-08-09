# services/api/src/schemas/reports.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportRead(BaseModel):
    task_id: uuid.UUID
    html_path: Optional[str] = Field(default=None)
    pdf_path: Optional[str] = Field(default=None)
    storage_url: Optional[str] = Field(default=None)
    size_bytes: Optional[int] = Field(default=None)
    checksum_sha256: Optional[str] = Field(default=None)
    created_at: datetime

    class Config:
        from_attributes = True
