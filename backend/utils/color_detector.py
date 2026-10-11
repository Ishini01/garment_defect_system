
from pathlib import Path
from io import BytesIO

import numpy as np
import tensorflow as tf
from PIL import Image

# Locate project root
BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = BASE_DIR / "models" / "color_imbalance_model.h5"

# Load the model only once
color_model = tf.keras.models.load_model(
    str(MODEL_PATH),
    compile=False
)

IMG_SIZE = (224, 224)


def predict_color_imbalance(image_bytes):
    # Open uploaded image and convert to RGB
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Resize to model input dimensions
    image = image.resize(IMG_SIZE)

    # Convert image to NumPy array
    image_array = np.asarray(image, dtype=np.float32)

    # ResNet50 preprocessing
    image_array = tf.keras.applications.resnet50.preprocess_input(
        image_array
    )

    # Add batch dimension
    image_array = np.expand_dims(image_array, axis=0)

    # Make prediction
    prediction = color_model.predict(
        image_array,
        verbose=0
    )

    score = float(prediction[0][0])

    return {
        "model": "color_imbalance",
        "raw_score": score
    }
