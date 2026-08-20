import os
from insightface.app import FaceAnalysis

def download_models():
    print("InsightFace modeli indiriliyor ve onnxruntime hazırlanıyor...")
    # 'buffalo_s' daha hızlı yüz tanıma modelidir.
    app = FaceAnalysis(name='buffalo_s', root='/home/user/.insightface')
    app.prepare(ctx_id=0, det_size=(640, 640))
    print("Model başarıyla indirildi ve hazır!")

if __name__ == "__main__":
    download_models()
