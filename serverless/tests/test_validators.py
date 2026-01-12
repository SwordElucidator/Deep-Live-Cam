"""
Tests for input validators
"""

import pytest

from src.api.validators import (
    validate_request,
    validate_s3_location,
    validate_video_constraints,
    ValidationError,
)
from src.api.schemas import S3Location


class TestValidateRequest:
    """Tests for validate_request function"""
    
    def test_valid_request(self):
        """Test validation of valid request"""
        input_data = {
            "job_id": "test-job-123",
            "source_image_s3": {
                "bucket": "my-bucket",
                "key": "inputs/source.jpg",
                "region": "us-east-1"
            },
            "target_video_s3": {
                "bucket": "my-bucket",
                "key": "inputs/target.mp4",
                "region": "us-east-1"
            },
            "output_s3": {
                "bucket": "my-bucket",
                "key": "outputs/result.mp4",
                "region": "us-east-1"
            }
        }
        
        request = validate_request(input_data)
        assert request.job_id == "test-job-123"
        assert request.source_image_s3.bucket == "my-bucket"
    
    def test_invalid_format(self):
        """Test validation error for invalid format"""
        with pytest.raises(ValidationError) as exc_info:
            validate_request({"invalid": "data"})
        
        assert exc_info.value.code == "INVALID_REQUEST"
    
    def test_missing_fields(self):
        """Test validation error for missing required fields"""
        with pytest.raises(ValidationError):
            validate_request({
                "job_id": "test",
                # Missing source_image_s3, target_video_s3, output_s3
            })


class TestValidateS3Location:
    """Tests for validate_s3_location function"""
    
    def test_valid_source_image(self):
        """Test validation of valid source image location"""
        location = S3Location(bucket="bucket", key="path/to/image.jpg")
        # Should not raise
        validate_s3_location(location, "source_image")
    
    def test_valid_source_image_formats(self):
        """Test validation of various image formats"""
        for ext in ['.jpg', '.jpeg', '.png', '.webp', '.JPG', '.PNG']:
            location = S3Location(bucket="bucket", key=f"image{ext}")
            validate_s3_location(location, "source_image")
    
    def test_invalid_source_image_format(self):
        """Test validation error for invalid source image format"""
        location = S3Location(bucket="bucket", key="image.gif")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_s3_location(location, "source_image")
        
        assert exc_info.value.code == "UNSUPPORTED_FORMAT"
    
    def test_valid_target_video(self):
        """Test validation of valid target video location"""
        location = S3Location(bucket="bucket", key="path/to/video.mp4")
        # Should not raise
        validate_s3_location(location, "target_video")
    
    def test_valid_target_video_formats(self):
        """Test validation of various video formats"""
        for ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            location = S3Location(bucket="bucket", key=f"video{ext}")
            validate_s3_location(location, "target_video")
    
    def test_invalid_target_video_format(self):
        """Test validation error for invalid video format"""
        location = S3Location(bucket="bucket", key="video.wmv")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_s3_location(location, "target_video")
        
        assert exc_info.value.code == "UNSUPPORTED_FORMAT"
    
    def test_output_any_format(self):
        """Test that output location accepts any format"""
        location = S3Location(bucket="bucket", key="output.mp4")
        # Should not raise - output validation is less strict
        validate_s3_location(location, "output")


class TestValidateVideoConstraints:
    """Tests for validate_video_constraints function"""
    
    def test_valid_video(self):
        """Test validation of video within constraints"""
        video_info = {
            "duration": 60,  # 1 minute
            "size_mb": 100
        }
        # Should not raise
        validate_video_constraints(video_info)
    
    def test_video_too_long(self):
        """Test validation error for video exceeding duration limit"""
        video_info = {
            "duration": 700,  # > 600s default limit
            "size_mb": 100
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_video_constraints(video_info)
        
        assert exc_info.value.code == "VIDEO_TOO_LONG"
    
    def test_video_too_large(self):
        """Test validation error for video exceeding size limit"""
        video_info = {
            "duration": 60,
            "size_mb": 3000  # > 2048MB default limit
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_video_constraints(video_info)
        
        assert exc_info.value.code == "FILE_TOO_LARGE"
