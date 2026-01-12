"""
GPU Utilities

GPU detection and status monitoring.
"""

from typing import Dict, Any, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_gpu_info() -> Dict[str, Any]:
    """
    Get GPU information.
    
    Returns:
        Dictionary with GPU details
    """
    info = {
        "available": False,
        "name": None,
        "memory_total_gb": None,
        "memory_used_gb": None,
        "memory_free_gb": None,
        "cuda_version": None,
    }
    
    try:
        import torch
        
        if torch.cuda.is_available():
            info["available"] = True
            info["cuda_version"] = torch.version.cuda
            
            # Get device info
            device_count = torch.cuda.device_count()
            if device_count > 0:
                device = torch.cuda.current_device()
                info["name"] = torch.cuda.get_device_name(device)
                
                # Memory info
                memory_total = torch.cuda.get_device_properties(device).total_memory
                memory_allocated = torch.cuda.memory_allocated(device)
                memory_reserved = torch.cuda.memory_reserved(device)
                
                info["memory_total_gb"] = round(memory_total / (1024**3), 2)
                info["memory_used_gb"] = round(memory_reserved / (1024**3), 2)
                info["memory_free_gb"] = round((memory_total - memory_reserved) / (1024**3), 2)
                
    except ImportError:
        logger.warning("PyTorch not installed, GPU info unavailable")
    except Exception as e:
        logger.warning(f"Error getting GPU info: {e}")
    
    return info


def check_gpu_available() -> bool:
    """
    Check if GPU is available.
    
    Returns:
        True if CUDA GPU is available
    """
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_gpu_memory_usage() -> Optional[float]:
    """
    Get current GPU memory usage as percentage.
    
    Returns:
        Memory usage percentage (0-100) or None if unavailable
    """
    try:
        import torch
        
        if not torch.cuda.is_available():
            return None
        
        device = torch.cuda.current_device()
        memory_total = torch.cuda.get_device_properties(device).total_memory
        memory_reserved = torch.cuda.memory_reserved(device)
        
        return (memory_reserved / memory_total) * 100
        
    except Exception:
        return None


def clear_gpu_memory() -> None:
    """
    Clear GPU memory cache.
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU memory cache cleared")
            
    except Exception as e:
        logger.warning(f"Error clearing GPU memory: {e}")
