import cv2
from ultralytics import YOLO

MODEL_PATH           = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.6
LOW_CONF_THRESHOLD   = 0.3
PERSON_CLASS_ID      = 0

MIN_HEIGHT = 80
MIN_ASPECT = 0.3
MAX_ASPECT = 1.0

_bg_subtractors: dict[str, cv2.BackgroundSubtractor] = {}

_model = YOLO(MODEL_PATH)


def detect_people(
    frame,
    roi: tuple[int, int, int, int],
    area_id: str = "default",
    skip: bool = False
) -> tuple[int, any]:

    if area_id not in _bg_subtractors:
        _bg_subtractors[area_id] = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=50, detectShadows=False
        )
    bg_sub = _bg_subtractors[area_id]
    fg_mask = bg_sub.apply(frame)

    if skip:
        return 0, frame

    results = _model(frame)
    count = 0

    for box in results[0].boxes:
        cls  = int(box.cls[0])
        conf = float(box.conf[0])

        if cls != PERSON_CLASS_ID:
            continue

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

        if h < MIN_HEIGHT or not (MIN_ASPECT < aspect < MAX_ASPECT):
            continue

        box_mask     = fg_mask[y1:y2, x1:x2]
        motion_ratio = cv2.countNonZero(box_mask) / (w * h) if w * h > 0 else 0
        if motion_ratio < 0.05:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
            continue

        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        in_roi = roi[0] < cx < roi[2] and roi[1] < cy < roi[3]
        color  = (0, 255, 0) if in_roi else (0, 0, 255)

        if in_roi:
            count += 1

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, (cx, cy), 5, color, -1)

    cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 2)
    cv2.putText(frame, f"People in ROI: {count}",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return count, frame