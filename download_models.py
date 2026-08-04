import os
import urllib.request

os.makedirs('models', exist_ok=True)

urls = {
    'models/face_detection_yunet.onnx': 'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx',
    'models/face_recognition_sface.onnx': 'https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx'
}

for path, url in urls.items():
    if not os.path.exists(path):
        print(f"Downloading {path}...")
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {path}")
    else:
        print(f"{path} already exists")
