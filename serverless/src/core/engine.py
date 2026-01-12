"""
Face Swap Engine

Main processing engine that orchestrates face swap operations.
Supports multi-threaded frame processing for improved performance.
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import cv2
import numpy as np

from src.config import settings
from src.api.schemas import ProcessingOptions
from src.utils.logger import get_logger
from src.utils.gpu import clear_gpu_memory

logger = get_logger(__name__)


@dataclass
class ProcessingResultData:
    """Processing result data"""
    processing_time: float
    frames_processed: int
    fps: float
    duration: float
    faces_detected: int


class ProgressCallback:
    """Thread-safe progress tracking"""
    
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self._lock = threading.Lock()
    
    def increment(self, amount: int = 1) -> None:
        with self._lock:
            self.current += amount
    
    @property
    def percentage(self) -> float:
        return (self.current / self.total * 100) if self.total > 0 else 0


class FaceSwapEngine:
    """
    Video face swap processing engine.
    
    Manages model loading and orchestrates the face swap pipeline:
    1. Face detection and analysis (InsightFace buffalo_l)
    2. Face swapping (InSwapper)
    3. Optional face enhancement (GFPGAN)
    4. Video encoding (FFmpeg)
    
    Features:
    - Multi-threaded frame processing
    - GPU memory management
    - Progress tracking
    """
    
    def __init__(self):
        self.face_analyser = None
        self.face_swapper = None
        self.face_enhancer = None
        self._models_loaded = False
        self._load_lock = threading.Lock()
    
    def load_models(self) -> None:
        """
        Load all required models to GPU.
        
        Should be called once during container initialization.
        Thread-safe.
        """
        with self._load_lock:
            if self._models_loaded:
                logger.info("Models already loaded, skipping")
                return
            
            logger.info("Loading models...")
            start_time = time.time()
            
            # Import here to defer heavy imports
            from src.core.face_analyser import FaceAnalyser
            from src.core.face_swapper import FaceSwapper
            from src.core.face_enhancer import FaceEnhancer
            
            # Load face analyser (InsightFace)
            logger.info("Loading Face Analyser (InsightFace buffalo_l)...")
            self.face_analyser = FaceAnalyser(
                providers=settings.execution_providers
            )
            
            # Load face swapper (InSwapper)
            logger.info("Loading Face Swapper (InSwapper)...")
            self.face_swapper = FaceSwapper(
                model_path=settings.swapper_model_path,
                providers=settings.execution_providers
            )
            
            # Load face enhancer (GFPGAN)
            logger.info("Loading Face Enhancer (GFPGAN)...")
            self.face_enhancer = FaceEnhancer(
                model_path=settings.enhancer_model_path
            )
            
            self._models_loaded = True
            load_time = time.time() - start_time
            logger.info(f"All models loaded in {load_time:.2f}s")
    
    def process_video(
        self,
        source_image_path: str,
        target_video_path: str,
        output_video_path: str,
        options: ProcessingOptions,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ProcessingResultData:
        """
        Process video with face swap.
        
        Args:
            source_image_path: Path to source face image
            target_video_path: Path to target video
            output_video_path: Path for output video
            options: Processing options
            progress_callback: Optional callback(current, total)
            
        Returns:
            ProcessingResultData with results
        """
        if not self._models_loaded:
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        start_time = time.time()
        
        # Import video processor
        from src.core.video_processor import VideoProcessor
        video_processor = VideoProcessor()
        
        # Step 1: Read and analyze source face
        logger.info("Analyzing source face...")
        source_image = cv2.imread(source_image_path)
        if source_image is None:
            raise ValueError(f"Failed to read source image: {source_image_path}")
        
        source_face = self.face_analyser.get_one_face(source_image)
        if source_face is None:
            raise ValueError("No face detected in source image")
        
        logger.info("Source face analyzed successfully")
        
        # Step 2: Get video info
        video_info = video_processor.get_video_info(target_video_path)
        logger.info(
            f"Video: {video_info['width']}x{video_info['height']}, "
            f"{video_info['fps']:.2f}fps, {video_info['duration']:.2f}s, "
            f"~{video_info['frame_count']} frames"
        )
        
        # Step 3: Extract frames
        temp_dir = os.path.dirname(output_video_path)
        frames_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        logger.info("Extracting frames...")
        frame_paths = video_processor.extract_frames(target_video_path, frames_dir)
        total_frames = len(frame_paths)
        logger.info(f"Extracted {total_frames} frames")
        
        # Step 4: Process frames (multi-threaded or single-threaded)
        logger.info(f"Processing {total_frames} frames with {options.execution_threads} threads...")
        
        progress = ProgressCallback(total_frames)
        max_faces_detected = 0
        faces_lock = threading.Lock()
        
        def process_single_frame(frame_path: str) -> int:
            """Process a single frame and return faces detected"""
            nonlocal max_faces_detected
            
            frame = cv2.imread(frame_path)
            if frame is None:
                logger.warning(f"Failed to read frame: {frame_path}")
                progress.increment()
                return 0
            
            # Detect faces in target frame
            if options.many_faces:
                target_faces = self.face_analyser.get_many_faces(frame)
            else:
                target_face = self.face_analyser.get_one_face(frame)
                target_faces = [target_face] if target_face else []
            
            faces_count = len(target_faces)
            
            # Track max faces detected
            if faces_count > 0:
                with faces_lock:
                    max_faces_detected = max(max_faces_detected, faces_count)
            
            # Apply face swap for each detected face
            for target_face in target_faces:
                if target_face is not None:
                    frame = self.face_swapper.swap(
                        source_face,
                        target_face,
                        frame,
                        mouth_mask=options.mouth_mask
                    )
            
            # Apply face enhancement
            if options.face_enhancer and target_faces:
                frame = self.face_enhancer.enhance(frame)
            
            # Save processed frame
            cv2.imwrite(frame_path, frame)
            
            # Update progress
            progress.increment()
            
            return faces_count
        
        # Process frames
        if options.execution_threads > 1:
            # Multi-threaded processing
            with ThreadPoolExecutor(max_workers=options.execution_threads) as executor:
                futures = {
                    executor.submit(process_single_frame, path): path 
                    for path in frame_paths
                }
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        frame_path = futures[future]
                        logger.error(f"Error processing {frame_path}: {e}")
                    
                    # Progress logging
                    if progress.current % 100 == 0 or progress.current == total_frames:
                        logger.info(
                            f"Progress: {progress.current}/{total_frames} "
                            f"({progress.percentage:.1f}%)"
                        )
        else:
            # Single-threaded processing
            for i, frame_path in enumerate(frame_paths):
                try:
                    process_single_frame(frame_path)
                except Exception as e:
                    logger.error(f"Error processing frame {i}: {e}")
                
                # Progress logging
                if (i + 1) % 100 == 0 or (i + 1) == total_frames:
                    logger.info(
                        f"Progress: {i + 1}/{total_frames} "
                        f"({(i + 1) / total_frames * 100:.1f}%)"
                    )
        
        # Step 5: Create output video
        fps = video_info['fps'] if options.keep_fps else 30.0
        logger.info(f"Creating output video at {fps:.2f} fps with {options.video_encoder.value}...")
        
        video_processor.create_video(
            frames_dir=frames_dir,
            output_path=output_video_path,
            fps=fps,
            encoder=options.video_encoder.value,
            quality=options.video_quality
        )
        
        # Step 6: Restore audio if requested
        if options.keep_audio:
            logger.info("Restoring audio...")
            video_processor.restore_audio(
                source_video=target_video_path,
                target_video=output_video_path
            )
        
        # Step 7: Cleanup frames
        logger.info("Cleaning up frames...")
        video_processor.cleanup_frames(frames_dir)
        
        # Cleanup GPU memory
        clear_gpu_memory()
        
        processing_time = time.time() - start_time
        
        # Calculate stats
        fps_achieved = total_frames / processing_time if processing_time > 0 else 0
        logger.info(
            f"Processing complete in {processing_time:.2f}s "
            f"({fps_achieved:.1f} frames/sec)"
        )
        
        return ProcessingResultData(
            processing_time=processing_time,
            frames_processed=total_frames,
            fps=fps,
            duration=video_info['duration'],
            faces_detected=max_faces_detected
        )
    
    def get_status(self) -> dict:
        """
        Get engine status.
        
        Returns:
            Status dictionary
        """
        return {
            "models_loaded": self._models_loaded,
            "face_analyser": self.face_analyser is not None,
            "face_swapper": self.face_swapper is not None,
            "face_enhancer": self.face_enhancer is not None,
        }
