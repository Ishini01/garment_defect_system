import cv2
import numpy as np

class ButtonDetector:
    def __init__(self):
        self.expected_buttons = 7
        self.tolerance_angle = 5
        self.tolerance_spacing = 15
    
    def detect_buttons(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
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
        
        return boxes
    
    def analyze_buttons(self, boxes):
        if len(boxes) == 0:
            return {
                'count': 0,
                'expected': self.expected_buttons,
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
        
        return {
            'count': len(boxes),
            'expected': self.expected_buttons,
            'count_ok': count_ok,
            'alignment_ok': alignment_ok,
            'spacing_ok': spacing_ok,
            'has_defect': has_defect,
            'defects': defects,
            'alignment_score': alignment_score,
            'spacing_score': spacing_score,
            'overall_status': 'FAIL' if has_defect else 'PASS'
        }
    
    def _get_centers(self, boxes):
        centers = []
        for box in boxes:
            x1, y1, x2, y2 = box
            centers.append([(x1+x2)/2, (y1+y2)/2])
        return np.array(centers)
    
    def _check_alignment(self, centers):
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