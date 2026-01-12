"""
Face Enhancer

Face enhancement using GFPGAN model.
Extracted from Deep-Live-Cam modules/processors/frame/face_enhancer.py
"""

import os
import platform
import threading
from typing import Optional

import numpy as np
import torch

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FaceEnhancer:
    """
    Face enhancement using GFPGAN model.
    
    Improves face quality by:
    - Removing artifacts from face swap
    - Enhancing facial details
    - Improving skin texture
    - Fixing inconsistencies
    
    Supports CUDA, MPS (Apple Silicon), and CPU.
    """
    
    _lock = threading.Lock()
    _semaphore = threading.Semaphore(1)  # Limit concurrent enhancements
    
    def __init__(self, model_path: str):
        """
        Initialize face enhancer.
        
        Args:
            model_path: Path to GFPGAN model file (.pth)
        """
        logger.info(f"Initializing FaceEnhancer with model: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Enhancer model not found: {model_path}")
        
        # Select best available device
        device = self._select_device()
        logger.info(f"Using device: {device}")
        
        try:
            # Import GFPGAN
            import gfpgan
            
            with self._lock:
                self.enhancer = gfpgan.GFPGANer(
                    model_path=model_path,
                    upscale=1,  # No upscaling, just enhancement
                    arch='clean',
                    channel_multiplier=2,
                    bg_upsampler=None,
                    device=device
                )
            
            self._device = device
            logger.info("FaceEnhancer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize FaceEnhancer: {e}")
            # Try fallback to CPU
            if device.type != 'cpu':
                logger.info("Attempting fallback to CPU...")
                try:
                    import gfpgan
                    device = torch.device("cpu")
                    self.enhancer = gfpgan.GFPGANer(
                        model_path=model_path,
                        upscale=1,
                        arch='clean',
                        channel_multiplier=2,
                        bg_upsampler=None,
                        device=device
                    )
                    self._device = device
                    logger.info("FaceEnhancer initialized on CPU (fallback)")
                except Exception as fallback_e:
                    logger.error(f"CPU fallback failed: {fallback_e}")
                    raise
            else:
                raise
    
    def _select_device(self) -> torch.device:
        """
        Select the best available device.
        
        Priority: CUDA > MPS > CPU
        
        Returns:
            torch.device for computation
        """
        # Priority 1: CUDA
        if torch.cuda.is_available():
            return torch.device("cuda")
        
        # Priority 2: MPS (Apple Silicon)
        if platform.system() == "Darwin":
            try:
                if torch.backends.mps.is_available():
                    return torch.device("mps")
            except AttributeError:
                pass  # MPS not available in this PyTorch version
        
        # Priority 3: CPU
        return torch.device("cpu")
    
    def enhance(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance faces in a frame.
        
        Args:
            frame: Input frame (BGR format, uint8)
            
        Returns:
            Enhanced frame (BGR format, uint8)
        """
        if frame is None or frame.size == 0:
            logger.warning("Empty frame provided to enhancer")
            return frame
        
        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        
        try:
            with self._semaphore:
                # GFPGAN enhance method returns:
                # (cropped_faces, restored_faces, restored_img)
                _, _, restored_img = self.enhancer.enhance(
                    frame,
                    has_aligned=False,  # Faces are not pre-aligned
                    only_center_face=False,  # Enhance all detected faces
                    paste_back=True  # Paste enhanced faces back
                )
            
            if restored_img is None:
                logger.debug("Enhancement returned None, using original")
                return frame
            
            # Ensure output is uint8
            if restored_img.dtype != np.uint8:
                restored_img = np.clip(restored_img, 0, 255).astype(np.uint8)
            
            return restored_img
            
        except Exception as e:
            logger.warning(f"Enhancement error: {e}")
            return frame
    
    def get_device_info(self) -> dict:
        """
        Get information about the device being used.
        
        Returns:
            Device information dictionary
        """
        info = {
            "device_type": self._device.type,
            "cuda_available": torch.cuda.is_available(),
        }
        
        if self._device.type == "cuda":
            info["cuda_device_name"] = torch.cuda.get_device_name()
            info["cuda_memory_total_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        return info
