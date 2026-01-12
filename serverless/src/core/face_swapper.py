"""
Face Swapper

Face swapping using InsightFace InSwapper model.
Extracted and enhanced from Deep-Live-Cam modules/processors/frame/face_swapper.py
"""

import os
import threading
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
import insightface

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias
Face = Any


class FaceSwapper:
    """
    Face swapping using InsightFace InSwapper model.
    
    Replaces target faces with source face while maintaining
    target face pose, expression, and lighting.
    
    Features:
    - High-quality face swap with paste_back
    - Optional mouth mask preservation
    - Opacity blending support
    - Thread-safe model loading
    """
    
    _lock = threading.Lock()
    
    def __init__(self, model_path: str, providers: List[str]):
        """
        Initialize face swapper.
        
        Args:
            model_path: Path to inswapper model file (.onnx)
            providers: ONNX execution providers
        """
        logger.info(f"Initializing FaceSwapper with model: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Swapper model not found: {model_path}")
        
        try:
            with self._lock:
                self.model = insightface.model_zoo.get_model(
                    model_path,
                    providers=providers
                )
            logger.info("FaceSwapper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to load swapper model: {e}")
            raise
    
    def swap(
        self,
        source_face: Face,
        target_face: Face,
        frame: np.ndarray,
        mouth_mask: bool = False,
        opacity: float = 1.0
    ) -> np.ndarray:
        """
        Swap target face with source face.
        
        Args:
            source_face: Source face to use
            target_face: Target face to replace
            frame: Input frame (BGR format)
            mouth_mask: Whether to preserve original mouth
            opacity: Blend opacity (0.0-1.0)
            
        Returns:
            Frame with swapped face
        """
        if source_face is None or target_face is None:
            logger.debug("Source or target face is None, skipping swap")
            return frame
        
        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        
        # Ensure contiguous memory layout
        frame = np.ascontiguousarray(frame)
        
        # Store original frame for blending
        original_frame = frame.copy()
        
        try:
            # Perform face swap
            swapped_frame = self.model.get(
                frame,
                target_face,
                source_face,
                paste_back=True
            )
            
            # Validate output
            if swapped_frame is None:
                logger.warning("Face swap returned None, using original frame")
                return original_frame
            
            if not isinstance(swapped_frame, np.ndarray):
                logger.warning("Face swap returned non-array, using original frame")
                return original_frame
            
            # Handle shape mismatch
            if swapped_frame.shape != frame.shape:
                try:
                    swapped_frame = cv2.resize(
                        swapped_frame, 
                        (frame.shape[1], frame.shape[0])
                    )
                except Exception as e:
                    logger.warning(f"Resize failed: {e}")
                    return original_frame
            
            # Ensure uint8
            swapped_frame = np.clip(swapped_frame, 0, 255).astype(np.uint8)
            
            # Apply mouth mask if requested
            if mouth_mask:
                swapped_frame = self._apply_mouth_mask(
                    original_frame,
                    swapped_frame,
                    target_face
                )
            
            # Apply opacity blending
            if opacity < 1.0:
                swapped_frame = cv2.addWeighted(
                    original_frame, 1 - opacity,
                    swapped_frame, opacity,
                    0
                )
            
            return swapped_frame.astype(np.uint8)
            
        except Exception as e:
            logger.error(f"Face swap error: {e}")
            return original_frame
    
    def _apply_mouth_mask(
        self,
        original_frame: np.ndarray,
        swapped_frame: np.ndarray,
        target_face: Face
    ) -> np.ndarray:
        """
        Apply mouth mask to preserve original mouth movements.
        
        Uses facial landmarks to create a smooth mask around the mouth area
        and blends the original mouth onto the swapped face.
        
        Args:
            original_frame: Original frame
            swapped_frame: Frame after face swap
            target_face: Target face with landmarks
            
        Returns:
            Frame with preserved mouth
        """
        try:
            # Check for landmarks
            if not hasattr(target_face, 'landmark_2d_106'):
                return swapped_frame
            
            landmarks = target_face.landmark_2d_106
            if landmarks is None or len(landmarks) < 106:
                return swapped_frame
            
            # Lower lip landmark indices for 106-point model
            # These form the lower lip and chin area
            lower_lip_indices = [
                65, 66, 62, 70, 69,  # Upper lip bottom edge
                18, 19, 20, 21, 22, 23, 24,  # Chin curve
                0, 8, 7, 6, 5, 4, 3, 2  # Jaw line
            ]
            
            # Get mouth region landmarks
            mouth_points = landmarks[lower_lip_indices].astype(np.int32)
            
            # Calculate bounding box with padding
            x_min, y_min = np.min(mouth_points, axis=0)
            x_max, y_max = np.max(mouth_points, axis=0)
            
            # Add padding
            padding = int((x_max - x_min) * 0.15)
            height, width = original_frame.shape[:2]
            
            x_min = max(0, int(x_min) - padding)
            y_min = max(0, int(y_min) - padding)
            x_max = min(width, int(x_max) + padding)
            y_max = min(height, int(y_max) + padding)
            
            if x_max <= x_min or y_max <= y_min:
                return swapped_frame
            
            # Create mask for mouth region
            mask = np.zeros(original_frame.shape[:2], dtype=np.uint8)
            
            # Create convex hull of mouth points
            hull = cv2.convexHull(mouth_points)
            cv2.fillConvexPoly(mask, hull, 255)
            
            # Feather mask edges with Gaussian blur
            feather_size = max(3, (x_max - x_min) // 8)
            feather_size = feather_size if feather_size % 2 == 1 else feather_size + 1
            mask = cv2.GaussianBlur(mask, (feather_size, feather_size), 0)
            
            # Normalize mask to [0, 1]
            mask_float = mask.astype(np.float32) / 255.0
            mask_3ch = mask_float[:, :, np.newaxis]
            
            # Blend original mouth onto swapped frame
            result = (
                swapped_frame.astype(np.float32) * (1 - mask_3ch) +
                original_frame.astype(np.float32) * mask_3ch
            )
            
            return result.astype(np.uint8)
            
        except Exception as e:
            logger.warning(f"Mouth mask error: {e}")
            return swapped_frame
    
    def _create_face_mask(
        self,
        face: Face,
        frame: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Create a mask covering the face area.
        
        Args:
            face: Face object with landmarks
            frame: Frame for mask dimensions
            
        Returns:
            Uint8 mask or None
        """
        try:
            if not hasattr(face, 'landmark_2d_106'):
                return None
            
            landmarks = face.landmark_2d_106
            if landmarks is None or len(landmarks) < 106:
                return None
            
            # Use face outline landmarks (0-32)
            face_outline = landmarks[0:33].astype(np.int32)
            
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            hull = cv2.convexHull(face_outline)
            cv2.fillConvexPoly(mask, hull, 255)
            
            # Blur edges
            mask = cv2.GaussianBlur(mask, (21, 21), 0)
            
            return mask
            
        except Exception as e:
            logger.warning(f"Face mask creation error: {e}")
            return None
