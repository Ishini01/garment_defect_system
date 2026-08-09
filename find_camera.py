import cv2

print("=" * 50)
print("📷 CAMERA DETECTION TOOL")
print("=" * 50)

print("\n🔍 Searching for cameras...")
print("-" * 40)

available_cameras = []

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ Camera {i}: WORKING")
            available_cameras.append(i)
            # Show a small preview
            cv2.imshow(f"Camera {i} - Press any key to continue", frame)
            cv2.waitKey(1000)
            cv2.destroyAllWindows()
        else:
            print(f"⚠️ Camera {i}: Connected but no image")
    else:
        print(f"❌ Camera {i}: NOT AVAILABLE")
    cap.release()

print("-" * 40)

if available_cameras:
    print(f"\n✅ Available cameras: {available_cameras}")
    print("\n💡 Camera 0 is usually your built-in webcam")
    print("📱 Your iPhone (via Camo) will be Camera 1 or 2")
    print(f"\n👉 Set CAMERA_INDEX = {available_cameras[-1]} in app.py")
else:
    print("\n❌ No cameras found! Please connect a camera.")

print("=" * 50)