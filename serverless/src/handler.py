"""
RunPod Serverless Handler

Entry point for the Deep-Live-Cam Video Face Swap API.
Handles job dispatch, error handling, and lifecycle management.
"""

import os
import sys
import time
import traceback
from typing import Dict, Any, Optional

import runpod

from src.config import settings
from src.api.schemas import (
    SwapVideoRequest,
    SwapVideoResponse,
    ProcessingResult,
    JobStatus,
    ProcessingOptions,
    HealthResponse,
)
from src.api.validators import validate_request, ValidationError, validate_video_constraints
from src.core.engine import FaceSwapEngine
from src.services.s3_service import S3Service, S3Error
from src.services.callback_service import CallbackService, CallbackError
from src.services.temp_storage import TempStorage
from src.utils.logger import get_logger, JobLogContext, setup_logging
from src.utils.gpu import get_gpu_info, check_gpu_available

# Initialize logging
setup_logging(use_json=True)
logger = get_logger(__name__)

# Global instances (initialized once per container)
engine: Optional[FaceSwapEngine] = None
s3_service: Optional[S3Service] = None
_initialized = False


class ProcessingError(Exception):
    """Processing error with code"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def initialize() -> None:
    """
    Initialize global services and load models.
    Called once when container starts.
    """
    global engine, s3_service, _initialized
    
    if _initialized:
        logger.info("Already initialized, skipping")
        return
    
    logger.info("=" * 60)
    logger.info("Deep-Live-Cam Video Face Swap API Starting...")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 60)
    
    # Check GPU availability
    gpu_info = get_gpu_info()
    if gpu_info.get("available"):
        logger.info(f"GPU: {gpu_info.get('name')} ({gpu_info.get('memory_total_gb')}GB)")
        logger.info(f"CUDA: {gpu_info.get('cuda_version')}")
    else:
        logger.warning("No GPU available - processing will be slow")
    
    # Validate AWS credentials
    if settings.validate_aws_credentials():
        logger.info("AWS credentials configured")
    else:
        logger.warning("AWS credentials not configured - S3 operations will fail")
    
    # Initialize S3 service
    logger.info("Initializing S3 service...")
    try:
        s3_service = S3Service()
    except Exception as e:
        logger.error(f"Failed to initialize S3 service: {e}")
        raise
    
    # Initialize and load face swap engine
    logger.info("Initializing Face Swap Engine...")
    try:
        engine = FaceSwapEngine()
        engine.load_models()
    except Exception as e:
        logger.error(f"Failed to initialize Face Swap Engine: {e}")
        raise
    
    _initialized = True
    logger.info("=" * 60)
    logger.info("Initialization complete - Ready to accept jobs")
    logger.info("=" * 60)


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler function.
    
    Processes face swap jobs by:
    1. Validating input
    2. Downloading files from S3
    3. Processing video
    4. Uploading result to S3
    5. Sending webhook callback
    
    Args:
        job: RunPod job object containing 'input' field
        
    Returns:
        Response dictionary with job result
    """
    job_input = job.get("input", {})
    job_id = job_input.get("job_id", job.get("id", f"unknown-{int(time.time())}"))
    
    # Create temp storage for this job
    temp_storage = TempStorage(job_id)
    
    with JobLogContext(job_id):
        logger.info("=" * 40)
        logger.info(f"Job started: {job_id}")
        logger.info("=" * 40)
        
        start_time = time.time()
        
        try:
            # Ensure initialized
            if not _initialized:
                logger.info("Service not initialized, attempting initialization...")
                try:
                    initialize()
                except Exception as init_error:
                    logger.error(f"Initialization failed in handler: {init_error}")
                    raise ProcessingError("INIT_FAILED", f"Service initialization failed: {str(init_error)}")
            
            # Step 1: Validate request
            logger.info("Step 1/6: Validating request...")
            try:
                request = validate_request(job_input)
            except ValidationError as e:
                raise ProcessingError(e.code, e.message)
            
            # Step 2: Download source image from S3
            logger.info(f"Step 2/6: Downloading source image...")
            logger.info(f"  Source: {request.source_image_s3.to_uri()}")
            try:
                source_path = s3_service.download(
                    request.source_image_s3,
                    temp_storage.get_path("source.jpg")
                )
            except S3Error as e:
                raise ProcessingError("S3_DOWNLOAD_ERROR", f"Failed to download source image: {e.message}")
            
            # Step 3: Download target video from S3
            logger.info(f"Step 3/6: Downloading target video...")
            logger.info(f"  Target: {request.target_video_s3.to_uri()}")
            try:
                target_path = s3_service.download(
                    request.target_video_s3,
                    temp_storage.get_path("target.mp4")
                )
            except S3Error as e:
                raise ProcessingError("S3_DOWNLOAD_ERROR", f"Failed to download target video: {e.message}")
            
            # Validate video constraints
            from src.core.video_processor import VideoProcessor
            video_processor = VideoProcessor()
            video_info = video_processor.get_video_info(target_path)
            
            try:
                validate_video_constraints(video_info)
            except ValidationError as e:
                raise ProcessingError(e.code, e.message)
            
            logger.info(f"  Video: {video_info['width']}x{video_info['height']}, "
                       f"{video_info['fps']:.1f}fps, {video_info['duration']:.1f}s")
            
            # Step 4: Process video
            logger.info("Step 4/6: Processing video...")
            output_path = temp_storage.get_path("output.mp4")
            
            try:
                result = engine.process_video(
                    source_image_path=source_path,
                    target_video_path=target_path,
                    output_video_path=output_path,
                    options=request.options
                )
            except ValueError as e:
                # Face detection errors
                error_msg = str(e)
                if "source" in error_msg.lower() and "face" in error_msg.lower():
                    raise ProcessingError("NO_FACE_IN_SOURCE", error_msg)
                elif "face" in error_msg.lower():
                    raise ProcessingError("NO_FACE_IN_VIDEO", error_msg)
                else:
                    raise ProcessingError("PROCESSING_ERROR", error_msg)
            except Exception as e:
                raise ProcessingError("PROCESSING_ERROR", f"Video processing failed: {str(e)}")
            
            # Step 5: Upload result to S3
            logger.info("Step 5/6: Uploading result...")
            logger.info(f"  Output: {request.output_s3.to_uri()}")
            try:
                s3_service.upload(output_path, request.output_s3)
            except S3Error as e:
                raise ProcessingError("S3_UPLOAD_ERROR", f"Failed to upload result: {e.message}")
            
            # Step 6: Build response
            total_time = time.time() - start_time
            logger.info("Step 6/6: Building response...")
            
            response = SwapVideoResponse(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                result=ProcessingResult(
                    output_s3=request.output_s3.model_dump(),
                    processing_time_seconds=round(result.processing_time, 2),
                    frames_processed=result.frames_processed,
                    fps=round(result.fps, 2),
                    duration_seconds=round(result.duration, 2),
                    faces_detected=result.faces_detected,
                    face_enhancer_applied=request.options.face_enhancer
                ),
                message=f"Completed in {total_time:.1f}s"
            )
            
            logger.info("=" * 40)
            logger.info(f"Job completed successfully")
            logger.info(f"  Processing time: {result.processing_time:.1f}s")
            logger.info(f"  Frames processed: {result.frames_processed}")
            logger.info(f"  Total time: {total_time:.1f}s")
            logger.info("=" * 40)
            
            # Send success callback if configured
            if request.callback_url:
                logger.info(f"Sending callback to {request.callback_url}")
                try:
                    CallbackService.send(request.callback_url, response.model_dump())
                except CallbackError as e:
                    logger.warning(f"Callback failed (non-fatal): {e}")
            
            return response.model_dump()
            
        except ProcessingError as e:
            logger.error(f"Processing error [{e.code}]: {e.message}")
            return _build_error_response(job_id, job_input, e.code, e.message, e.details)
            
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            return _build_error_response(
                job_id, 
                job_input, 
                "INTERNAL_ERROR",
                str(e),
                {"traceback": traceback.format_exc()}
            )
            
        finally:
            # Always cleanup temp files
            logger.info("Cleaning up temporary files...")
            temp_storage.cleanup()


def _build_error_response(
    job_id: str,
    job_input: Dict[str, Any],
    error_code: str,
    error_message: str,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Build error response and send callback.
    
    Args:
        job_id: Job identifier
        job_input: Original job input
        error_code: Error code
        error_message: Error message
        details: Additional error details
        
    Returns:
        Error response dictionary
    """
    # Build response dict directly to ensure all fields are included
    response = {
        "job_id": job_id,
        "status": "failed",
        "result": None,
        "error": {
            "code": error_code,
            "message": error_message,
            "details": details or {}
        },
        "message": f"Error: {error_code} - {error_message}"
    }
    
    logger.error(f"Building error response: {error_code} - {error_message}")
    
    # Send failure callback if configured
    callback_url = job_input.get("callback_url")
    if callback_url:
        try:
            CallbackService.send(callback_url, response)
        except Exception as callback_error:
            logger.error(f"Failed to send error callback: {callback_error}")
    
    return response


def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status dictionary
    """
    gpu_info = get_gpu_info()
    
    models_status = {
        "face_analyser": "loaded" if engine and engine.face_analyser else "not_loaded",
        "face_swapper": "loaded" if engine and engine.face_swapper else "not_loaded",
        "face_enhancer": "loaded" if engine and engine.face_enhancer else "not_loaded",
    }
    
    return HealthResponse(
        status="healthy" if _initialized and engine and engine._models_loaded else "initializing",
        gpu=gpu_info,
        models=models_status,
        version="1.0.0"
    ).model_dump()


# Initialize on module load (for container pre-warming)
try:
    initialize()
except Exception as e:
    logger.error(f"Initialization failed: {e}")
    logger.error("Will retry on first request")


# Start RunPod serverless handler
if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler...")
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False,
    })
