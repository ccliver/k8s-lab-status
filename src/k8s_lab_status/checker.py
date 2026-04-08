import asyncio
import json
import time
from pathlib import Path

import httpx

from .config import Settings


async def _check_url(client: httpx.AsyncClient, url: str) -> dict:
    start = time.monotonic()
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "url": url,
            "up": resp.status_code < 500,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "url": url,
            "up": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


def _write_results(path_str: str, data: dict) -> None:
    """Write check results to disk (EFS ReadWriteMany demo)."""
    try:
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass  # volume may not be mounted in dev/test


async def run_checker(
    settings: Settings, results: dict, stop_event: asyncio.Event
) -> None:
    """Background loop: check URLs, update shared results dict, write to EFS path."""
    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            urls = settings.get_urls()
            if urls:
                checks = await asyncio.gather(
                    *[_check_url(client, url) for url in urls]
                )
                snapshot = {
                    "checked_at": time.time(),
                    "endpoints": {c["url"]: c for c in checks},
                }
                results.clear()
                results.update(snapshot)
                _write_results(settings.results_path, snapshot)

            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=float(settings.check_interval)
                )
            except TimeoutError:
                pass
