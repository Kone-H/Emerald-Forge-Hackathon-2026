import cv2
from ultralytics import YOLO

MODEL_PATH           = "yolov8na.pt"
CONFIDENCE_THRESHOLD = 0.6
LOW_CONF_THRESHOLD   = 0.3
PERSON_CLASS_ID      = 0

# Bounding-box size/shape filters to reject obvious false positives
MIN_HEIGHT = 80
MIN_ASPECT = 0.3
MAX_ASPECT = 1.0

# Per-area background subtractors. Used to tell moving objects from static ones
# (so that furniture misclassified as "person" gets filtered out).
_bg_subtractors: dict[str, cv2.BackgroundSubtractor] = {}

# Per-area set of tracking IDs that have been observed moving at least once.
# Once a track ID lands in here, that person keeps being counted even after
# they sit down and stop moving. Furniture never moves, so its (misdetected)
# track IDs never enter this set and therefore never get counted.
_moved_ids: dict[str, set[int]] = {}

_model = YOLO(MODEL_PATH)


def detect_people(
    frame,
    roi: tuple[int, int, int, int],
    area_id: str = "default",
    skip: bool = False
) -> tuple[int, any]:

    # --- Background subtractor (per area) -----------------------------------
    # Keeps a separate motion model for each camera/area so they don't
    # interfere with each other.
    if area_id not in _bg_subtractors:
        _bg_subtractors[area_id] = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=50, detectShadows=False
        )
    bg_sub = _bg_subtractors[area_id]
    fg_mask = bg_sub.apply(frame)

    # --- "Has moved before" memory (per area) -------------------------------
    if area_id not in _moved_ids:
        _moved_ids[area_id] = set()
    moved = _moved_ids[area_id]

    # On skipped frames we still updated the background model above (good),
    # but we don't run detection to save compute.
    if skip:
        return 0, frame

    # Run YOLO with built-in tracker so each detection carries a stable
    # track_id across frames. persist=True keeps IDs consistent between calls.
    results = _model.track(frame, persist=True, verbose=False, device="mps")
    count = 0

    for box in results[0].boxes:
        cls  = int(box.cls[0])
        conf = float(box.conf[0])

        # Filter 1: must be the "person" class
        if cls != PERSON_CLASS_ID:
            continue

        # Filter 2: confidence must be high enough.
        # Medium-confidence boxes are drawn in yellow for debugging but not counted.
        if conf <= CONFIDENCE_THRESHOLD:
            if conf >= LOW_CONF_THRESHOLD:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)
                cv2.putText(frame, f"low {conf:.2f}",
                            (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        w = x2 - x1
        h = y2 - y1
        aspect = w / h if h > 0 else 0

        # Filter 3: reject boxes that are too small or have a weird aspect ratio
        # (real standing/sitting humans fall within these bounds).
        if h < MIN_HEIGHT or not (MIN_ASPECT < aspect < MAX_ASPECT):
            continue

        # Filter 4: motion check with memory.
        # - If the box currently has motion, remember its track_id.
        # - If it has no motion AND has never been seen moving, treat it as
        #   a static object (e.g. a chair misidentified as a person) and skip.
        # - If it has no motion but was seen moving before (e.g. a person who
        #   walked in and then sat down), keep counting it.
        track_id = int(box.id[0]) if box.id is not None else None

        box_mask     = fg_mask[y1:y2, x1:x2]
        motion_ratio = cv2.countNonZero(box_mask) / (w * h) if w * h > 0 else 0

        if motion_ratio >= 0.05 and track_id is not None:
            moved.add(track_id)

        if motion_ratio < 0.05 and (track_id is None or track_id not in moved):
            # Never-moved object -> assume it's furniture, draw gray and skip.
            cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
            continue

        # Filter 5: count only if the box center is inside the ROI
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        in_roi = roi[0] < cx < roi[2] and roi[1] < cy < roi[3]
        color  = (0, 255, 0) if in_roi else (0, 0, 255)

        if in_roi:
            count += 1

        # Draw the detection: green if counted, red if outside the ROI
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, (cx, cy), 5, color, -1)

    # Draw the ROI rectangle and the current count for visual debugging
    cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    cv2.putText(frame, f"People in ROI: {count}",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return count, frame