# services/worker/src/core/parsers.py
from __future__ import annotations

import base64
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Optional

import idna
from pydantic import BaseModel, ValidationError
from yarl import URL


# -----------------------------
# Public models
# -----------------------------
class ConfigType(str):
    VLESS = "vless"
    VMESS = "vmess"


class ParsedVLESS(BaseModel):
    type: Literal["vless"] = "vless"
    id: uuid.UUID
    host: str
    port: int
    sni: Optional[str] = None
    security: Optional[str] = None  # e.g., "tls", "reality", "none"
    network: Optional[str] = None  # ws, grpc, tcp
    path: Optional[str] = None
    alpn: Optional[str] = None
    flow: Optional[str] = None
    name: Optional[str] = None
    params: dict[str, Any] = {}


class ParsedVMESS(BaseModel):
    type: Literal["vmess"] = "vmess"
    id: uuid.UUID
    host: str
    port: int
    aid: Optional[int] = None
    net: Optional[str] = None
    type_field: Optional[str] = None  # 'type' conflicts with BaseModel
    tls: Optional[str] = None
    sni: Optional[str] = None
    host_header: Optional[str] = None
    path: Optional[str] = None
    name: Optional[str] = None
    raw: dict[str, Any] = {}


ParsedConfig = ParsedVLESS | ParsedVMESS


@dataclass(frozen=True)
class ParseResult:
    config: ParsedConfig
    warnings: list[str]


# -----------------------------
# Utilities
# -----------------------------
_DOMAIN_RE = re.compile(r"^(?=.{1,253}\.?$)([a-zA-Z0-9-_]{1,63}\.)+[a-zA-Z]{2,63}\.?$")
_IPV4_RE = re.compile(
    r"^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$"
)
_IPV6_RE = re.compile(r"^\[?[0-9a-fA-F:]+\]?$")


def _validate_hostname(host: str) -> str:
    host = host.strip()
    if _IPV4_RE.match(host) or _IPV6_RE.match(host):
        return host
    try:
        _ = idna.encode(host, uts46=True).decode("ascii")
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"invalid hostname: {host}") from e
    if not _DOMAIN_RE.search(host + ".") and "." not in host:
        # Accept single-label in dev but warn; still allow via IDNA check
        pass
    return host


def _validate_port(port: int | str) -> int:
    try:
        p = int(str(port).strip())
    except Exception as e:  # noqa: BLE001
        raise ValueError("port must be int") from e
    if not (1 <= p <= 65535):
        raise ValueError("port out of range")
    return p


# -----------------------------
# VLESS
# -----------------------------
def parse_vless(uri: str) -> ParseResult:
    """
    vless://<uuid>@host:port?security=tls&encryption=none&type=ws&path=/#name
    """
    url = URL(uri)
    if url.scheme.lower() != "vless":
        raise ValueError("not a vless uri")

    # username part is UUID
    try:
        user_id = uuid.UUID(url.user or "")
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid vless uuid") from e

    host = _validate_hostname(url.host or "")
    port = _validate_port(url.port or 0)

    q = dict(url.query)
    warnings: list[str] = []

    sni = q.get("sni") or q.get("serverName")
    security = q.get("security")
    network = q.get("type") or q.get("network")
    path = q.get("path")
    alpn = q.get("alpn")
    flow = q.get("flow")

    name = url.fragment or None
    params = {k: v for k, v in q.items() if k not in {"sni", "serverName", "security", "type", "network", "path", "alpn", "flow"}}

    model = ParsedVLESS(
        id=user_id,
        host=host,
        port=port,
        sni=sni,
        security=security,
        network=network,
        path=path,
        alpn=alpn,
        flow=flow,
        name=name,
        params=params,
    )

    # Basic sanity warnings
    if (security or "").lower() in {"", "none", "insecure"}:
        warnings.append("VLESS without TLS/REALITY; may leak metadata.")
    if network == "ws" and not path:
        warnings.append("WebSocket selected but path is empty.")
    return ParseResult(config=model, warnings=warnings)


# -----------------------------
# VMESS
# -----------------------------
def _b64pad(s: str) -> str:
    return s + "=" * ((4 - (len(s) % 4)) % 4)


def parse_vmess(uri: str) -> ParseResult:
    """
    Two common forms:
      1) vmess://<base64-JSON>
      2) vnext uri form (rare) — we primarily support base64-JSON.
    """
    if not uri.lower().startswith("vmess://"):
        raise ValueError("not a vmess uri")

    payload = uri[len("vmess://") :]
    warnings: list[str] = []

    try:
        decoded = base64.urlsafe_b64decode(_b64pad(payload)).decode("utf-8", errors="replace")
        data = json.loads(decoded)
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid vmess base64/json") from e

    # Typical fields
    # v, ps(name), add(host), port, id(uuid), aid, net, type, host, path, tls, sni
    try:
        user_id = uuid.UUID(str(data.get("id", "")).strip())
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid vmess uuid") from e

    host = _validate_hostname(str(data.get("add", "")).strip())
    port = _validate_port(data.get("port", 0))
    aid = None
    try:
        if "aid" in data and str(data["aid"]).strip():
            aid = int(str(data["aid"]).strip())
    except Exception:
        warnings.append("vmess 'aid' is not numeric; ignored.")

    net = (data.get("net") or "").strip() or None
    type_field = (data.get("type") or "").strip() or None
    tls = (data.get("tls") or "").strip() or None
    sni = (data.get("sni") or "").strip() or None
    host_header = (data.get("host") or "").strip() or None
    path = (data.get("path") or "").strip() or None
    name = (data.get("ps") or "").strip() or None

    model = ParsedVMESS(
        id=user_id,
        host=host,
        port=port,
        aid=aid,
        net=net,
        type_field=type_field,
        tls=tls,
        sni=sni,
        host_header=host_header,
        path=path,
        name=name,
        raw=data,
    )

    if (tls or "").lower() in {"", "none", "insecure"}:
        warnings.append("VMESS without TLS; traffic may be observable.")
    if net == "ws" and not path:
        warnings.append("WebSocket selected but path is empty.")
    return ParseResult(config=model, warnings=warnings)


# -----------------------------
# Unified entry
# -----------------------------
def parse_config(raw: str) -> ParseResult:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty config")
    if raw.lower().startswith("vless://"):
        return parse_vless(raw)
    if raw.lower().startswith("vmess://"):
        return parse_vmess(raw)
    raise ValueError("unsupported config type (expect vless:// or vmess://)")
