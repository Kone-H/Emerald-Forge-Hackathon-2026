import sqlite3

# Path to the SQLite database file (created automatically on first run)
DB_PATH = "occupancy.db"

# All area IDs - must match the IDs used in the frontend map
AREA_IDS = [
    "area_225_2f_1",
    "area_225_2f_2",
    "area_225_2f_3",
    "area_225_2f_4",
]

# Display name and max capacity for each area
# Update names here if the frontend changes them
AREA_META = {
    "area_225_2f_1": {"name": "North Corridor",      "capacity": 8},
    "area_225_2f_2": {"name": "Northeast Open Area", "capacity": 20},
    "area_225_2f_3": {"name": "Northwest Open Area", "capacity": 20},
    "area_225_2f_4": {"name": "East Corridor",       "capacity": 8},
}


def init_db():
    """Create the occupancy_history table and index if they don't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # One row per area per minute: stores how many people were detected at that time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS occupancy_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id     TEXT    NOT NULL,
            count       INTEGER NOT NULL,
            recorded_at INTEGER NOT NULL
        )
    """)

    # Index speeds up queries like "give me all records for area X in the last 24 hours"
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_area_recorded
        ON occupancy_history (area_id, recorded_at)
    """)

    conn.commit()
    conn.close()


def insert_record(area_id: str, count: int, recorded_at: int):
    """Save one occupancy snapshot to SQLite (called once per minute per area)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO occupancy_history (area_id, count, recorded_at) VALUES (?, ?, ?)",
        (area_id, count, recorded_at),
    )
    conn.commit()
    conn.close()


def query_history(area_id: str, since: int) -> list[dict]:
    """Return all records for area_id where recorded_at >= since (Unix timestamp)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT area_id, count, recorded_at FROM occupancy_history "
        "WHERE area_id = ? AND recorded_at >= ? ORDER BY recorded_at ASC",
        (area_id, since),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"area_id": r[0], "count": r[1], "recorded_at": r[2]} for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
