"""
Color Imbalance Detection using a pre-trained Keras (.h5) model.

Uses Keras 3 (TensorFlow 2.16+) with a tf.keras fallback.
Exposes `ColorImbalanceDetector.analyze(image_path)` returning a dict
consumed by app.py.
"""

import os
import cv2
import numpy as np

# Silence TF logs before importing TF/Keras
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

# Try Keras 3 first, fall back to tf.keras
try:
    import keras
    KERAS_3 = True
except ImportError:
    KERAS_3 = False
    from tensorflow.keras.models import load_model as keras_load_model


class ColorImbalanceDetector:
    """
    Wrapper class for the pre-trained color imbalance model.
    Handles image preprocessing, prediction, and result formatting.
    """

    # ---------- CONFIG ----------
    # Path relative to project root (where you run `python -m backend.app`)
    DEFAULT_MODEL_PATH = os.path.join('models', 'color_imbalance_model.h5')

    # Input size — matches your resnet model
    IMG_SIZE = (224, 224)

    # Class order: index 0 = Balanced, index 1 = Imbalanced
    # (If your model outputs the opposite, swap these)
    CLASS_NAMES = ['Balanced', 'Imbalanced']

    # Normalization:
    #   'div255'   -> divide by 255 (range [0, 1])
    #   'centered' -> (x/127.5) - 1 (range [-1, 1])  ← typical for ResNet50
    #   'none'     -> raw [0, 255]
    NORMALIZATION = 'centered'

    # -----------------------------

    def __init__(self, model_path=None):
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.model = None
        self.img_size = self.IMG_SIZE
        self.class_names = self.CLASS_NAMES
        self._load_model()

    # ---------- MODEL LOADING ----------
    def _load_model(self):
        """Load the Keras model once at startup."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        print(f"[ColorImbalance] Loading model from {self.model_path}...")

        loaded = False
        errors = []

        # ---- Try Keras 3 first ----
        if KERAS_3:
            try:
                self.model = keras.models.load_model(
                    self.model_path,
                    compile=False,
                    safe_mode=False  # allow custom layers / lambda
                )
                print(f"[ColorImbalance] ✓ Loaded via Keras 3. Input shape: {self.model.input_shape}")
                loaded = True
            except Exception as e:
                errors.append(f"Keras 3: {e}")
                print(f"[ColorImbalance] Keras 3 load failed: {e}")

        # ---- Fallback to tf.keras ----
        if not loaded:
            try:
                from tensorflow.keras.models import load_model as tf_load
                self.model = tf_load(self.model_path, compile=False)
                print(f"[ColorImbalance] ✓ Loaded via tf.keras. Input shape: {self.model.input_shape}")
                loaded = True
            except Exception as e:
                errors.append(f"tf.keras: {e}")
                print(f"[ColorImbalance] tf.keras load failed: {e}")

        if not loaded:
            raise RuntimeError(
                "Could not load model with Keras 3 or tf.keras. Errors:\n  - "
                + "\n  - ".join(errors)
            )

    # ---------- PREPROCESSING ----------
    def _preprocess(self, image):
        """
        Preprocess a BGR image for model inference.
        Resize -> BGR→RGB -> normalize -> add batch dim.
        """
        img = cv2.resize(image, self.img_size, interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype('float32')

        if self.NORMALIZATION == 'div255':
            img = img / 255.0
        elif self.NORMALIZATION == 'centered':
            img = (img / 127.5) - 1.0
        # else 'none' -> leave as raw

        return np.expand_dims(img, axis=0)

    # ---------- PUBLIC API ----------
    def analyze(self, image_path):
        """
        Run color imbalance detection on an image file path.
        Called by app.py:  color_detector.analyze(image_path)

        Returns:
            dict with keys: has_defect, confidence, predicted_class,
                            balanced_probability, imbalanced_probability
            OR {'error': '...'} on failure.
        """
        try:
            if not os.path.exists(image_path):
                return {'error': f'Image not found: {image_path}'}

            image = cv2.imread(image_path)
            if image is None:
                return {'error': f'Could not read image: {image_path}'}

            return self.predict(image)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': f'Color detection failed: {str(e)}'}

    def predict(self, image):
        """
        Run inference on a BGR numpy image.

        Returns:
            dict with keys:
                has_defect              (bool)
                is_imbalanced           (bool, alias)
                confidence              (float, 0.0 – 1.0)
                predicted_class         (str)
                balanced_probability    (float, 0 – 100)
                imbalanced_probability  (float, 0 – 100)
                defect_type             (str or None)
        """
        if self.model is None:
            return {'error': 'Model not loaded'}

        try:
            preprocessed = self._preprocess(image)

            # Run inference — supports both Keras 3 and tf.keras
            try:
                output = self.model.predict(preprocessed, verbose=0)
            except TypeError:
                # Keras 3 sometimes doesn't like `verbose`
                output = self.model(preprocessed, training=False)
                output = np.array(output)

            predictions = output[0]

            # ---- Handle binary (sigmoid) vs multi-class (softmax) ----
            if predictions.ndim == 0 or len(predictions) == 1:
                # Binary sigmoid — value is probability of class 1
                p_imbalanced = float(predictions[0]) if predictions.ndim == 0 else float(predictions)
                p_balanced = 1.0 - p_imbalanced
                if p_imbalanced >= 0.5:
                    predicted_class = 1
                    confidence = p_imbalanced
                else:
                    predicted_class = 0
                    confidence = p_balanced
            else:
                # Multi-class softmax
                predicted_class = int(np.argmax(predictions))
                confidence = float(predictions[predicted_class])
                p_balanced = float(predictions[0]) if len(predictions) > 0 else 0.0
                p_imbalanced = float(predictions[1]) if len(predictions) > 1 else 0.0

            is_imbalanced = (predicted_class == 1)

            return {
                'has_defect': is_imbalanced,          # app.py reads this
                'is_imbalanced': is_imbalanced,
                'predicted_class': self.class_names[predicted_class],
                'confidence': round(confidence, 4),   # 0.0 – 1.0 (matches app.py)
                'balanced_probability': round(p_balanced * 100, 2),   # 0 – 100
                'imbalanced_probability': round(p_imbalanced * 100, 2),  # 0 – 100
                'defect_type': 'Color Imbalance' if is_imbalanced else None
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'error': f'Prediction failed: {str(e)}'}

    def predict_from_path(self, image_path):
        """Convenience: predict directly from an image file path."""
        image = cv2.imread(image_path)
        if image is None:
            return {'error': f'Could not read image at {image_path}'}
        return self.predict(image)