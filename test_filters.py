import os
import cv2
from core.face_analyzer import FaceAnalyzer

# Initialize analyzer
analyzer = FaceAnalyzer(gpu_id=0)

DIR = "/home/selahaddin/Belgeler/denemeresim"
for filename in os.listdir(DIR):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    filepath = os.path.join(DIR, filename)
    img = cv2.imread(filepath)
    if img is None:
        continue
        
    faces = analyzer.analyze_image(img)
    print(f"\n--- {filename} ---")
    print(f"Bulunan yüz sayısı: {len(faces)}")
    
    for i, face in enumerate(faces):
        bbox = face.bbox
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        det_score = face.det_score
        
        # Blur score
        crop_img = img[max(0, int(y1)):min(img.shape[0], int(y2)), 
                       max(0, int(x1)):min(img.shape[1], int(x2))]
        blur_score = 0
        if crop_img.size > 0:
            gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            
        print(f"Yüz {i+1}: Boyut={width:.1f}x{height:.1f}, Skor={det_score:.3f}, Blur={blur_score:.1f}")
        
        if width < 60 or height < 60:
            print("  -> RED: Boyut (60'tan küçük)")
        if det_score < 0.7:
            print("  -> RED: Skor (0.7'den küçük)")
        if blur_score < 100.0:
            print("  -> RED: Blur (100.0'den küçük)")
