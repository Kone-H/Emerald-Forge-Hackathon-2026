import asyncio
import os
import time

import httpx

from cache import set_current
from db import insert_record

# CV server address — overridden via CV_SERVER_URL env var in Docker/production.
# Defaults to localhost for plain local development.
CV_SERVER_URL = os.getenv("CV_SERVER_URL", "http://localhost:8001/api/current_count")

# Poll Kone's server once per second
POLL_INTERVAL = 1

# Persist a snapshot to SQLite once per minute per area
PERSIST_INTERVAL = 60

# Tracks the last time each area was written to SQLite
_last_persist: dict[str, int] = {}


async def poll_and_store(on_update=None):
    """Background task: polls Kone's CV server every second.

    For each poll:
    - Writes the latest count for each area into Redis (overwrites previous value)
    - Once per minute, also writes a snapshot into SQLite for historical records
    - If on_update callback is provided, calls it so WebSocket clients get notified
    - If Kone's server is offline, logs the error and retries next second
    """
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(CV_SERVER_URL, timeout=2)
                # Expects: [{"area_id": "area_225_2f_1", "count": 3}, ...]
                areas = response.json()

                now = int(time.time())
                for item in areas:
                    area_id = item["area_id"]
                    count = item["count"]

                    # Always update Redis with the latest value
                    set_current(area_id, count, now)

                    # Write to SQLite once per minute (for historical trend chart)
                    last = _last_persist.get(area_id, 0)
                    if now - last >= PERSIST_INTERVAL:
                        insert_record(area_id, count, now)
                        _last_persist[area_id] = now

                # Trigger WebSocket broadcast so frontend updates in real time
                if on_update:
                    await on_update(areas)

            except Exception as e:
                print(f"[ingest] Failed to poll CV server: {e}")

            await asyncio.sleep(POLL_INTERVAL)
