"""Broken-stitch detection using YOLO garment ROIs and a three-model ensemble.

No inspection images or ROI crops are written to disk.
"""
from pathlib import Path
import cv2
import numpy as np
import tensorflow as tf
import keras_hub  # noqa: F401 - registers KerasHub ViT model classes
from ultralytics import YOLO
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input as mobilenet_preprocess


class StitchDetector:
    def __init__(self, models_dir=None, roi_conf=0.25):
        root = Path(models_dir) if models_dir is not None else Path(__file__).resolve().parents[2] / 'models'
        self.roi_model = YOLO(str(root / 'stitch_roi_best.pt'))
        self.mobile_model = tf.keras.models.load_model(str(root / 'mobileNet_Model.keras'), compile=False)
        self.efficient_model = tf.keras.models.load_model(str(root / 'EfficientNet.keras'), compile=False)
        self.vit_model = tf.keras.models.load_model(str(root / 'ViT_Model.keras'), compile=False)
        self.roi_conf = roi_conf

    def _classify(self, crop_bgr):
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (224, 224))
        batch = np.expand_dims(resized, axis=0).astype(np.float32)

        mobile = float(self.mobile_model.predict(mobilenet_preprocess(batch.copy()), verbose=0)[0][0])
        efficient = float(self.efficient_model.predict(batch.copy(), verbose=0)[0][0])
        vit_logits = self.vit_model.predict(batch.copy(), verbose=0)
        vit = float(tf.nn.softmax(vit_logits, axis=1).numpy()[0][1])
        prob = 0.40 * mobile + 0.25 * efficient + 0.35 * vit
        return {
            'status': 'Broken Stitches' if prob >= 0.5 else 'Normal Stitches',
            'ensemble_prob': round(float(prob), 6),
            'mobile_prob': round(mobile, 6),
            'efficient_prob': round(efficient, 6),
            'vit_prob': round(vit, 6),
        }

    def detect(self, image_bgr):
        """Accept OpenCV BGR ndarray; return JSON-serializable metadata only."""
        if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
            raise ValueError('A nonempty OpenCV BGR image is required')
        height, width = image_bgr.shape[:2]
        prediction = self.roi_model.predict(source=image_bgr, conf=self.roi_conf, verbose=False)[0]
        rois = []
        for box in prediction.boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            x1, x2 = max(0, x1), min(width, x2)
            y1, y2 = max(0, y1), min(height, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            crop = image_bgr[y1:y2, x1:x2]
            cls_id = int(box.cls[0].item())
            result = self._classify(crop)
            rois.append({
                'roi_name': self.roi_model.names[cls_id],
                'bbox': [x1, y1, x2, y2],
                'roi_confidence': round(float(box.conf[0].item()), 6),
                **result,
            })
        if not rois:
            return {
                'evaluated': False,
                'status': 'NOT_TESTED',
                'broken_stitches': None,
                'message': 'No valid stitch ROIs detected; cannot assess stitches',
                'rois': [],
            }
        broken = any(roi['status'] == 'Broken Stitches' for roi in rois)
        return {
            'evaluated': True,
            'status': 'FAIL' if broken else 'PASS',
            'broken_stitches': broken,
            'rois': rois,
        }
