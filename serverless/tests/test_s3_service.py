"""
Tests for S3 service (using moto mock)
"""

import os
import pytest
import boto3
from moto import mock_aws

from src.api.schemas import S3Location
from src.services.s3_service import S3Service, S3Error


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_bucket(aws_credentials):
    """Create mock S3 bucket"""
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        yield conn


@pytest.fixture
def s3_service(aws_credentials):
    """Create S3 service instance"""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        yield S3Service()


class TestS3Service:
    """Tests for S3Service class"""
    
    @mock_aws
    def test_download_success(self, aws_credentials, tmp_path):
        """Test successful file download"""
        # Setup
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        conn.put_object(
            Bucket="test-bucket",
            Key="test/file.txt",
            Body=b"test content"
        )
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="test/file.txt")
        local_path = str(tmp_path / "downloaded.txt")
        
        # Test
        result = service.download(location, local_path)
        
        # Assert
        assert result == local_path
        assert os.path.exists(local_path)
        with open(local_path, "rb") as f:
            assert f.read() == b"test content"
    
    @mock_aws
    def test_download_not_found(self, aws_credentials, tmp_path):
        """Test download of non-existent file"""
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="nonexistent.txt")
        local_path = str(tmp_path / "downloaded.txt")
        
        with pytest.raises(S3Error) as exc_info:
            service.download(location, local_path, max_retries=1)
        
        assert "S3_DOWNLOAD_ERROR" in exc_info.value.code
    
    @mock_aws
    def test_upload_success(self, aws_credentials, tmp_path):
        """Test successful file upload"""
        # Setup
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        
        # Create local file
        local_file = tmp_path / "upload.txt"
        local_file.write_text("upload content")
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="uploads/file.txt")
        
        # Test
        result = service.upload(str(local_file), location)
        
        # Assert
        assert result == "s3://test-bucket/uploads/file.txt"
        
        # Verify file exists in S3
        response = conn.get_object(Bucket="test-bucket", Key="uploads/file.txt")
        assert response["Body"].read() == b"upload content"
    
    @mock_aws
    def test_upload_file_not_found(self, aws_credentials):
        """Test upload with non-existent local file"""
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="uploads/file.txt")
        
        with pytest.raises(S3Error) as exc_info:
            service.upload("/nonexistent/file.txt", location)
        
        assert "S3_UPLOAD_ERROR" in exc_info.value.code
    
    @mock_aws
    def test_check_exists_true(self, aws_credentials):
        """Test check_exists for existing file"""
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        conn.put_object(Bucket="test-bucket", Key="exists.txt", Body=b"content")
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="exists.txt")
        
        assert service.check_exists(location) is True
    
    @mock_aws
    def test_check_exists_false(self, aws_credentials):
        """Test check_exists for non-existent file"""
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        
        service = S3Service()
        location = S3Location(bucket="test-bucket", key="notexists.txt")
        
        assert service.check_exists(location) is False
    
    @mock_aws
    def test_content_type_detection(self, aws_credentials, tmp_path):
        """Test content type detection for different file types"""
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test-bucket")
        
        service = S3Service()
        
        # Test video content type
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake video content")
        
        location = S3Location(bucket="test-bucket", key="video.mp4")
        service.upload(str(video_file), location)
        
        response = conn.head_object(Bucket="test-bucket", Key="video.mp4")
        assert response["ContentType"] == "video/mp4"
