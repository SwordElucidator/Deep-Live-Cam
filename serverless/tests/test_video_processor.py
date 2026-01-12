"""
Tests for video processor
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.core.video_processor import VideoProcessor, FFmpegError


class TestVideoProcessor:
    """Tests for VideoProcessor class"""
    
    @pytest.fixture
    def video_processor(self):
        """Create video processor with mocked ffmpeg check"""
        with patch.object(VideoProcessor, '_check_ffmpeg', return_value=True):
            return VideoProcessor()
    
    def test_init_no_ffmpeg(self):
        """Test initialization fails without ffmpeg"""
        with patch.object(VideoProcessor, '_check_ffmpeg', return_value=False):
            with pytest.raises(RuntimeError, match="FFmpeg not found"):
                VideoProcessor()
    
    def test_get_video_info_file_not_found(self, video_processor):
        """Test get_video_info with non-existent file"""
        with pytest.raises(FileNotFoundError):
            video_processor.get_video_info("/nonexistent/video.mp4")
    
    @patch('subprocess.run')
    def test_get_video_info_success(self, mock_run, video_processor, tmp_path):
        """Test successful video info extraction"""
        # Create dummy video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video content" * 1000)
        
        # Mock ffprobe output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1920,1080,30/1,60.5,1815",
            stderr=""
        )
        
        info = video_processor.get_video_info(str(video_file))
        
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["fps"] == 30.0
        assert info["duration"] == 60.5
        assert info["frame_count"] == 1815
        assert info["size_bytes"] > 0
    
    @patch('subprocess.run')
    def test_extract_frames(self, mock_run, video_processor, tmp_path):
        """Test frame extraction"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")
        output_dir = tmp_path / "frames"
        
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Create some fake frame files
        output_dir.mkdir()
        for i in range(5):
            (output_dir / f"{i:06d}.png").write_bytes(b"fake frame")
        
        frames = video_processor.extract_frames(str(video_file), str(output_dir))
        
        assert len(frames) == 5
        assert all(f.endswith(".png") for f in frames)
    
    @patch('subprocess.run')
    def test_create_video(self, mock_run, video_processor, tmp_path):
        """Test video creation from frames"""
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        output_path = tmp_path / "output.mp4"
        
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        video_processor.create_video(
            str(frames_dir),
            str(output_path),
            fps=30.0,
            encoder="libx264",
            quality=18
        )
        
        # Verify ffmpeg was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert "-c:v" in call_args
        assert "libx264" in call_args
    
    @patch('subprocess.run')
    def test_restore_audio_success(self, mock_run, video_processor, tmp_path):
        """Test audio restoration"""
        source_video = tmp_path / "source.mp4"
        target_video = tmp_path / "target.mp4"
        source_video.write_bytes(b"source video")
        target_video.write_bytes(b"target video")
        
        # Mock ffprobe to indicate audio exists
        mock_run.return_value = MagicMock(returncode=0, stdout="audio", stderr="")
        
        result = video_processor.restore_audio(str(source_video), str(target_video))
        
        # Should attempt audio restoration
        assert mock_run.called
    
    @patch('subprocess.run')
    def test_restore_audio_no_audio(self, mock_run, video_processor, tmp_path):
        """Test audio restoration with no audio track"""
        source_video = tmp_path / "source.mp4"
        target_video = tmp_path / "target.mp4"
        source_video.write_bytes(b"source video")
        target_video.write_bytes(b"target video")
        
        # Mock ffprobe to indicate no audio
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        result = video_processor.restore_audio(str(source_video), str(target_video))
        
        assert result is False
    
    def test_cleanup_frames(self, video_processor, tmp_path):
        """Test frames cleanup"""
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame.png").write_bytes(b"frame")
        
        assert frames_dir.exists()
        
        video_processor.cleanup_frames(str(frames_dir))
        
        assert not frames_dir.exists()
    
    def test_cleanup_frames_nonexistent(self, video_processor, tmp_path):
        """Test cleanup of non-existent directory"""
        # Should not raise
        video_processor.cleanup_frames(str(tmp_path / "nonexistent"))
