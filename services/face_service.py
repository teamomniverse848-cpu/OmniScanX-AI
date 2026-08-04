import cv2
import numpy as np
import base64
import json
import os

# Initialize OpenCV Face Detector (YuNet) and Face Recognizer (SFace)
# We load these from the models directory. They don't require tensorflow/pytorch.
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
detector_model = os.path.join(base_dir, 'models', 'face_detection_yunet.onnx')
recognizer_model = os.path.join(base_dir, 'models', 'face_recognition_sface.onnx')

# Ensure models exist before initializing
if os.path.exists(detector_model) and os.path.exists(recognizer_model):
    face_detector = cv2.FaceDetectorYN.create(detector_model, "", (320, 320), 0.9, 0.3, 5000)
    face_recognizer = cv2.FaceRecognizerSF.create(recognizer_model, "")
else:
    face_detector = None
    face_recognizer = None

def get_embedding(image_path):
    """
    Extracts the facial embedding (vector) from an image using OpenCV SFace.
    """
    if face_detector is None or face_recognizer is None:
        print("OpenCV ONNX models missing.")
        return None
        
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        height, width, _ = img.shape
        face_detector.setInputSize((width, height))
        
        _, faces = face_detector.detect(img)
        if faces is not None and len(faces) > 0:
            # Assume 1 face for enrollment
            face = faces[0]
            # Align face
            aligned_face = face_recognizer.alignCrop(img, face)
            # Get 128D feature vector
            feature = face_recognizer.feature(aligned_face)
            return feature[0].tolist()
            
        return None
    except Exception as e:
        print(f"Face extraction error: {e}")
        return None

def cosine_distance(a, b):
    """
    Calculates cosine distance between two vectors.
    """
    a = np.array(a)
    b = np.array(b)
    
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    
    if a_norm == 0 or b_norm == 0:
        return 2.0
        
    cos_sim = np.dot(a, b) / (a_norm * b_norm)
    return 1 - cos_sim

def recognize_faces_in_group(group_image_path, known_embeddings_dict, threshold=0.363):
    """
    Takes a group photo and a dictionary of known embeddings {student_id: embedding_vector}
    Returns a list of student_ids that were matched in the photo.
    OpenCV SFace cosine distance threshold is usually 0.363
    """
    if face_detector is None or face_recognizer is None:
        return []
        
    matched_student_ids = set()
    
    try:
        img = cv2.imread(group_image_path)
        if img is None:
            return []
            
        height, width, _ = img.shape
        face_detector.setInputSize((width, height))
        
        _, faces = face_detector.detect(img)
        if faces is None or len(faces) == 0:
            return []
            
        for face in faces:
            aligned_face = face_recognizer.alignCrop(img, face)
            face_feature = face_recognizer.feature(aligned_face)[0]
            
            best_match_id = None
            best_distance = float('inf')
            
            for student_id, known_emb_list in known_embeddings_dict.items():
                if type(known_emb_list) == str:
                    known_emb_list = json.loads(known_emb_list)
                    
                # In multi-angle enrollment, known_emb_list is a list of embeddings
                # We need to ensure we handle cases where it might be a single embedding vs a list of embeddings
                # If it's a list of lists (multi-angle), we iterate. If it's just a single list (old enrollment), wrap it.
                if len(known_emb_list) > 0 and type(known_emb_list[0]) != list:
                    known_emb_list = [known_emb_list]
                    
                for known_emb in known_emb_list:
                    dist = cosine_distance(face_feature, known_emb)
                    
                    if dist < best_distance:
                        best_distance = dist
                        best_match_id = student_id
            
            if best_distance <= threshold and best_match_id is not None:
                matched_student_ids.add(best_match_id)
                
        return list(matched_student_ids)
        
    except Exception as e:
        print(f"Group recognition error: {e}")
        return []

def base64_to_image(base64_string, output_path):
    """
    Helper to save a base64 webcam image to disk.
    """
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
        
    img_data = base64.b64decode(base64_string)
    with open(output_path, "wb") as fh:
        fh.write(img_data)
    return output_path
