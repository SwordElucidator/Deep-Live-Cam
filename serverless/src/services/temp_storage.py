"""
Temporary Storage Service

Manages temporary files for job processing.
"""

import os
import shutil
from pathlib import Path

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TempStorage:
    """
    Temporary storage manager for job processing.
    
    Creates a dedicated directory for each job and handles cleanup.
    """
    
    def __init__(self, job_id: str):
        """
        Initialize temp storage for a job.
        
        Args:
            job_id: Unique job identifier
        """
        self.job_id = job_id
        self.job_dir = os.path.join(settings.temp_dir, job_id)
        
        # Create job directory
        Path(self.job_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temp directory: {self.job_dir}")
    
    def get_path(self, filename: str) -> str:
        """
        Get full path for a file in the job directory.
        
        Args:
            filename: File name
            
        Returns:
            Full file path
        """
        return os.path.join(self.job_dir, filename)
    
    def get_frames_dir(self) -> str:
        """
        Get path to frames directory and create it.
        
        Returns:
            Frames directory path
        """
        frames_dir = os.path.join(self.job_dir, "frames")
        Path(frames_dir).mkdir(parents=True, exist_ok=True)
        return frames_dir
    
    def cleanup(self) -> None:
        """
        Remove all temporary files for this job.
        """
        if os.path.exists(self.job_dir):
            try:
                shutil.rmtree(self.job_dir)
                logger.info(f"Cleaned up temp directory: {self.job_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - always cleanup"""
        self.cleanup()
        return False
    
    @property
    def size_mb(self) -> float:
        """Get total size of temp directory in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.job_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)
