import json
import time
import threading
import cv2
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from detector import detect_people

CONFIG_PATH = "cameras_config.json"
PROCESS_EVERY_N_FRAMES = 7

def _load_sources(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        sources = json.load(f)
    for src in sources:
        src["roi"] = tuple(src["roi"])
    return sources

SOURCES = _load_sources(CONFIG_PATH)

_state: dict[str, dict] = {
    src["area_id"]: {"count": 0, "latest_frame": None}
    for src in SOURCES
}
_state_lock = threading.Lock()


def _run_source(src: dict):
    area_id   = src["area_id"]
    roi       = src["roi"]
    video     = src["video"]
    frame_idx = 0

    cap = cv2.VideoCapture(video)

    while True:
        ret, frame = cap.read()
        if not ret:
            if isinstance(video, int):
                print(f"[{area_id}] Camera read failed, retrying...")
                cap.release()
                cap = cv2.VideoCapture(video)
                continue
            else:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

        skip = (frame_idx % PROCESS_EVERY_N_FRAMES != 0)
        count, annotated = detect_people(frame, roi, area_id, skip=skip)
        frame_idx += 1

        if skip:
            continue

        ret2, buf = cv2.imencode(".jpg", annotated)
        jpeg = buf.tobytes() if ret2 else None

        with _state_lock:
            _state[area_id]["count"]        = count
            _state[area_id]["latest_frame"] = jpeg


def _frame_generator(area_id: str):
    while True:
        with _state_lock:
            jpeg = _state[area_id]["latest_frame"]
        if jpeg:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
        time.sleep(0.03)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/video_feed/{area_id}")
def video_feed(area_id: str):
    if area_id not in _state:
        return {"error": "area_id not found"}
    return StreamingResponse(
        _frame_generator(area_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/current_count")
def get_current_count():
    with _state_lock:
        return [
            {"area_id": aid, "count": data["count"]}
            for aid, data in _state.items()
        ]


if __name__ == "__main__":
    for src in SOURCES:
        t = threading.Thread(target=_run_source, args=(src,), daemon=True)
        t.start()
        print(f"[pythoncv] Started source: {src['area_id']} ← {src['video']}")

    uvicorn.run(app, host="0.0.0.0", port=8001)
