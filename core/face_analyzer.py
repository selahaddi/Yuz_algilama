import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis

class FaceAnalyzer:
    def __init__(self, gpu_id=0):
        """
        Initialize the InsightFace analysis app.
        Will use CUDA (GPU) if available and onnxruntime-gpu is installed, otherwise falls back to CPU.
        Set USE_GPU=0 environment variable to skip GPU probe (faster startup on Cloud Run).
        """
        # Cloud Run'da GPU yoktur, gereksiz CUDA probe atlanır
        use_gpu = os.environ.get("USE_GPU", "0") == "1"
        if use_gpu:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']
        
        # 'buffalo_s' is a smaller, much faster model with good accuracy.
        self.app = FaceAnalysis(name='buffalo_s', providers=providers)
        
        # Prepare the model. ctx_id=0 means GPU 0. If no GPU, it will use CPU.
        # det_size is the input size for the detection model. 640x640 is optimized for buffalo_s.
        self.app.prepare(ctx_id=gpu_id, det_size=(640, 640))
        
    def analyze_image(self, image: np.ndarray):
        """
        Analyze an image to detect faces and extract embeddings.
        
        :param image: numpy array of the image (BGR format, as loaded by OpenCV)
        :return: List of face objects containing bbox, kps, det_score, and embedding.
        """
        faces = self.app.get(image)
        return faces
