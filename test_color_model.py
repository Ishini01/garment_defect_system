
from pathlib import Path
import tensorflow as tf

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent

# Path to trained color imbalance model
MODEL_PATH = BASE_DIR / "models" / "color_imbalance_model.h5"

print("Checking model path:", MODEL_PATH)

if not MODEL_PATH.exists():
    print("ERROR: Model file not found!")

else:
    print("Model file found!")

    try:
        model = tf.keras.models.load_model(
            str(MODEL_PATH),
            compile=False
        )

        print("Model loaded successfully!")
        print("Input shape:", model.input_shape)
        print("Output shape:", model.output_shape)

        model.summary()

    except Exception as e:
        print("Error loading model:", e)
