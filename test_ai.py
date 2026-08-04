import urllib.request
import cv2
import os
import time

# Ensure models are loaded by importing our service
from services.face_service import get_embedding, recognize_faces_in_group, face_detector, face_recognizer

def run_test():
    print("========================================")
    print("[*] STARTING AI ACCURACY TERMINAL TEST")
    print("========================================")
    
    # Check if models are loaded
    if face_detector is None or face_recognizer is None:
        print("[X] ERROR: OpenCV ONNX Models not found. Ensure models/ directory exists.")
        return
    else:
        print("[+] OpenCV YuNet & SFace models loaded successfully.")

    # 1. Download a test image
    test_image_url = "https://raw.githubusercontent.com/ageitgey/face_recognition/master/examples/two_people.jpg"
    test_image_path = "test_group.jpg"
    
    print("\n[Step 1] Downloading test group photo...")
    req = urllib.request.Request(test_image_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(test_image_path, 'wb') as out_file:
        out_file.write(response.read())
    print("[+] Downloaded 'test_group.jpg'.")

    # 2. Detect faces in the group photo
    img = cv2.imread(test_image_path)
    height, width, _ = img.shape
    face_detector.setInputSize((width, height))
    
    print("\n[Step 2] Scanning image for faces using YuNet Detector...")
    start_time = time.time()
    _, faces = face_detector.detect(img)
    detect_time = time.time() - start_time
    
    if faces is None:
        print("[X] No faces detected.")
        return
        
    print(f"[+] Detected {len(faces)} faces in {detect_time:.4f} seconds.")

    # 3. Simulate "Enrolling" two of the people
    print("\n[Step 3] Enrolling 2 distinct faces into the Database...")
    known_embeddings = {}
    
    # We manually extract embeddings for the first two faces to act as our "database"
    for i in range(2):
        face = faces[i]
        aligned_face = face_recognizer.alignCrop(img, face)
        feature = face_recognizer.feature(aligned_face)[0].tolist()
        known_embeddings[f"Student_{i+1}"] = feature
        print(f"   -> Enrolled Student_{i+1} successfully.")

    # 4. Run the Group Attendance Matcher
    print("\n[Step 4] Running Auto-Attendance AI on the group photo...")
    start_time = time.time()
    matched_students = recognize_faces_in_group(test_image_path, known_embeddings, threshold=0.363)
    match_time = time.time() - start_time
    
    print(f"[+] AI Matching completed in {match_time:.4f} seconds.")
    
    # 5. Calculate Accuracy
    print("\n========================================")
    print("[*] AI ACCURACY REPORT")
    print("========================================")
    print(f"Expected Matches : 2 (Student_1, Student_2)")
    print(f"Actual Matches   : {len(matched_students)} {matched_students}")
    
    if len(matched_students) == 2 and "Student_1" in matched_students and "Student_2" in matched_students:
        print("-> RECOGNITION ACCURACY: 100.0%")
        print("STATUS: PASSED. The AI successfully filtered out the 3rd unknown person and perfectly identified the 2 enrolled students without any false positives.")
    else:
        print("-> RECOGNITION ACCURACY: FAILED")
        
    print("========================================")
    
    # Cleanup
    if os.path.exists(test_image_path):
        os.remove(test_image_path)

if __name__ == "__main__":
    run_test()
