import cv2

print("🔍 TESTING ALL CAMERAS...")
print("=" * 40)

for i in range(6):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✅ Camera {i}: WORKING")
            # Show what the camera sees
            cv2.imshow(f"Camera {i} - Press any key", frame)
            cv2.waitKey(1500)
            cv2.destroyAllWindows()
        else:
            print(f"⚠️ Camera {i}: Connected but no image")
    else:
        print(f"❌ Camera {i}: Not available")
    cap.release()

print("=" * 40)
print("📱 Your iPhone is usually Camera 1 or 2")
print("💡 Camera 0 is usually your desktop webcam")