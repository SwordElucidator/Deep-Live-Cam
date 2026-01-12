"""
API Schemas

Pydantic models for request/response validation.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class VideoEncoder(str, Enum):
    """Supported video encoders"""
    LIBX264 = "libx264"
    LIBX265 = "libx265"
    LIBVPX_VP9 = "libvpx-vp9"


class S3Location(BaseModel):
    """AWS S3 file location"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key (path)")
    region: str = Field(default="us-east-1", description="AWS region")
    
    @field_validator('bucket')
    @classmethod
    def validate_bucket(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError("Invalid bucket name")
        return v
    
    @field_validator('key')
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v:
            raise ValueError("S3 key cannot be empty")
        return v
    
    def to_uri(self) -> str:
        """Convert to S3 URI format"""
        return f"s3://{self.bucket}/{self.key}"


class ProcessingOptions(BaseModel):
    """Video processing options"""
    
    # Face swap options
    many_faces: bool = Field(
        default=False,
        description="Replace all detected faces in the video"
    )
    mouth_mask: bool = Field(
        default=False,
        description="Preserve original mouth movements"
    )
    
    # Enhancement
    face_enhancer: bool = Field(
        default=True,
        description="Apply GFPGAN face enhancement"
    )
    
    # Video output options
    keep_fps: bool = Field(
        default=True,
        description="Maintain original video frame rate"
    )
    keep_audio: bool = Field(
        default=True,
        description="Preserve original audio track"
    )
    video_quality: int = Field(
        default=18,
        ge=0,
        le=51,
        description="Video quality CRF (0=best, 51=worst)"
    )
    video_encoder: VideoEncoder = Field(
        default=VideoEncoder.LIBX264,
        description="Video encoder to use"
    )
    
    # Performance options
    execution_threads: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Number of parallel processing threads"
    )


class SwapVideoRequest(BaseModel):
    """Video face swap request"""
    
    job_id: str = Field(
        ...,
        description="Unique job identifier (provided by caller)"
    )
    source_image_s3: S3Location = Field(
        ...,
        description="Source face image S3 location"
    )
    target_video_s3: S3Location = Field(
        ...,
        description="Target video S3 location"
    )
    output_s3: S3Location = Field(
        ...,
        description="Output video S3 location"
    )
    options: ProcessingOptions = Field(
        default_factory=ProcessingOptions,
        description="Processing options"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for completion callback"
    )
    
    @field_validator('job_id')
    @classmethod
    def validate_job_id(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("job_id cannot be empty")
        return v


class ProcessingResult(BaseModel):
    """Processing result details"""
    
    output_s3: Dict[str, str] = Field(
        ...,
        description="Output S3 location"
    )
    processing_time_seconds: float = Field(
        ...,
        description="Total processing time in seconds"
    )
    frames_processed: int = Field(
        ...,
        description="Number of frames processed"
    )
    fps: float = Field(
        ...,
        description="Output video frame rate"
    )
    duration_seconds: float = Field(
        ...,
        description="Video duration in seconds"
    )
    faces_detected: int = Field(
        ...,
        description="Number of faces detected"
    )
    face_enhancer_applied: bool = Field(
        ...,
        description="Whether face enhancement was applied"
    )


class JobStatus(str, Enum):
    """Job status values"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SwapVideoResponse(BaseModel):
    """Video face swap response"""
    
    job_id: str
    status: JobStatus
    result: Optional[ProcessingResult] = None
    error: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class ErrorDetail(BaseModel):
    """Error details"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(default="healthy")
    gpu: Dict[str, Any] = Field(default_factory=dict)
    models: Dict[str, str] = Field(default_factory=dict)
    version: str = Field(default="1.0.0")


class JobProgressResponse(BaseModel):
    """Job progress response"""
    
    job_id: str
    status: JobStatus
    progress: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
