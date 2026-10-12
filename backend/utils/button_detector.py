import cv2
import numpy as np
import requests
import os
import time
import gc
from datetime import datetime
import base64
import io
from PIL import Image

# ============================================
# TRAINED MODEL LOADING (singleton, loaded once per process)
# ============================================

DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'models',
    'best.pt'
)

_yolo_model = None
_yolo_load_error = None


def _get_model():
    """Lazily load the trained YOLOv11 button-defect model (exported from the
    Colab training notebook as best.pt) and cache it for the life of the process."""
    global _yolo_model, _yolo_load_error

    if _yolo_model is not None:
        return _yolo_model
    if _yolo_load_error is not None:
        raise _yolo_load_error

    try:
        from ultralytics import YOLO
    except ImportError:
        _yolo_load_error = RuntimeError(
            "ultralytics is not installed. Run: pip install ultralytics"
        )
        raise _yolo_load_error

    model_path = os.environ.get('BUTTON_MODEL_PATH', DEFAULT_MODEL_PATH)

    if not os.path.exists(model_path):
        _yolo_load_error = FileNotFoundError(
            f"Trained button-defect model not found at: {model_path}\n"
            "Export best.pt from the Colab training notebook (Notebook 1) and place it "
            "at this path, or point BUTTON_MODEL_PATH to its location."
        )
        raise _yolo_load_error

    _yolo_model = YOLO(model_path)
    print(f"✅ Loaded button-defect model: {model_path}")
    return _yolo_model


class ButtonDetector:
    # Class names produced by the trained YOLOv11 model
    CLASS_BUTTON = 'buttons'
    CLASS_MISALIGNED = 'button_misaligned'
    CLASS_MISSING_GAP = 'missing_button_gap'

    def __init__(self, camera_type='camo', camera_index=1, phone_url='http://localhost:8080/shot.jpg'):
        """
        Initialize Button Detector

        Args:
            camera_type: 'webcam' for USB webcam, 'url' for IP Webcam, 'camo' for Camo app
            camera_index: Index of the camera device (0=default, 1=iPhone via Camo)
            phone_url: URL for IP Webcam app (if using URL method)
        """
        self.expected_buttons = None  # No universal count; garments can have different button counts

        # Inference settings (match the Colab notebook's deployment config)
        self.model_img_size = 640
        self.model_conf_threshold = 0.25  # Matches the successful standalone test; tune on validation images

        # Camera settings - iPhone is index 1
        self.camera_type = camera_type
        self.camera_index = 1  # iPhone via Camo
        self.phone_url = phone_url
        self.upload_dir = 'static/uploads'

        # Image size limits to prevent memory issues
        self.max_image_width = 1280
        self.max_image_height = 960

        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs('static', exist_ok=True)

    # ============================================
    # IMAGE RESIZE & MEMORY MANAGEMENT
    # ============================================

    def resize_image(self, img):
        """
        Resize image to prevent memory issues
        Args:
            img: OpenCV image (numpy array)
        Returns:
            Resized OpenCV image
        """
        if img is None:
            return None

        h, w = img.shape[:2]

        # If image is already small enough, return it
        if w <= self.max_image_width and h <= self.max_image_height:
            return img

        # Calculate scale factor (maintain aspect ratio)
        scale = min(self.max_image_width / w, self.max_image_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Resize image using INTER_AREA for downscaling
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        print(f"📐 Resized image from {w}x{h} to {new_w}x{new_h}")

        # Free memory
        del img
        gc.collect()

        return resized

    def _cleanup_memory(self):
        """Clean up memory after processing"""
        try:
            cv2.destroyAllWindows()
        except:
            pass
        gc.collect()

    # ============================================
    # IMAGE CAPTURE METHODS
    # ============================================

    def capture_image(self):
        """
        Capture image from iPhone or webcam
        Returns: OpenCV image or None
        """
        if self.camera_type == 'url':
            return self._capture_from_url()
        else:
            return self._capture_from_webcam()

    def _capture_from_url(self):
        """Capture from IP Webcam URL (via USB forwarding)"""
        try:
            response = requests.get(self.phone_url, timeout=5)
            if response.status_code == 200:
                img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    # Resize to prevent memory issues
                    img = self.resize_image(img)
                    print("✅ Captured image from phone via USB")
                    self._cleanup_memory()
                    return img
        except Exception as e:
            print(f"❌ Error capturing from URL: {e}")
        return None

    def _capture_from_webcam(self):
        """Capture from iPhone via Camo virtual camera"""
        try:
            # Try iPhone camera indices (1, 2, 3)
            iphone_indices = [1, 2, 3]

            for idx in iphone_indices:
                print(f"🔍 Trying camera index {idx}...")
                cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    time.sleep(0.3)

                    ret, frame = cap.read()
                    cap.release()

                    if ret and frame is not None:
                        # Resize to prevent memory issues
                        frame = self.resize_image(frame)
                        print(f"✅ Captured image from iPhone (camera index {idx})")
                        self._cleanup_memory()
                        return frame
                    else:
                        print(f"⚠️ Camera {idx}: Connected but no image")
                else:
                    print(f"❌ Camera {idx}: Not available")

            # Fallback to webcam
            print("🔄 iPhone not found, trying webcam...")
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    frame = self.resize_image(frame)
                    print("✅ Using webcam as fallback")
                    self._cleanup_memory()
                    return frame

            return None

        except Exception as e:
            print(f"❌ Error capturing from iPhone: {e}")
            self._cleanup_memory()
            return None

    def capture_and_save(self, prefix='iphone'):
        """
        Capture image and save to file
        Returns: file path or None
        """
        img = self.capture_image()
        if img is not None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{prefix}_{timestamp}.jpg'
            filepath = os.path.join(self.upload_dir, filename)
            cv2.imwrite(filepath, img)
            print(f"✅ Image saved: {filepath}")

            # Free memory
            del img
            self._cleanup_memory()

            return filepath
        return None

    def capture_from_image(self, image_path):
        """Load image from file path with resizing"""
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Could not load image from: {image_path}")
            return None
        # Resize to prevent memory issues
        resized = self.resize_image(img)
        self._cleanup_memory()
        return resized

    def process_uploaded_image(self, image_data):
        """
        Process uploaded image from web interface

        Args:
            image_data: Can be one of:
                - File object from Flask request.files
                - Base64 encoded string
                - Bytes data
                - File path (string)
                - OpenCV image (numpy array)

        Returns:
            OpenCV image or None
        """
        try:
            img = None

            # Check if it's a file object (from Flask)
            if hasattr(image_data, 'read'):
                # Read file content
                file_bytes = image_data.read()
                img_array = np.asarray(bytearray(file_bytes), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                print("✅ Processed uploaded file object")

            # Check if it's a base64 string
            elif isinstance(image_data, str) and image_data.startswith('data:image'):
                # Remove the data URL prefix
                base64_data = image_data.split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                img_array = np.asarray(bytearray(img_bytes), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                print("✅ Processed base64 image")

            # Check if it's bytes
            elif isinstance(image_data, bytes):
                img_array = np.asarray(bytearray(image_data), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                print("✅ Processed bytes image")

            # Check if it's a file path
            elif isinstance(image_data, str) and os.path.exists(image_data):
                img = cv2.imread(image_data)
                print(f"✅ Loaded image from path: {image_data}")

            # Check if it's already an OpenCV image
            elif isinstance(image_data, np.ndarray):
                img = image_data
                print("✅ Using existing OpenCV image")

            else:
                print(f"❌ Unsupported image data type: {type(image_data)}")
                return None

            # Resize image if needed
            if img is not None:
                img = self.resize_image(img)
                print(f"✅ Image processed successfully: {img.shape}")
                return img
            else:
                print("❌ Failed to decode image")
                return None

        except Exception as e:
            print(f"❌ Error processing uploaded image: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ============================================
    # DETECTION METHODS (trained YOLOv11 model)
    # ============================================

    def detect_buttons(self, image_source):
        """
        Run the trained YOLOv11 button-defect model on an image source
        (path, array, upload, base64, or None to capture from camera).

        Returns:
            list of detections: [{'class': str, 'confidence': float, 'box': [x1, y1, x2, y2]}, ...]
        """
        img = None

        # Determine image source type
        if image_source is None:
            # Capture from camera
            img = self.capture_image()
        elif isinstance(image_source, str):
            if image_source.startswith('data:image'):
                # Base64 image
                img = self.process_uploaded_image(image_source)
            elif os.path.exists(image_source):
                # File path
                img = cv2.imread(image_source)
                if img is not None:
                    img = self.resize_image(img)
            else:
                raise ValueError(f"Invalid image source: {image_source}")
        elif hasattr(image_source, 'read'):
            # File object (from Flask upload)
            img = self.process_uploaded_image(image_source)
        elif isinstance(image_source, bytes):
            # Bytes data
            img = self.process_uploaded_image(image_source)
        elif isinstance(image_source, np.ndarray):
            # OpenCV image
            img = self.resize_image(image_source)
        else:
            raise TypeError(f"Unknown image source type: {type(image_source)}")

        if img is None:
            raise ValueError("No readable image available for button detection")

        try:
            model = _get_model()

            results = model.predict(
                source=img,
                imgsz=self.model_img_size,
                conf=self.model_conf_threshold,
                save=False,
                verbose=False
            )

            detections = []
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append({
                    'class': class_name,
                    'confidence': confidence,
                    'box': [x1, y1, x2, y2]
                })

            print(f"🔍 Detected {len(detections)} object(s)")
            return detections

        except Exception as e:
            print(f"❌ Detection error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Clean up memory
            if img is not None:
                del img
            self._cleanup_memory()

    def analyze_buttons(self, detections):
        """Combine trained YOLO classes with a cautious geometric gap check.

        A fixed count of seven is NOT assumed. Missing buttons outside the
        observed row cannot be inferred from spacing alone.
        """
        if not detections:
            raise ValueError("No button detections: inspection is inconclusive; retake image")

        normal = [d for d in detections if d['class'] == self.CLASS_BUTTON]
        misaligned = [d for d in detections if d['class'] == self.CLASS_MISALIGNED]
        missing = [d for d in detections if d['class'] == self.CLASS_MISSING_GAP]
        button_detections = normal + misaligned
        count = len(button_detections)
        if count < 3 and not (missing or misaligned):
            raise ValueError("Fewer than three buttons detected; cannot verify button spacing")

        defects = []
        if misaligned:
            defects.append(f"{len(misaligned)} misaligned button(s) detected by YOLO")
        if missing:
            defects.append(f"{len(missing)} missing button gap(s) detected by YOLO")

        # Geometric reasoning on vertically ordered detected button centres.
        # Use the median spacing as the reference, as in the hybrid notebook.
        centers = sorted((d['box'][1] + d['box'][3]) / 2.0 for d in button_detections)
        distances = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        typical_spacing = float(np.median(distances)) if distances else None
        large_gaps = []
        if typical_spacing is not None and typical_spacing > 0:
            large_gaps = [round(distance, 2) for distance in distances
                          if distance > 1.5 * typical_spacing]
        if large_gaps:
            defects.append(f"{len(large_gaps)} unusually large button spacing gap(s) detected")

        has_defect = bool(defects)
        alignment_ok = not misaligned
        spacing_ok = not (missing or large_gaps)
        return {
            'count': count,
            'expected': None,
            'button_count': count,
            'count_ok': None,
            'alignment_ok': alignment_ok,
            'spacing_ok': spacing_ok,
            'has_defect': has_defect,
            'defects': defects,
            'alignment_score': 100.0 if alignment_ok else round(100 * len(normal) / max(count, 1), 2),
            'spacing_score': 100.0 if spacing_ok else 0.0,
            'overall_status': 'FAIL' if has_defect else 'PASS',
            'misaligned_count': len(misaligned),
            'missing_gap_count': len(missing),
            'geometric_gap_count': len(large_gaps),
            'median_spacing': round(typical_spacing, 2) if typical_spacing is not None else None,
            'model': 'YOLO11 garment button detector',
        }

    # ============================================
    # COMPLETE PROCESSING PIPELINE
    # ============================================

    def process_image(self, image_data):
        """
        Complete image processing pipeline:
        1. Load/process image
        2. Detect buttons using the trained YOLOv11 model
        3. Analyze results

        Args:
            image_data: Can be file path, uploaded file, base64 string, or None

        Returns:
            dict with detection results
        """
        print("🔄 Starting image processing pipeline...")

        # Step 1: Get the image
        if image_data is None:
            # Capture from camera
            print("📸 No image provided, capturing from camera...")
            img = self.capture_image()
            if img is None:
                return {
                    'error': 'Failed to capture image from camera',
                    'overall_status': 'ERROR'
                }
        else:
            # Process the provided image
            print("📷 Processing provided image...")
            img = self.process_uploaded_image(image_data)
            if img is None:
                return {
                    'error': 'Failed to process uploaded image',
                    'overall_status': 'ERROR'
                }

        # Step 2: Detect buttons
        print("🔍 Detecting buttons...")
        detections = self.detect_buttons(img)
        del img  # Free memory

        # Step 3: Analyze results
        print("📊 Analyzing button placement...")
        results = self.analyze_buttons(detections)
        del detections  # Free memory

        self._cleanup_memory()
        print(f"✅ Processing complete: {results['overall_status']}")

        return results

    # ============================================
    # TEST METHODS
    # ============================================

    def test_camera(self):
        """Test if iPhone camera is working"""
        print("🔍 Testing iPhone camera...")
        img = self.capture_image()
        if img is not None:
            print("✅ iPhone camera test: SUCCESS")
            print(f"📐 Image shape: {img.shape}")
            del img
            self._cleanup_memory()
            return True
        else:
            print("❌ iPhone camera test: FAILED")
            print("💡 Make sure:")
            print("   1. Camo is running on your iPhone")
            print("   2. Camo Studio is running on your PC")
            print("   3. iPhone is connected via USB-C cable")
            print("   4. You tapped 'Trust' on your iPhone")
            return False

    def find_camera_index(self, max_index=5):
        """Find available camera indices"""
        available = []
        print("🔍 Searching for cameras...")
        print("-" * 40)

        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available.append(i)
                    print(f"✅ Camera {i}: WORKING")
                    # Show preview
                    cv2.imshow(f"Camera {i}", frame)
                    cv2.waitKey(1000)
                    cv2.destroyAllWindows()
                    del frame
                else:
                    print(f"⚠️ Camera {i}: Connected but not reading")
            else:
                print(f"❌ Camera {i}: Not available")
            cap.release()
            self._cleanup_memory()

        print("-" * 40)
        if available:
            print(f"✅ Available camera indices: {available}")
            print(f"📱 Your iPhone should be index 1 (with Camo running)")
        else:
            print("❌ No cameras found!")

        self._cleanup_memory()
        return available

    def test_uploaded_image(self, image_path):
        """Test processing an uploaded image file"""
        print(f"🔍 Testing uploaded image: {image_path}")
        result = self.process_image(image_path)
        print(f"📊 Result: {result}")
        return result
