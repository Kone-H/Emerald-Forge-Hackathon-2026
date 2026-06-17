import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, query_history, AREA_IDS, AREA_META
from cache import get_current
from ingest import poll_and_store


def get_level(count: int, capacity: int) -> str:
    """Convert a raw count into a crowd level label.
    low:    0-33% of capacity
    medium: 34-66% of capacity
    high:   67%+ of capacity
    """
    ratio = count / capacity
    if ratio <= 0.33:
        return "low"
    elif ratio <= 0.66:
        return "medium"
    return "high"


class ConnectionManager:
    """Keeps track of all currently connected WebSocket clients.
    When new occupancy data arrives, broadcast it to all of them at once.
    """
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


async def on_cv_update(areas: list[dict]):
    """Called by ingest.py after each successful poll from Kone's CV server.
    Packages the data into the agreed WebSocket format and broadcasts to all clients.
    """
    now = int(time.time())
    payload = {
        "areas": [
            {
                "area_id": item["area_id"],
                "count": item["count"],
                "level": get_level(item["count"], AREA_META[item["area_id"]]["capacity"]),
            }
            for item in areas
            if item["area_id"] in AREA_META
        ],
        "timestamp": now,
    }
    await manager.broadcast(payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts up."""
    init_db()          # Create SQLite tables if they don't exist
    print("Database ready.")
    asyncio.create_task(poll_and_store(on_update=on_cv_update))  # Start CV polling
    print("CV polling started.")
    yield


app = FastAPI(title="Campus Occupancy API", lifespan=lifespan)

# Allow the React frontend (any origin during development) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Simple health check - returns ok if the server is running."""
    return {"status": "ok"}


@app.get("/api/areas")
def get_areas():
    """Returns current occupancy data for all 4 areas.
    Reads from Redis (fast, in-memory). If no data yet, count defaults to 0.
    """
    results = []
    for area_id in AREA_IDS:
        meta = AREA_META[area_id]
        cached = get_current(area_id)
        count = cached["count"] if cached else 0
        timestamp = cached["timestamp"] if cached else int(time.time())
        results.append({
            "area_id": area_id,
            "name": meta["name"],
            "count": count,
            "capacity": meta["capacity"],
            "level": get_level(count, meta["capacity"]),
            "timestamp": timestamp,
        })
    return results


@app.get("/api/areas/{area_id}/history")
def get_history(area_id: str, hours: int = 24):
    """Returns historical occupancy records for one area (one snapshot per minute).
    Default: past 24 hours. Use ?hours=N to change the range.
    """
    if area_id not in AREA_IDS:
        raise HTTPException(status_code=404, detail="Area not found")
    since = int(time.time()) - hours * 3600
    return query_history(area_id, since)


@app.get("/api/recommend")
def recommend():
    """Returns all areas sorted by occupancy ratio (least crowded first).
    Sorts by count/capacity so areas with different capacities are compared fairly.
    Frontend uses this to power the 'Find me a seat' feature.
    """
    results = []
    for area_id in AREA_IDS:
        meta = AREA_META[area_id]
        cached = get_current(area_id)
        count = cached["count"] if cached else 0
        results.append({
            "area_id": area_id,
            "name": meta["name"],
            "count": count,
            "capacity": meta["capacity"],
            "level": get_level(count, meta["capacity"]),
        })
    return sorted(results, key=lambda x: x["count"] / x["capacity"])


@app.get("/api/viewers")
def get_viewers():
    """Returns the number of currently connected WebSocket clients."""
    return {"count": len(manager.active)}


@app.websocket("/ws/density")
async def websocket_density(ws: WebSocket):
    """WebSocket endpoint for real-time occupancy updates.
    Frontend connects here once; backend pushes new data every second automatically.
    """
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)
