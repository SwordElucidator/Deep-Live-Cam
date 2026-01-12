"""
S3 Service

AWS S3 file operations with retry logic.
"""

import os
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.api.schemas import S3Location
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class S3Error(Exception):
    """S3 operation error"""
    
    def __init__(self, code: str, message: str, original_error: Optional[Exception] = None):
        self.code = code
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class S3Service:
    """
    AWS S3 file operations service.
    
    Handles downloading and uploading files to S3 with retry logic.
    """
    
    def __init__(self):
        """Initialize S3 client"""
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region
        )
        logger.info(f"S3 service initialized (region: {settings.aws_default_region})")
    
    def download(
        self,
        location: S3Location,
        local_path: str,
        max_retries: int = 3
    ) -> str:
        """
        Download file from S3.
        
        Args:
            location: S3 file location
            local_path: Local destination path
            max_retries: Maximum retry attempts
            
        Returns:
            Local file path
            
        Raises:
            S3Error: If download fails after retries
        """
        logger.info(f"Downloading {location.to_uri()} to {local_path}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Use region-specific client if different from default
                client = self._get_client_for_region(location.region)
                
                # Download file
                client.download_file(
                    location.bucket,
                    location.key,
                    local_path
                )
                
                # Verify file exists and has content
                if not os.path.exists(local_path):
                    raise S3Error("S3_DOWNLOAD_ERROR", "Downloaded file not found")
                
                file_size = os.path.getsize(local_path)
                logger.info(f"Downloaded {file_size / 1024 / 1024:.2f} MB")
                
                return local_path
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                last_error = S3Error(
                    "S3_DOWNLOAD_ERROR",
                    f"S3 download failed: {error_code} - {str(e)}",
                    e
                )
                logger.warning(f"Download attempt {attempt + 1}/{max_retries} failed: {error_code}")
                
            except Exception as e:
                last_error = S3Error(
                    "S3_DOWNLOAD_ERROR",
                    f"Download failed: {str(e)}",
                    e
                )
                logger.warning(f"Download attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            # Exponential backoff
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        
        raise last_error
    
    def upload(
        self,
        local_path: str,
        location: S3Location,
        max_retries: int = 3
    ) -> str:
        """
        Upload file to S3.
        
        Args:
            local_path: Local file path
            location: S3 destination location
            max_retries: Maximum retry attempts
            
        Returns:
            S3 URI
            
        Raises:
            S3Error: If upload fails after retries
        """
        logger.info(f"Uploading {local_path} to {location.to_uri()}")
        
        # Verify local file exists
        if not os.path.exists(local_path):
            raise S3Error("S3_UPLOAD_ERROR", f"Local file not found: {local_path}")
        
        file_size = os.path.getsize(local_path)
        content_type = self._get_content_type(local_path)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Use region-specific client if different from default
                client = self._get_client_for_region(location.region)
                
                # Upload file
                client.upload_file(
                    local_path,
                    location.bucket,
                    location.key,
                    ExtraArgs={
                        'ContentType': content_type
                    }
                )
                
                s3_uri = location.to_uri()
                logger.info(f"Uploaded {file_size / 1024 / 1024:.2f} MB to {s3_uri}")
                
                return s3_uri
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                last_error = S3Error(
                    "S3_UPLOAD_ERROR",
                    f"S3 upload failed: {error_code} - {str(e)}",
                    e
                )
                logger.warning(f"Upload attempt {attempt + 1}/{max_retries} failed: {error_code}")
                
            except Exception as e:
                last_error = S3Error(
                    "S3_UPLOAD_ERROR",
                    f"Upload failed: {str(e)}",
                    e
                )
                logger.warning(f"Upload attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            # Exponential backoff
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                logger.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        
        raise last_error
    
    def check_exists(self, location: S3Location) -> bool:
        """
        Check if S3 object exists.
        
        Args:
            location: S3 location to check
            
        Returns:
            True if object exists
        """
        try:
            client = self._get_client_for_region(location.region)
            client.head_object(Bucket=location.bucket, Key=location.key)
            return True
        except ClientError:
            return False
    
    def _get_client_for_region(self, region: str) -> boto3.client:
        """Get S3 client for specific region"""
        if region == settings.aws_default_region:
            return self.client
        
        return boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=region
        )
    
    @staticmethod
    def _get_content_type(path: str) -> str:
        """Get content type from file extension"""
        ext = os.path.splitext(path)[1].lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
        }
        return content_types.get(ext, 'application/octet-stream')
