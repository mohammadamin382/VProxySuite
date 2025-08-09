# services/api/src/schemas/configs.py
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


class ConfigInput(BaseModel):
    config_type: Literal["vless", "vmess"] = Field(..., description="Type of proxy configuration")
    config_raw: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)] = Field(
        ..., description="Raw VLESS/VMESS config string as provided by user"
    )
    label: Optional[str] = Field(None, max_length=120, description="Optional label/alias for the task")


class ConfigValidated(BaseModel):
    """Placeholder for a future parsed/validated structure (produced in worker)."""
    config_type: Literal["vless", "vmess"]
    normalized: dict
