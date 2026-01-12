"""
Video Processor

Video processing utilities using FFmpeg.
Handles frame extraction, video creation, and audio restoration.
"""

import os
import glob
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FFmpegError(Exception):
    """FFmpeg operation error"""
    pass


class VideoProcessor:
    """
    Video processing using FFmpeg.
    
    Handles:
    - Video information extraction (fps, duration, resolution)
    - Frame extraction to PNG
    - Video creation from frames
    - Audio restoration from original video
    """
    
    def __init__(self):
        """Initialize video processor"""
        # Verify ffmpeg is available
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        logger.info("VideoProcessor initialized")
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _run_ffmpeg(
        self, 
        args: List[str], 
        check: bool = True,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """
        Run FFmpeg command.
        
        Args:
            args: FFmpeg arguments
            check: Raise exception on error
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess result
        """
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-y",  # Overwrite output without asking
        ] + args
        
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if check and result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise FFmpegError(f"FFmpeg error (code {result.returncode}): {error_msg}")
            
            return result
            
        except subprocess.TimeoutExpired:
            raise FFmpegError(f"FFmpeg timeout after {timeout}s")
    
    def _run_ffprobe(self, args: List[str]) -> str:
        """
        Run ffprobe command.
        
        Args:
            args: ffprobe arguments
            
        Returns:
            stdout output
        """
        cmd = ["ffprobe"] + args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise FFmpegError(f"ffprobe error: {result.stderr}")
        
        return result.stdout.strip()
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video info:
            - width: int
            - height: int
            - fps: float
            - duration: float (seconds)
            - frame_count: int (estimated)
            - size_bytes: int
            - size_mb: float
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        file_size = os.path.getsize(video_path)
        
        # Get video stream info
        try:
            output = self._run_ffprobe([
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,duration,nb_frames",
                "-of", "csv=p=0",
                video_path
            ])
            
            parts = output.split(',')
            
            # Parse width and height
            width = int(parts[0]) if len(parts) > 0 and parts[0] else 1920
            height = int(parts[1]) if len(parts) > 1 and parts[1] else 1080
            
            # Parse frame rate (format: "30/1" or "30000/1001")
            fps = 30.0
            if len(parts) > 2 and parts[2]:
                try:
                    fps_parts = parts[2].split('/')
                    if len(fps_parts) == 2 and fps_parts[1]:
                        fps = float(fps_parts[0]) / float(fps_parts[1])
                    else:
                        fps = float(fps_parts[0])
                except (ValueError, ZeroDivisionError):
                    fps = 30.0
            
            # Parse duration
            duration = 0.0
            if len(parts) > 3 and parts[3]:
                try:
                    duration = float(parts[3])
                except ValueError:
                    pass
            
            # If duration not in stream, try container level
            if duration == 0.0:
                try:
                    duration_output = self._run_ffprobe([
                        "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "csv=p=0",
                        video_path
                    ])
                    duration = float(duration_output)
                except (ValueError, FFmpegError):
                    pass
            
            # Parse or estimate frame count
            frame_count = 0
            if len(parts) > 4 and parts[4]:
                try:
                    frame_count = int(parts[4])
                except ValueError:
                    pass
            
            if frame_count == 0 and duration > 0 and fps > 0:
                frame_count = int(duration * fps)
            
            return {
                "width": width,
                "height": height,
                "fps": fps,
                "duration": duration,
                "frame_count": frame_count,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.warning(f"Error getting video info: {e}")
            return {
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "duration": 0.0,
                "frame_count": 0,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024 * 1024), 2)
            }
    
    def extract_frames(
        self, 
        video_path: str, 
        output_dir: str,
        frame_pattern: str = "%06d.png"
    ) -> List[str]:
        """
        Extract frames from video as PNG images.
        
        Args:
            video_path: Path to video file
            output_dir: Directory for output frames
            frame_pattern: Frame filename pattern (default: 6-digit padded)
            
        Returns:
            List of frame file paths (sorted)
        """
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        output_pattern = os.path.join(output_dir, frame_pattern)
        
        logger.info(f"Extracting frames from {video_path}")
        
        self._run_ffmpeg([
            "-i", video_path,
            "-pix_fmt", "rgb24",
            "-vsync", "0",  # Preserve frame timing
            output_pattern
        ])
        
        # Get list of extracted frames (sorted by name)
        frame_paths = sorted(glob.glob(os.path.join(output_dir, "*.png")))
        
        logger.info(f"Extracted {len(frame_paths)} frames to {output_dir}")
        return frame_paths
    
    def create_video(
        self,
        frames_dir: str,
        output_path: str,
        fps: float = 30.0,
        encoder: str = "libx264",
        quality: int = 18,
        frame_pattern: str = "%06d.png",
        pixel_format: str = "yuv420p"
    ) -> None:
        """
        Create video from frames.
        
        Args:
            frames_dir: Directory containing frame images
            output_path: Output video path
            fps: Frame rate
            encoder: Video encoder (libx264, libx265, libvpx-vp9)
            quality: CRF quality value (0-51, lower is better)
            frame_pattern: Frame filename pattern
            pixel_format: Output pixel format
        """
        input_pattern = os.path.join(frames_dir, frame_pattern)
        
        # Ensure output directory exists
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating video at {fps} fps with {encoder}")
        
        # Build encoder-specific arguments
        encoder_args = []
        if encoder == "libx264":
            encoder_args = [
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", str(quality),
            ]
        elif encoder == "libx265":
            encoder_args = [
                "-c:v", "libx265",
                "-preset", "medium",
                "-crf", str(quality),
            ]
        elif encoder == "libvpx-vp9":
            encoder_args = [
                "-c:v", "libvpx-vp9",
                "-b:v", "0",
                "-crf", str(quality),
            ]
        else:
            encoder_args = ["-c:v", encoder, "-crf", str(quality)]
        
        self._run_ffmpeg([
            "-framerate", str(fps),
            "-i", input_pattern,
            *encoder_args,
            "-pix_fmt", pixel_format,
            "-movflags", "+faststart",  # Enable streaming
            output_path
        ])
        
        logger.info(f"Video created: {output_path}")
    
    def restore_audio(
        self, 
        source_video: str, 
        target_video: str
    ) -> bool:
        """
        Restore audio from source video to target video.
        
        Creates a new video with video from target and audio from source.
        
        Args:
            source_video: Video with original audio
            target_video: Video to add audio to (will be replaced)
            
        Returns:
            True if audio restored, False otherwise
        """
        # Check if source has audio
        try:
            audio_check = self._run_ffprobe([
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                source_video
            ])
            
            if not audio_check or "audio" not in audio_check:
                logger.info("Source video has no audio track")
                return False
                
        except FFmpegError:
            logger.info("Could not check for audio in source video")
            return False
        
        # Create temp output
        temp_output = target_video + ".temp.mp4"
        
        try:
            self._run_ffmpeg([
                "-i", target_video,
                "-i", source_video,
                "-c:v", "copy",  # Copy video stream without re-encoding
                "-map", "0:v:0",  # Video from target
                "-map", "1:a:0?",  # Audio from source (optional)
                "-shortest",  # Match shortest stream
                temp_output
            ])
            
            # Replace original with temp
            os.replace(temp_output, target_video)
            logger.info("Audio restored successfully")
            return True
            
        except FFmpegError as e:
            logger.warning(f"Audio restoration failed: {e}")
            # Clean up temp file if exists
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
            
        except Exception as e:
            logger.warning(f"Audio restoration error: {e}")
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
    
    def cleanup_frames(self, frames_dir: str) -> None:
        """
        Remove extracted frames directory.
        
        Args:
            frames_dir: Directory to remove
        """
        if os.path.exists(frames_dir):
            try:
                shutil.rmtree(frames_dir)
                logger.debug(f"Cleaned up frames: {frames_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup frames: {e}")
