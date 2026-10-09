"""Desktop-mode helpers: detect when the app window is closed, then stop the engine.

The UI keeps one tiny server-sent-events connection open (/api/desktop/session) and the
server records a heartbeat every 2 s. A window counts as open only while heartbeats keep
arriving, so shutdown never depends on the HTTP layer reporting the disconnect.
Only active when the launcher sets PDFTOOL_AUTOEXIT=1.
"""
import asyncio
import os
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()
_beats: dict[str, float] = {}   # connection id -> last heartbeat (monotonic)
_seen = False
BEAT_EVERY = 2.0
BEAT_TIMEOUT = 7.0


def _log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} [desktop] {msg}", flush=True)  # goes to data/server.log


def _live(now: float) -> int:
    return sum(1 for t in _beats.values() if now - t < BEAT_TIMEOUT)


@router.get("/api/desktop/session")
async def session():
    global _seen

    async def gen():
        cid = uuid.uuid4().hex[:6]
        _beats[cid] = time.monotonic()
        _log(f"window connected ({cid})")
        try:
            yield "retry: 1000\n\n"
            while True:
                _beats[cid] = time.monotonic()
                yield ": keepalive\n\n"
                await asyncio.sleep(BEAT_EVERY)
        finally:
            _beats.pop(cid, None)
            _log(f"window disconnected ({cid})")

    _seen = True
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@router.post("/api/desktop/quit")
async def quit_now(request: Request):
    # Custom header => browsers must pre-flight => other websites cannot call this.
    if os.environ.get("PDFTOOL_AUTOEXIT") != "1" or request.headers.get("x-pdf-tool") != "1":
        raise HTTPException(403, "not allowed")
    _log("quit requested")
    asyncio.get_running_loop().call_later(0.3, os._exit, 0)
    return {"ok": True}


async def watchdog() -> None:
    first_grace = float(os.environ.get("PDFTOOL_FIRST_GRACE", "120"))  # window never opened
    idle_grace = float(os.environ.get("PDFTOOL_IDLE_GRACE", "15"))     # covers page reloads
    started = last_tick = time.monotonic()
    idle_since = None
    _log("watchdog started")
    while True:
        await asyncio.sleep(1)
        now = time.monotonic()
        if now - last_tick > 5:  # PC was asleep: give the window time to reconnect
            started, idle_since = now, None
            for k in list(_beats):
                _beats[k] = now
        last_tick = now
        if _live(now) > 0:
            idle_since = None
            continue
        if idle_since is None:
            idle_since = now
        limit = idle_grace if _seen else first_grace
        if now - (idle_since if _seen else started) > limit:
            _log("no open window -> shutting down")
            os._exit(0)
