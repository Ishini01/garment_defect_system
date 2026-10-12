
from pathlib import Path
from ultralytics import YOLO


class LabelDetector:

    def __init__(self):
        project_root = Path(__file__).resolve().parents[2]
        model_path = project_root / "models" / "label_best.pt"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Missing label model: {model_path}"
            )

        self.model = YOLO(str(model_path))
        print("Label detection model loaded successfully!")

    def detect_labels(self, image):
        if image is None or image.size == 0:
            raise ValueError("Invalid image provided")

        # Detect labels from the complete shirt image
        results = self.model.predict(
            source=image,
            imgsz=960,
            conf=0.20,
            iou=0.45,
            save=False,
            verbose=False
        )

        detections = []

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            class_name = str(self.model.names[class_id])
            confidence = float(box.conf[0])

            normalized_name = class_name.strip().lower()

            # Only consider ProductLabel and NoLabel
            if normalized_name not in ("productlabel", "nolabel"):
                continue

            detections.append({
                "class": class_name,
                "confidence": round(confidence, 4)
            })

        product_conf = max(
            (
                d["confidence"] for d in detections
                if d["class"].strip().lower() == "productlabel"
            ),
            default=None
        )

        no_label_conf = max(
            (
                d["confidence"] for d in detections
                if d["class"].strip().lower() == "nolabel"
            ),
            default=None
        )

        # Minimum confidence threshold
        threshold = 0.45

        product_detected = (
            product_conf is not None
            and product_conf >= threshold
        )

        no_label_detected = (
            no_label_conf is not None
            and no_label_conf >= threshold
        )

        # Only PASS and FAIL
        if product_detected and no_label_detected:
            status = "FAIL"
            message = "Conflicting label predictions"

        elif product_detected:
            status = "PASS"
            message = "Product label detected"

        elif no_label_detected:
            status = "FAIL"
            message = "No product label detected"

        else:
            status = "FAIL"
            message = "Product label not detected"

        return {
            "evaluated": True,
            "status": status,
            "message": message,

            "product_label": {
                "status": (
                    "DETECTED"
                    if product_detected
                    else "NOT_CONFIRMED"
                ),
                "confidence": product_conf
            },

            # Size label is not checked
            "size_label": {
                "status": "NOT_TESTED",
                "confidence": None
            },

            "no_label_detected": no_label_detected,
            "detections": detections
        }
