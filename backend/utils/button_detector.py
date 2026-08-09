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

class ButtonDetector:
    def __init__(self, camera_type='camo', camera_index=1, phone_url='http://localhost:8080/shot.jpg'):
        """
        Initialize Button Detector
        
        Args:
            camera_type: 'webcam' for USB webcam, 'url' for IP Webcam, 'camo' for Camo app
            camera_index: Index of the camera device (0=default, 1=iPhone via Camo)
            phone_url: URL for IP Webcam app (if using URL method)
        """
        self.expected_buttons = 7
        self.tolerance_angle = 5
        self.tolerance_spacing = 15
        
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
    # DETECTION METHODS
    # ============================================
    
    def detect_buttons(self, image_source):
        """
        Detect buttons from image source (path, array, upload, or capture)
        
        Args:
            image_source: file path (str), OpenCV image (numpy array), 
                         uploaded file, base64 string, or None (to capture)
        
        Returns:
            list of bounding boxes [x1, y1, x2, y2]
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
                print(f"❌ Invalid image source: {image_source}")
                return []
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
            print(f"❌ Unknown image source type: {type(image_source)}")
            return []
        
        if img is None:
            print("❌ No image available for detection")
            return []
        
        try:
            # Process image - convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Use Hough Circle Transform for button detection
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=20,
                param1=50,
                param2=30,
                minRadius=8,
                maxRadius=35
            )
            
            boxes = []
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                for (x, y, r) in circles:
                    boxes.append([x-r, y-r, x+r, y+r])
                print(f"🔍 Detected {len(boxes)} buttons")
            else:
                print("🔍 No buttons detected")
            
            # Clean up
            del img
            if 'gray' in locals(): del gray
            if 'blurred' in locals(): del blurred
            if 'circles' in locals(): del circles
            self._cleanup_memory()
            
            return boxes
            
        except Exception as e:
            print(f"❌ Detection error: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # Clean up memory
            if 'img' in locals() and img is not None:
                del img
            self._cleanup_memory()
    
    def analyze_buttons(self, boxes):
        """
        Analyze button placements and detect defects
        
        Args:
            boxes: list of [x1, y1, x2, y2] bounding boxes
        
        Returns:
            dict with analysis results
        """
        if len(boxes) == 0:
            return {
                'count': 0,
                'expected': self.expected_buttons,
                'button_count': 0,
                'count_ok': False,
                'alignment_ok': False,
                'spacing_ok': False,
                'has_defect': True,
                'defects': ['No buttons detected'],
                'alignment_score': 0,
                'spacing_score': 0,
                'overall_status': 'FAIL'
            }
        
        count_ok = len(boxes) == self.expected_buttons
        
        centers = self._get_centers(boxes)
        alignment_ok, alignment_score = self._check_alignment(centers)
        spacing_ok, spacing_score = self._check_spacing(centers)
        
        defects = []
        if not count_ok:
            defects.append(f"Expected {self.expected_buttons} buttons, found {len(boxes)}")
        if not alignment_ok:
            defects.append("Buttons are misaligned")
        if not spacing_ok:
            defects.append("Button spacing is uneven")
        
        has_defect = len(defects) > 0
        
        result = {
            'count': len(boxes),
            'expected': self.expected_buttons,
            'button_count': len(boxes),
            'count_ok': count_ok,
            'alignment_ok': alignment_ok,
            'spacing_ok': spacing_ok,
            'has_defect': has_defect,
            'defects': defects,
            'alignment_score': alignment_score,
            'spacing_score': spacing_score,
            'overall_status': 'FAIL' if has_defect else 'PASS'
        }
        
        # Clean up
        del boxes
        if 'centers' in locals(): del centers
        self._cleanup_memory()
        
        return result
    
    # ============================================
    # COMPLETE PROCESSING PIPELINE
    # ============================================
    
    def process_image(self, image_data):
        """
        Complete image processing pipeline:
        1. Load/process image
        2. Detect buttons
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
        boxes = self.detect_buttons(img)
        del img  # Free memory
        
        # Step 3: Analyze results
        print("📊 Analyzing button placement...")
        results = self.analyze_buttons(boxes)
        del boxes  # Free memory
        
        self._cleanup_memory()
        print(f"✅ Processing complete: {results['overall_status']}")
        
        return results
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _get_centers(self, boxes):
        """Extract center points from bounding boxes"""
        centers = []
        for box in boxes:
            x1, y1, x2, y2 = box
            centers.append([(x1+x2)/2, (y1+y2)/2])
        return np.array(centers)
    
    def _check_alignment(self, centers):
        """Check if buttons are vertically aligned"""
        if len(centers) < 2:
            return False, 0
        
        x_values = centers[:, 0]
        if np.max(x_values) - np.min(x_values) < 10:
            return True, 100
        
        if len(centers) >= 2:
            x1, y1 = centers[0]
            x2, y2 = centers[-1]
            angle = np.degrees(np.arctan2(abs(x2 - x1), abs(y2 - y1)))
            deviation = abs(90 - angle) if angle < 90 else abs(angle - 90)
            score = max(0, 100 - (deviation * 10))
            return deviation <= self.tolerance_angle, min(100, score)
        
        return True, 100
    
    def _check_spacing(self, centers):
        """Check if buttons are evenly spaced"""
        if len(centers) < 3:
            return True, 100
        
        distances = []
        for i in range(len(centers) - 1):
            dist = np.linalg.norm(centers[i] - centers[i+1])
            distances.append(dist)
        
        if len(distances) < 2:
            return True, 100
        
        mean_dist = np.mean(distances)
        ok = True
        max_deviation = 0
        
        for d in distances:
            deviation = abs(d - mean_dist)
            if deviation > self.tolerance_spacing:
                ok = False
                max_deviation = max(max_deviation, deviation)
        
        score = 100 if ok else max(0, 100 - (max_deviation / mean_dist * 100))
        return ok, min(100, score)
    
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