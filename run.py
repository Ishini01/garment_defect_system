from backend.app import app

if __name__ == '__main__':
    print("=" * 50)
    print("👕 Garment Defect Detection System")
    print("=" * 50)
    print("📱 Open http://127.0.0.1:5000 in your browser")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)