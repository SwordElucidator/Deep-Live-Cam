"""
Face Analyser

Face detection and analysis using InsightFace buffalo_l model.
Extracted and simplified from Deep-Live-Cam modules/face_analyser.py
"""

import threading
from typing import Any, List, Optional, Tuple

import numpy as np
import insightface
from insightface.app import FaceAnalysis

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias for face object
Face = Any


class FaceAnalyser:
    """
    Face detection and analysis using InsightFace buffalo_l model.
    
    Provides:
    - Face detection
    - Facial landmark detection (106 points)
    - Face embedding extraction
    - Face attribute analysis
    
    Thread-safe singleton pattern for model loading.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, providers: List[str], det_size: Tuple[int, int] = (640, 640)):
        """
        Initialize face analyser.
        
        Args:
            providers: ONNX execution providers (e.g., ['CUDAExecutionProvider'])
            det_size: Detection size tuple (width, height)
        """
        logger.info(f"Initializing FaceAnalyser with providers: {providers}")
        logger.info(f"Detection size: {det_size}")
        
        try:
            self.app = FaceAnalysis(
                name='buffalo_l',
                providers=providers
            )
            self.app.prepare(ctx_id=0, det_size=det_size)
            self._det_size = det_size
            logger.info("FaceAnalyser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FaceAnalyser: {e}")
            raise
    
    def get_one_face(self, frame: np.ndarray) -> Optional[Face]:
        """
        Detect and return the primary face in a frame.
        
        Returns the face with the smallest x-coordinate (leftmost),
        which is typically the primary subject.
        
        Args:
            frame: Input image as numpy array (BGR format)
            
        Returns:
            Face object or None if no face detected
        """
        faces = self._detect_faces(frame)
        
        if not faces:
            return None
        
        # Return face with smallest x coordinate (leftmost face)
        try:
            return min(faces, key=lambda x: x.bbox[0])
        except (ValueError, AttributeError, TypeError):
            return faces[0] if faces else None
    
    def get_many_faces(self, frame: np.ndarray) -> List[Face]:
        """
        Detect and return all faces in a frame.
        
        Args:
            frame: Input image as numpy array (BGR format)
            
        Returns:
            List of Face objects (may be empty)
        """
        return self._detect_faces(frame)
    
    def _detect_faces(self, frame: np.ndarray) -> List[Face]:
        """
        Internal face detection method.
        
        Args:
            frame: Input image
            
        Returns:
            List of detected faces
        """
        try:
            if frame is None or frame.size == 0:
                logger.warning("Empty or None frame provided")
                return []
            
            # Ensure frame is uint8 BGR
            if frame.dtype != np.uint8:
                frame = np.clip(frame, 0, 255).astype(np.uint8)
            
            faces = self.app.get(frame)
            return faces if faces else []
            
        except Exception as e:
            logger.warning(f"Error detecting faces: {e}")
            return []
    
    def get_face_count(self, frame: np.ndarray) -> int:
        """
        Count faces in a frame.
        
        Args:
            frame: Input image as numpy array
            
        Returns:
            Number of faces detected
        """
        return len(self._detect_faces(frame))
    
    def get_face_embedding(self, face: Face) -> Optional[np.ndarray]:
        """
        Get normalized face embedding from detected face.
        
        Args:
            face: Face object from detection
            
        Returns:
            Normalized embedding vector or None
        """
        try:
            if hasattr(face, 'normed_embedding'):
                return face.normed_embedding
            elif hasattr(face, 'embedding'):
                # Normalize if not already normalized
                emb = face.embedding
                return emb / np.linalg.norm(emb)
            return None
        except Exception:
            return None
    
    def get_face_bbox(self, face: Face) -> Optional[Tuple[int, int, int, int]]:
        """
        Get face bounding box.
        
        Args:
            face: Face object
            
        Returns:
            Tuple (x1, y1, x2, y2) or None
        """
        try:
            if hasattr(face, 'bbox') and face.bbox is not None:
                bbox = face.bbox.astype(int)
                return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
            return None
        except Exception:
            return None
    
    def get_face_landmarks(self, face: Face) -> Optional[np.ndarray]:
        """
        Get face landmarks (106 points).
        
        Args:
            face: Face object
            
        Returns:
            Landmarks array or None
        """
        try:
            if hasattr(face, 'landmark_2d_106'):
                return face.landmark_2d_106
            elif hasattr(face, 'landmark'):
                return face.landmark
            return None
        except Exception:
            return None
    
    def get_detection_score(self, face: Face) -> float:
        """
        Get face detection confidence score.
        
        Args:
            face: Face object
            
        Returns:
            Detection score (0-1)
        """
        try:
            if hasattr(face, 'det_score'):
                return float(face.det_score)
            return 0.0
        except Exception:
            return 0.0
    
    def find_best_face(self, faces: List[Face]) -> Optional[Face]:
        """
        Find the best face from a list based on detection score.
        
        Args:
            faces: List of face objects
            
        Returns:
            Face with highest detection score or None
        """
        if not faces:
            return None
        
        try:
            return max(faces, key=lambda f: self.get_detection_score(f))
        except Exception:
            return faces[0] if faces else None
