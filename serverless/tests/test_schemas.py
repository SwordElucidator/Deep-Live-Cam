"""
Tests for API schemas
"""

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    S3Location,
    ProcessingOptions,
    SwapVideoRequest,
    SwapVideoResponse,
    JobStatus,
    VideoEncoder,
)


class TestS3Location:
    """Tests for S3Location schema"""
    
    def test_valid_s3_location(self):
        """Test valid S3 location creation"""
        location = S3Location(
            bucket="my-bucket",
            key="path/to/file.mp4",
            region="us-east-1"
        )
        assert location.bucket == "my-bucket"
        assert location.key == "path/to/file.mp4"
        assert location.region == "us-east-1"
    
    def test_default_region(self):
        """Test default region is us-east-1"""
        location = S3Location(bucket="bucket", key="key")
        assert location.region == "us-east-1"
    
    def test_to_uri(self):
        """Test S3 URI generation"""
        location = S3Location(bucket="my-bucket", key="path/to/file.mp4")
        assert location.to_uri() == "s3://my-bucket/path/to/file.mp4"
    
    def test_invalid_bucket(self):
        """Test validation error for invalid bucket"""
        with pytest.raises(ValidationError):
            S3Location(bucket="", key="key")
    
    def test_invalid_key(self):
        """Test validation error for empty key"""
        with pytest.raises(ValidationError):
            S3Location(bucket="bucket", key="")


class TestProcessingOptions:
    """Tests for ProcessingOptions schema"""
    
    def test_default_values(self):
        """Test default processing options"""
        options = ProcessingOptions()
        
        assert options.many_faces is False
        assert options.mouth_mask is False
        assert options.face_enhancer is True
        assert options.keep_fps is True
        assert options.keep_audio is True
        assert options.video_quality == 18
        assert options.video_encoder == VideoEncoder.LIBX264
        assert options.execution_threads == 8
    
    def test_custom_values(self):
        """Test custom processing options"""
        options = ProcessingOptions(
            many_faces=True,
            face_enhancer=False,
            video_quality=23,
            video_encoder=VideoEncoder.LIBX265
        )
        
        assert options.many_faces is True
        assert options.face_enhancer is False
        assert options.video_quality == 23
        assert options.video_encoder == VideoEncoder.LIBX265
    
    def test_video_quality_bounds(self):
        """Test video quality validation"""
        # Valid range: 0-51
        options = ProcessingOptions(video_quality=0)
        assert options.video_quality == 0
        
        options = ProcessingOptions(video_quality=51)
        assert options.video_quality == 51
        
        # Invalid: out of range
        with pytest.raises(ValidationError):
            ProcessingOptions(video_quality=-1)
        
        with pytest.raises(ValidationError):
            ProcessingOptions(video_quality=52)
    
    def test_execution_threads_bounds(self):
        """Test execution threads validation"""
        # Valid range: 1-32
        options = ProcessingOptions(execution_threads=1)
        assert options.execution_threads == 1
        
        options = ProcessingOptions(execution_threads=32)
        assert options.execution_threads == 32
        
        # Invalid: out of range
        with pytest.raises(ValidationError):
            ProcessingOptions(execution_threads=0)
        
        with pytest.raises(ValidationError):
            ProcessingOptions(execution_threads=33)


class TestSwapVideoRequest:
    """Tests for SwapVideoRequest schema"""
    
    def test_valid_request(self):
        """Test valid request creation"""
        request = SwapVideoRequest(
            job_id="test-job-123",
            source_image_s3=S3Location(bucket="bucket", key="source.jpg"),
            target_video_s3=S3Location(bucket="bucket", key="target.mp4"),
            output_s3=S3Location(bucket="bucket", key="output.mp4")
        )
        
        assert request.job_id == "test-job-123"
        assert request.source_image_s3.key == "source.jpg"
        assert request.callback_url is None
    
    def test_request_with_options(self):
        """Test request with custom options"""
        request = SwapVideoRequest(
            job_id="test-job-456",
            source_image_s3=S3Location(bucket="bucket", key="source.jpg"),
            target_video_s3=S3Location(bucket="bucket", key="target.mp4"),
            output_s3=S3Location(bucket="bucket", key="output.mp4"),
            options=ProcessingOptions(many_faces=True, face_enhancer=False),
            callback_url="https://example.com/webhook"
        )
        
        assert request.options.many_faces is True
        assert request.options.face_enhancer is False
        assert request.callback_url == "https://example.com/webhook"
    
    def test_empty_job_id(self):
        """Test validation error for empty job_id"""
        with pytest.raises(ValidationError):
            SwapVideoRequest(
                job_id="",
                source_image_s3=S3Location(bucket="bucket", key="source.jpg"),
                target_video_s3=S3Location(bucket="bucket", key="target.mp4"),
                output_s3=S3Location(bucket="bucket", key="output.mp4")
            )


class TestSwapVideoResponse:
    """Tests for SwapVideoResponse schema"""
    
    def test_success_response(self):
        """Test successful response creation"""
        response = SwapVideoResponse(
            job_id="test-job-123",
            status=JobStatus.COMPLETED,
            result={
                "output_s3": {"bucket": "b", "key": "k", "region": "r"},
                "processing_time_seconds": 120.5,
                "frames_processed": 1800,
                "fps": 30.0,
                "duration_seconds": 60.0,
                "faces_detected": 1,
                "face_enhancer_applied": True
            }
        )
        
        assert response.job_id == "test-job-123"
        assert response.status == JobStatus.COMPLETED
        assert response.result is not None
        assert response.error is None
    
    def test_error_response(self):
        """Test error response creation"""
        response = SwapVideoResponse(
            job_id="test-job-456",
            status=JobStatus.FAILED,
            error={
                "code": "NO_FACE_IN_SOURCE",
                "message": "No face detected in source image"
            }
        )
        
        assert response.status == JobStatus.FAILED
        assert response.error["code"] == "NO_FACE_IN_SOURCE"
        assert response.result is None
