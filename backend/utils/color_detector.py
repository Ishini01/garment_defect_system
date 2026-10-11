"""
Color Imbalance Detection using a pre-trained Keras (.h5) model.

This detector replicates the EXACT preprocessing pipeline used during
training in Color_Imbalance_ResNet.ipynb:

    1. cv2.imread              (BGR, 0-255)
    2. cv2.cvtColor(BGR->RGB)  (RGB, 0-255)
    3. cv2.resize              (224x224, float32, still 0-255)
    4. resnet50.preprocess_input  (RGB->BGR internally + ImageNet mean subtraction)
    5. np.expand_dims(x, 0)    (add batch dim)

The model's sigmoid output is P(class = 1). In the notebook:
    label 0 = Balanced
    label 1 = Imbalanced
So a HIGH sigmoid value means IMBALANCED.
"""

import os
import cv2
import numpy as np

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

# ⭐ This import is CRITICAL — it's the same function used in the notebook
from tensorflow.keras.applications.resnet50 import preprocess_input


class ColorImbalanceDetector:
    """Wraps the pre-trained color imbalance .h5 model."""

    DEFAULT_MODEL_PATH = os.path.join('models', 'color_imbalance_model.h5')
    DEFAULT_IMG_SIZE = (224, 224)

    # The notebook uses binary labels: 0=Balanced, 1=Imbalanced with a
    # single sigmoid output. So sigmoid output = P(Imbalanced).
    CLASS_NAMES = ['Balanced', 'Imbalanced']

    # ============================================

    def __init__(self, model_path=None):
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.model = None
        self.img_size = self.DEFAULT_IMG_SIZE
        self.class_names = self.CLASS_NAMES
        self.output_shape = None
        self._load_model()

    # ============================================
    # MODEL LOADING
    # ============================================
    def _load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        print(f"[ColorImbalance] Loading model from {self.model_path} ...")

        loaded_model = None
        load_error = None

        try:
            import keras
            loaded_model = keras.models.load_model(
                self.model_path, compile=False, safe_mode=False
            )
            print("[ColorImbalance] ✓ Loaded via Keras 3")
        except Exception as e:
            load_error = e
            print(f"[ColorImbalance] Keras 3 load failed: {e}")

        if loaded_model is None:
            try:
                from tensorflow.keras.models import load_model as tf_load
                loaded_model = tf_load(self.model_path, compile=False)
                print("[ColorImbalance] ✓ Loaded via tf.keras")
            except Exception as e:
                load_error = e
                print(f"[ColorImbalance] tf.keras load failed: {e}")

        if loaded_model is None:
            raise RuntimeError(f"Could not load model: {load_error}")

        self.model = loaded_model

        # Detect input size from model
        try:
            shape = self.model.input_shape
            if isinstance(shape, list):
                shape = shape[0]
            if isinstance(shape, tuple) and len(shape) == 4:
                h, w = shape[1], shape[2]
                if h and w:
                    self.img_size = (w, h)
                    print(f"[ColorImbalance] Input size: {self.img_size}")
        except Exception as e:
            print(f"[ColorImbalance] Using default input size: {e}")

        # Log output shape for diagnostics
        try:
            out_shape = self.model.output_shape
            if isinstance(out_shape, list):
                out_shape = out_shape[0]
            print(f"[ColorImbalance] Output shape: {out_shape}")
            self.output_shape = out_shape
        except Exception:
            self.output_shape = None

    # ============================================
    # PREPROCESSING — MUST MATCH THE NOTEBOOK
    # ============================================
    def _preprocess(self, image_bgr):
        """
        Replicates notebook pipeline EXACTLY, in the same order:

            img_bgr  = cv2.imread(path)                       # BGR, 0-255, uint8
            img_rgb  = cv2.cvtColor(img_bgr, BGR2RGB)         # RGB, 0-255, uint8
            img_rsz  = cv2.resize(img_rgb, (224,224)).astype(float32)
            x        = preprocess_input(img_rsz)              # RGB->BGR + mean subtraction
            x        = np.expand_dims(x, 0)                   # batch dim
        """
        # 1. BGR -> RGB first (matches notebook order)
        img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        # 2. Resize to model input size with DEFAULT interpolation
        #    (the notebook did not pass interpolation= so it used INTER_LINEAR)
        img = cv2.resize(img, self.img_size)

        # 3. Convert to float32; keep 0-255 range
        #    (preprocess_input expects 0-255 float input)
        img = img.astype('float32')

        # 4. Apply the SAME ResNet50 preprocessing used during training.
        #    Internally: RGB -> BGR, then subtract ImageNet means
        #    [103.939, 116.779, 123.68] per channel.
        img = preprocess_input(img)

        # 5. Add batch dimension -> (1, 224, 224, 3)
        return np.expand_dims(img, axis=0)

    # ============================================
    # PUBLIC API
    # ============================================
    def analyze(self, image_path):
        try:
            if not os.path.exists(image_path):
                return self._safe_default(error=f"Image not found: {image_path}")

            image = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if image is None:
                return self._safe_default(error=f"Could not read: {image_path}")

            return self.predict(image)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._safe_default(error=str(e))

    def predict(self, image_bgr):
        if self.model is None:
            return self._safe_default(error="Model not loaded")

        try:
            x = self._preprocess(image_bgr)

            # Run prediction (support both .predict() and direct call)
            try:
                output = self.model.predict(x, verbose=0)
            except TypeError:
                output = self.model(x, training=False)
                output = np.array(output)

            preds = np.array(output).flatten()
            print(f"[ColorImbalance] raw preds = {preds.tolist()}")

            if preds.size == 0:
                return self._safe_default(error="Empty prediction")

            # ================================================
            # CASE 1: Single sigmoid output
            #   In the notebook: 1 = Imbalanced, 0 = Balanced
            #   So sigmoid value = P(Imbalanced)
            # ================================================
            if preds.size == 1:
                sigmoid = float(preds[0])
                p_imbalanced = sigmoid
                p_balanced = 1.0 - sigmoid

            # ================================================
            # CASE 2: Two-output softmax
            #   class_names = ['Balanced', 'Imbalanced']
            #   So index 0 = Balanced, index 1 = Imbalanced
            # ================================================
            else:
                p_balanced = float(preds[0])
                p_imbalanced = float(preds[1])

            # Clamp to valid range
            p_balanced = max(0.0, min(1.0, p_balanced))
            p_imbalanced = max(0.0, min(1.0, p_imbalanced))

            # Winner takes all
            is_imbalanced = p_imbalanced > p_balanced
            predicted_class = 'Imbalanced' if is_imbalanced else 'Balanced'
            confidence = p_imbalanced if is_imbalanced else p_balanced

            print(f"[ColorImbalance] → p_bal={p_balanced:.3f}  p_imb={p_imbalanced:.3f}  "
                  f"verdict={predicted_class}  conf={confidence * 100:.1f}%")

            return {
                'has_defect': is_imbalanced,
                'is_imbalanced': is_imbalanced,
                'predicted_class': predicted_class,
                'confidence': round(float(confidence), 4),
                'balanced_probability': round(p_balanced * 100, 2),
                'imbalanced_probability': round(p_imbalanced * 100, 2),
                'defect_type': 'Color Imbalance' if is_imbalanced else None,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._safe_default(error=str(e))

    def predict_from_path(self, image_path):
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            return self._safe_default(error=f"Could not read {image_path}")
        return self.predict(image)

    # ============================================
    # HELPERS
    # ============================================
    @staticmethod
    def _safe_default(error=None):
        d = {
            'has_defect': False,
            'is_imbalanced': False,
            'predicted_class': 'Error' if error else 'Balanced',
            'confidence': 0.0,
            'balanced_probability': 0.0,
            'imbalanced_probability': 0.0,
            'defect_type': None,
        }
        if error:
            d['error'] = error
        return d


# ============================================
# QUICK SELF-TEST — run this file directly
# ============================================
if __name__ == '__main__':
    import sys

    model_path = sys.argv[1] if len(sys.argv) > 1 else ColorImbalanceDetector.DEFAULT_MODEL_PATH
    detector = ColorImbalanceDetector(model_path)

    if len(sys.argv) > 2:
        # Test on the provided image(s)
        for path in sys.argv[2:]:
            result = detector.predict_from_path(path)
            print(f"\n{path}")
            print(f"  → {result.get('predicted_class')}  "
                  f"(bal={result.get('balanced_probability')}%, "
                  f"imb={result.get('imbalanced_probability')}%)")
            if 'error' in result:
                print(f"  error: {result['error']}")
    else:
        print("\nUsage: python color_detector.py [model_path] [image1] [image2] ...")