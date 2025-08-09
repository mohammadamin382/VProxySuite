# services/worker/src/testsuite/common.py
from __future__ import annotations

import asyncio
import os
import platform
import resource
import shlex
import signal
from dataclasses import dataclass
from typing import Iterable, Sequence

from config.settings import get_settings

settings = get_settings()


@dataclass(frozen=True)
class CmdResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    timeout: bool = False


def _set_resource_limits() -> None:
    """
    Apply conservative resource caps for child processes (Linux only).
    No network privileges are escalated here; just CPU/Memory caps.
    """
    if platform.system() != "Linux":
        return
    try:
        # CPU time 20s hard (kernel enforced)
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        # Max resident memory ≈ 256MB
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        # File size, open files, processes (defensive)
        resource.setrlimit(resource.RLIMIT_FSIZE, (20 * 1024 * 1024, 20 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except Exception:
        # If container disallows, ignore silently.
        pass


async def run_cmd(
    argv: Sequence[str] | str,
    *,
    timeout_sec: int | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    max_output_bytes: int | None = None,
) -> CmdResult:
    """
    Safely run a child process with strict time/memory/output caps.
    - Never uses shell=True.
    - Enforces resource limits on Linux.
    """
    if isinstance(argv, str):
        argv = shlex.split(argv)

    if timeout_sec is None:
        timeout_sec = settings.DEFAULT_SUBPROCESS_TIMEOUT_SEC
    if max_output_bytes is None:
        max_output_bytes = settings.DEFAULT_SUBPROCESS_MAX_OUTPUT_BYTES

    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        preexec_fn=_set_resource_limits if platform.system() == "Linux" else None,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        # Truncate outputs if needed (defense-in-depth)
        if len(stdout) > max_output_bytes:
            stdout = stdout[:max_output_bytes]
        if len(stderr) > max_output_bytes:
            stderr = stderr[:max_output_bytes]
        return CmdResult(exit_code=proc.returncode or 0, stdout=stdout, stderr=stderr, timeout=False)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.send_signal(signal.SIGKILL)
        return CmdResult(exit_code=137, stdout=b"", stderr=b"timeout", timeout=True)
