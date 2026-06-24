import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import cv2
import numpy as np

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    HAS_MEDIAPIPE = True
except Exception as e:
    print(f"MediaPipe initialization failed (Likely Protobuf conflict): {e}. Stress tracking will run in Mock Mode.")
    HAS_MEDIAPIPE = False

def analyze_stress_and_focus(frame_np: np.ndarray) -> dict:
    """
    Uses MediaPipe to detect if the user is looking at the screen (focus)
    and extracts basic stress indicators.
    """
    if not HAS_MEDIAPIPE:
        return {"focused": True}
        
    try:
        rgb_frame = cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        is_focused = False
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            
            # Simple heuristic: Check nose tip (1) relative to face edges
            nose_x = face_landmarks.landmark[1].x
            
            # If nose is relatively centered horizontally, they are looking at the screen
            if 0.35 < nose_x < 0.65:
                is_focused = True
                
        return {"focused": is_focused}
    except Exception as e:
        print(f"MediaPipe Error: {e}")
        return {"focused": True} # Fallback
