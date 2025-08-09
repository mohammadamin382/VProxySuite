# services/worker/src/plugins/base.py
from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional

from config.settings import get_settings

settings = get_settings()

# Canonical kinds (must match API schemas)
KIND_PERFORMANCE = "performance"
KIND_STABILITY = "stability"
KIND_COMPLIANCE = "compliance"
KIND_SECURITY_BASIC = "security_basic"
KIND_SECURITY_ADV = "security_adv"


@dataclass
class PluginContext:
    """
    Context object passed to plugins. Extendable.
    """
    request_id: str
    config: dict[str, Any]   # normalized parsed config from parsers
    log_extra: dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = field(default_factory=lambda: settings.DEFAULT_TASK_TIMEOUT_SEC)


@dataclass
class PluginResult:
    ok: bool
    kind: str
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


class TestPlugin(abc.ABC):
    """
    Base class for all test plugins.
    """

    kind: ClassVar[str]

    @abc.abstractmethod
    async def run(self, ctx: PluginContext) -> PluginResult:  # pragma: no cover
        raise NotImplementedError


# -------------------------
# Plugin Registry
# -------------------------
_REGISTRY: Dict[str, Callable[[], TestPlugin]] = {}


def register_plugin(kind: str) -> Callable[[type[TestPlugin]], type[TestPlugin]]:
    """
    Decorator to register a plugin class factory under a given kind.
    """
    def _wrap(cls: type[TestPlugin]) -> type[TestPlugin]:
        if kind in _REGISTRY:
            raise RuntimeError(f"plugin kind already registered: {kind}")
        _REGISTRY[kind] = cls  # type: ignore[assignment]
        cls.kind = kind  # type: ignore[attr-defined]
        return cls
    return _wrap


def available_kinds() -> list[str]:
    return sorted(_REGISTRY.keys())


def make_plugin(kind: str) -> TestPlugin:
    factory = _REGISTRY.get(kind)
    if not factory:
        raise KeyError(f"no plugin registered for kind={kind}")
    return factory()  # type: ignore[call-arg]
