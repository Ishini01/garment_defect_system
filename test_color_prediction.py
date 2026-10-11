
from pathlib import Path
from backend.utils.color_detector import predict_color_imbalance

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "test_garment.png"

with open(IMAGE_PATH, "rb") as file:
    image_bytes = file.read()

result = predict_color_imbalance(image_bytes)

print("Prediction result:", result)
