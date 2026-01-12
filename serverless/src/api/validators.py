"""
Request Validators

Input validation for API requests.
"""

from typing import Dict, Any

from src.api.schemas import SwapVideoRequest, S3Location, ProcessingOptions
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Validation error with code"""
    
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_request(input_data: Dict[str, Any]) -> SwapVideoRequest:
    """
    Validate and parse incoming request data.
    
    Args:
        input_data: Raw input dictionary
        
    Returns:
        Validated SwapVideoRequest
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        # Parse request
        request = SwapVideoRequest(**input_data)
        
        # Additional validations
        validate_s3_location(request.source_image_s3, "source_image")
        validate_s3_location(request.target_video_s3, "target_video")
        validate_s3_location(request.output_s3, "output")
        
        logger.info("Request validation passed")
        return request
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError("INVALID_REQUEST", f"Invalid request format: {str(e)}")


def validate_s3_location(location: S3Location, field_name: str) -> None:
    """
    Validate S3 location.
    
    Args:
        location: S3Location to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If validation fails
    """
    if not location.bucket:
        raise ValidationError(
            "INVALID_S3_LOCATION",
            f"{field_name}: bucket name is required"
        )
    
    if not location.key:
        raise ValidationError(
            "INVALID_S3_LOCATION",
            f"{field_name}: object key is required"
        )
    
    # Validate file extensions for specific fields
    if field_name == "source_image":
        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        if not location.key.lower().endswith(valid_extensions):
            raise ValidationError(
                "UNSUPPORTED_FORMAT",
                f"Source image must be one of: {valid_extensions}"
            )
    
    if field_name == "target_video":
        valid_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        if not location.key.lower().endswith(valid_extensions):
            raise ValidationError(
                "UNSUPPORTED_FORMAT",
                f"Target video must be one of: {valid_extensions}"
            )


def validate_video_constraints(video_info: Dict[str, Any]) -> None:
    """
    Validate video against size/duration constraints.
    
    Args:
        video_info: Video information dictionary
        
    Raises:
        ValidationError: If constraints are violated
    """
    duration = video_info.get('duration', 0)
    if duration > settings.max_video_duration:
        raise ValidationError(
            "VIDEO_TOO_LONG",
            f"Video duration {duration}s exceeds maximum {settings.max_video_duration}s"
        )
    
    size_mb = video_info.get('size_mb', 0)
    if size_mb > settings.max_video_size_mb:
        raise ValidationError(
            "FILE_TOO_LARGE",
            f"Video size {size_mb}MB exceeds maximum {settings.max_video_size_mb}MB"
        )
