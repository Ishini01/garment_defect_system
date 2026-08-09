import cv2

print("=" * 50)
print("📱 FINDING IPHONE CAMERA")
print("=" * 50)

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"✅ Camera {i}: WORKING - This is your iPhone!")
            cv2.imshow(f"iPhone Camera {i}", frame)
            cv2.waitKey(2000)
            cv2.destroyAllWindows()
        else:
            print(f"⚠️ Camera {i}: Connected but no image")
    else:
        print(f"❌ Camera {i}: Not available")
    cap.release()

print("\n📱 Your iPhone is the camera that showed a preview!")
print("🔢 Remember the number (usually 1 or 2)")