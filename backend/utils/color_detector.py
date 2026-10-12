
from pathlib import Path
from io import BytesIO

import numpy as np
import tensorflow as tf
from PIL import Image

# Locate project root
BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = BASE_DIR / "models" / "color_imbalance_model.h5"

IMG_SIZE = (224, 224)
THRESHOLD = 0.5

# Load the model once
color_model = tf.keras.models.load_model(
    str(MODEL_PATH),
    compile=False
)


def predict_color_imbalance(image_bytes):
    # Read uploaded image
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Resize to the model's input size
    image = image.resize(IMG_SIZE)

    # Convert to float32
    image_array = np.asarray(image, dtype=np.float32)

    # Apply ResNet50 preprocessing
    image_array = tf.keras.applications.resnet50.preprocess_input(
        image_array
    )

    # Add batch dimension
    image_array = np.expand_dims(image_array, axis=0)

    # Run inference
    prediction = color_model.predict(
        image_array,
        verbose=0
    )

    score = float(prediction[0][0])

    # Assumes class 0 = Balanced, class 1 = Imbalanced
    is_imbalanced = score > THRESHOLD

    label = "Imbalanced" if is_imbalanced else "Balanced"
    status = "FAIL" if is_imbalanced else "PASS"
    confidence = score if is_imbalanced else 1.0 - score

    return {
        "model": "color_imbalance",
        "raw_score": score,
        "label": label,
        "status": status,
        "color_balanced": not is_imbalanced,
        "confidence": confidence
    }
