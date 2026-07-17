"""Shared helpers for EVT-first teaching labs."""

from __future__ import annotations

import asyncio
import sys
from typing import Callable

from .session_lite import SessionLite


def duration_arg(default: float = 12.0) -> float:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        return float(sys.argv[1])
    return default


def flag(name: str) -> bool:
    return name in sys.argv


async def connect_and_live(
    session: SessionLite,
    *,
    settle_s: float = 0.8,
) -> None:
    """Canonical bring-up: connect + BS_TX notify (CCCD opens TX_EVT)."""
    await session.connect()
    await session.go_live(settle_s=settle_s)


async def stream_for(
    session: SessionLite,
    duration_s: float,
    *,
    on_tick: Callable[[], None] | None = None,
    tick_s: float = 0.5,
) -> None:
    """Sleep for duration; optional periodic UI tick (dashboard)."""
    if on_tick is None:
        await asyncio.sleep(duration_s)
        return
    end = asyncio.get_running_loop().time() + duration_s
    while asyncio.get_running_loop().time() < end:
        on_tick()
        await asyncio.sleep(tick_s)
