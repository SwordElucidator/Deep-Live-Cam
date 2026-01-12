"""
Configuration Management

Load settings from environment variables with sensible defaults.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # ==========================================
    # AWS Configuration
    # ==========================================
    aws_access_key_id: str = Field(
        default="",
        description="AWS Access Key ID"
    )
    aws_secret_access_key: str = Field(
        default="",
        description="AWS Secret Access Key"
    )
    aws_default_region: str = Field(
        default="us-east-1",
        description="AWS default region"
    )
    
    # ==========================================
    # Model Paths
    # ==========================================
    models_dir: str = Field(
        default="/app/models",
        description="Directory containing model files"
    )
    
    # ==========================================
    # Processing Configuration
    # ==========================================
    execution_provider: str = Field(
        default="cuda",
        description="ONNX execution provider (cuda, cpu)"
    )
    execution_threads: int = Field(
        default=8,
        description="Number of parallel processing threads"
    )
    
    # ==========================================
    # Limits
    # ==========================================
    max_video_duration: int = Field(
        default=600,
        description="Maximum video duration in seconds (10 min)"
    )
    max_video_size_mb: int = Field(
        default=2048,
        description="Maximum video file size in MB (2 GB)"
    )
    max_source_image_size_mb: int = Field(
        default=10,
        description="Maximum source image size in MB"
    )
    
    # ==========================================
    # Logging
    # ==========================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # ==========================================
    # Temp Storage
    # ==========================================
    temp_dir: str = Field(
        default="/tmp/face_swap_jobs",
        description="Temporary directory for processing"
    )
    
    # ==========================================
    # Callback Configuration
    # ==========================================
    callback_timeout: int = Field(
        default=30,
        description="Webhook callback timeout in seconds"
    )
    callback_max_retries: int = Field(
        default=3,
        description="Maximum callback retry attempts"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def swapper_model_path(self) -> str:
        """Path to face swapper model"""
        return os.path.join(self.models_dir, "inswapper_128_fp16.onnx")
    
    @property
    def enhancer_model_path(self) -> str:
        """Path to face enhancer model"""
        return os.path.join(self.models_dir, "GFPGANv1.4.pth")
    
    @property
    def execution_providers(self) -> List[str]:
        """Get ONNX execution providers list"""
        provider_map = {
            "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
            "cpu": ["CPUExecutionProvider"],
            "tensorrt": ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        }
        return provider_map.get(
            self.execution_provider.lower(), 
            ["CPUExecutionProvider"]
        )
    
    def validate_aws_credentials(self) -> bool:
        """Check if AWS credentials are configured"""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)


# Global settings instance
settings = Settings()
