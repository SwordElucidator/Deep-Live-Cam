# Deep-Live-Cam Video Face Swap API - Architecture

> 技术架构文档  
> Version: 1.0.0  
> Last Updated: 2026-01-12

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Internal Services                                  │
│  (Your Backend / Workflow System / Batch Processing System)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP POST /swap/video
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RunPod Serverless Platform                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     Deep-Live-Cam API Container                        │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    RunPod Handler Layer                         │   │  │
│  │  │  • Job Dispatch                                                 │   │  │
│  │  │  • Request Validation                                           │   │  │
│  │  │  • Error Handling                                               │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  │                              │                                         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    Processing Pipeline                          │   │  │
│  │  │                                                                 │   │  │
│  │  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │   │  │
│  │  │  │ S3 Download  │──▶│ Video        │──▶│ S3 Upload        │    │   │  │
│  │  │  │ Service      │   │ Processor    │   │ Service          │    │   │  │
│  │  │  └──────────────┘   └──────────────┘   └──────────────────┘    │   │  │
│  │  │         │                  │                    │               │   │  │
│  │  │         ▼                  ▼                    ▼               │   │  │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │   │  │
│  │  │  │                    Local Temp Storage                     │  │   │  │
│  │  │  │  /tmp/jobs/{job_id}/                                      │  │   │  │
│  │  │  │    ├── source.jpg                                         │  │   │  │
│  │  │  │    ├── target.mp4                                         │  │   │  │
│  │  │  │    ├── frames/  (extracted frames)                        │  │   │  │
│  │  │  │    └── output.mp4                                         │  │   │  │
│  │  │  └──────────────────────────────────────────────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  │                              │                                         │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    Core Engine Layer (GPU)                      │   │  │
│  │  │                                                                 │   │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │  │
│  │  │  │ Face         │  │ Face         │  │ Face                 │  │   │  │
│  │  │  │ Analyser     │  │ Swapper      │  │ Enhancer             │  │   │  │
│  │  │  │ (InsightFace)│  │ (InSwapper)  │  │ (GFPGAN)             │  │   │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │  │
│  │  │         │                  │                    │               │   │  │
│  │  │         └──────────────────┴────────────────────┘               │   │  │
│  │  │                            │                                    │   │  │
│  │  │  ┌─────────────────────────▼────────────────────────────────┐  │   │  │
│  │  │  │              NVIDIA GPU (A10G/A100)                       │  │   │  │
│  │  │  │  • CUDA 12.8                                              │  │   │  │
│  │  │  │  • ONNX Runtime GPU                                       │  │   │  │
│  │  │  │  • PyTorch CUDA                                           │  │   │  │
│  │  │  └──────────────────────────────────────────────────────────┘  │   │  │
│  │  └────────────────────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                │                                          │
                │ Download                                 │ Upload
                ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS S3                                          │
│  ┌─────────────────────────┐         ┌─────────────────────────────────┐    │
│  │        Input Bucket      │         │         Output Bucket            │    │
│  │  • source_images/        │         │  • results/                      │    │
│  │  • target_videos/        │         │    └── {job_id}/result.mp4       │    │
│  └─────────────────────────┘         └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Webhook Callback
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Callback Endpoint                                    │
│                   (Your Internal Webhook Receiver)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 目录结构

```
Deep-Live-Cam/
├── serverless/                      # Serverless 部署相关
│   ├── SPEC.md                      # 规范文档
│   ├── ARCHITECTURE.md              # 架构文档 (本文件)
│   ├── TASKS.md                     # 任务拆解
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py                # 配置管理
│   │   ├── handler.py               # RunPod Handler 入口
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   │   └── validators.py        # 输入验证器
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py            # 统一处理引擎
│   │   │   ├── face_analyser.py     # 人脸分析封装
│   │   │   ├── face_swapper.py      # 换脸逻辑封装
│   │   │   ├── face_enhancer.py     # 增强逻辑封装
│   │   │   └── video_processor.py   # 视频处理流程
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── s3_service.py        # AWS S3 操作
│   │   │   ├── callback_service.py  # Webhook 回调
│   │   │   └── temp_storage.py      # 临时文件管理
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── ffmpeg.py            # FFmpeg 封装
│   │       ├── gpu.py               # GPU 状态检测
│   │       └── logger.py            # 日志配置
│   │
│   ├── Dockerfile                   # Docker 构建文件
│   ├── requirements.txt             # Python 依赖
│   ├── download_models.py           # 模型下载脚本
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_handler.py
│       ├── test_video_processor.py
│       └── test_s3_service.py
│
├── models/                          # 模型文件 (已存在)
│   ├── inswapper_128_fp16.onnx
│   ├── inswapper_128.onnx
│   └── GFPGANv1.4.pth
│
└── modules/                         # 原有核心模块 (复用)
    ├── face_analyser.py
    ├── processors/frame/face_swapper.py
    ├── processors/frame/face_enhancer.py
    └── ...
```

---

## 3. 核心组件设计

### 3.1 RunPod Handler (`src/handler.py`)

RunPod Serverless 的入口点，负责接收任务并分发处理。

```python
"""
RunPod Handler - 视频换脸服务入口
"""
import runpod
from src.config import settings
from src.core.engine import FaceSwapEngine
from src.services.s3_service import S3Service
from src.services.callback_service import CallbackService
from src.services.temp_storage import TempStorage
from src.api.schemas import SwapVideoRequest, SwapVideoResponse
from src.api.validators import validate_request
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 全局引擎实例 (模型预加载)
engine: FaceSwapEngine = None
s3_service: S3Service = None

def init():
    """容器启动时初始化"""
    global engine, s3_service
    logger.info("Initializing Face Swap Engine...")
    engine = FaceSwapEngine()
    engine.load_models()
    s3_service = S3Service()
    logger.info("Initialization complete")

def handler(job: dict) -> dict:
    """
    RunPod Handler 主函数
    
    Args:
        job: RunPod 任务对象，包含 input 字段
        
    Returns:
        处理结果字典
    """
    job_input = job.get("input", {})
    job_id = job_input.get("job_id", job.get("id"))
    
    logger.info(f"Processing job: {job_id}")
    temp_storage = TempStorage(job_id)
    
    try:
        # 1. 验证请求
        request = validate_request(job_input)
        
        # 2. 下载输入文件
        source_path = s3_service.download(
            request.source_image_s3, 
            temp_storage.get_path("source.jpg")
        )
        target_path = s3_service.download(
            request.target_video_s3,
            temp_storage.get_path("target.mp4")
        )
        
        # 3. 执行换脸处理
        output_path = temp_storage.get_path("output.mp4")
        result = engine.process_video(
            source_image_path=source_path,
            target_video_path=target_path,
            output_video_path=output_path,
            options=request.options
        )
        
        # 4. 上传结果
        s3_service.upload(output_path, request.output_s3)
        
        # 5. 构建响应
        response = SwapVideoResponse(
            job_id=job_id,
            status="completed",
            result={
                "output_s3": request.output_s3.dict(),
                "processing_time_seconds": result.processing_time,
                "frames_processed": result.frames_processed,
                "fps": result.fps,
                "duration_seconds": result.duration,
                "faces_detected": result.faces_detected,
                "face_enhancer_applied": request.options.face_enhancer
            }
        )
        
        # 6. 发送回调
        if request.callback_url:
            CallbackService.send(request.callback_url, response.dict())
        
        return response.dict()
        
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        error_response = {
            "job_id": job_id,
            "status": "failed",
            "error": {
                "code": type(e).__name__,
                "message": str(e)
            }
        }
        
        # 发送失败回调
        if job_input.get("callback_url"):
            CallbackService.send(job_input["callback_url"], error_response)
        
        return error_response
        
    finally:
        # 清理临时文件
        temp_storage.cleanup()

# 启动时初始化
init()

# RunPod 入口
runpod.serverless.start({"handler": handler})
```

### 3.2 处理引擎 (`src/core/engine.py`)

统一的换脸处理引擎，封装所有核心模块。

```python
"""
Face Swap Engine - 统一处理引擎
"""
import os
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np
import cv2

from src.config import settings
from src.core.face_analyser import FaceAnalyser
from src.core.face_swapper import FaceSwapper
from src.core.face_enhancer import FaceEnhancer
from src.core.video_processor import VideoProcessor
from src.api.schemas import ProcessingOptions
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ProcessingResult:
    """处理结果"""
    processing_time: float
    frames_processed: int
    fps: float
    duration: float
    faces_detected: int

class FaceSwapEngine:
    """
    视频换脸处理引擎
    
    负责:
    - 模型加载和管理
    - 视频处理流程编排
    - 帧处理逻辑
    """
    
    def __init__(self):
        self.face_analyser: Optional[FaceAnalyser] = None
        self.face_swapper: Optional[FaceSwapper] = None
        self.face_enhancer: Optional[FaceEnhancer] = None
        self.video_processor: Optional[VideoProcessor] = None
        self._models_loaded = False
        
    def load_models(self):
        """预加载所有模型到 GPU"""
        if self._models_loaded:
            logger.info("Models already loaded")
            return
            
        logger.info("Loading Face Analyser...")
        self.face_analyser = FaceAnalyser(
            providers=settings.execution_providers
        )
        
        logger.info("Loading Face Swapper...")
        self.face_swapper = FaceSwapper(
            model_path=settings.swapper_model_path,
            providers=settings.execution_providers
        )
        
        logger.info("Loading Face Enhancer...")
        self.face_enhancer = FaceEnhancer(
            model_path=settings.enhancer_model_path
        )
        
        self.video_processor = VideoProcessor()
        self._models_loaded = True
        logger.info("All models loaded successfully")
        
    def process_video(
        self,
        source_image_path: str,
        target_video_path: str,
        output_video_path: str,
        options: ProcessingOptions
    ) -> ProcessingResult:
        """
        处理视频换脸
        
        Args:
            source_image_path: 源人脸图片路径
            target_video_path: 目标视频路径
            output_video_path: 输出视频路径
            options: 处理选项
            
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        
        # 1. 分析源人脸
        source_image = cv2.imread(source_image_path)
        source_face = self.face_analyser.get_one_face(source_image)
        if source_face is None:
            raise ValueError("No face detected in source image")
        
        # 2. 获取视频信息
        video_info = self.video_processor.get_video_info(target_video_path)
        logger.info(f"Video info: {video_info}")
        
        # 3. 提取帧
        temp_dir = os.path.dirname(output_video_path)
        frames_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        frame_paths = self.video_processor.extract_frames(
            target_video_path, 
            frames_dir
        )
        
        # 4. 处理每一帧
        faces_detected = 0
        for i, frame_path in enumerate(frame_paths):
            frame = cv2.imread(frame_path)
            
            # 换脸
            if options.many_faces:
                target_faces = self.face_analyser.get_many_faces(frame)
            else:
                target_face = self.face_analyser.get_one_face(frame)
                target_faces = [target_face] if target_face else []
            
            if target_faces:
                faces_detected = max(faces_detected, len(target_faces))
                for target_face in target_faces:
                    frame = self.face_swapper.swap(
                        source_face, 
                        target_face, 
                        frame,
                        mouth_mask=options.mouth_mask
                    )
            
            # 增强
            if options.face_enhancer:
                frame = self.face_enhancer.enhance(frame)
            
            # 保存处理后的帧
            cv2.imwrite(frame_path, frame)
            
            # 进度日志
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(frame_paths)} frames")
        
        # 5. 合成视频
        fps = video_info['fps'] if options.keep_fps else 30.0
        self.video_processor.create_video(
            frames_dir,
            output_video_path,
            fps=fps,
            encoder=options.video_encoder,
            quality=options.video_quality
        )
        
        # 6. 恢复音频
        if options.keep_audio:
            self.video_processor.restore_audio(
                target_video_path,
                output_video_path
            )
        
        processing_time = time.time() - start_time
        
        return ProcessingResult(
            processing_time=processing_time,
            frames_processed=len(frame_paths),
            fps=fps,
            duration=video_info['duration'],
            faces_detected=faces_detected
        )
```

### 3.3 S3 服务 (`src/services/s3_service.py`)

封装 AWS S3 操作。

```python
"""
S3 Service - AWS S3 文件操作
"""
import os
import boto3
from botocore.exceptions import ClientError
from src.api.schemas import S3Location
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class S3Service:
    """AWS S3 服务封装"""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region
        )
        
    def download(self, location: S3Location, local_path: str) -> str:
        """
        从 S3 下载文件
        
        Args:
            location: S3 位置
            local_path: 本地保存路径
            
        Returns:
            本地文件路径
        """
        logger.info(f"Downloading s3://{location.bucket}/{location.key}")
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 下载文件
            self.client.download_file(
                location.bucket,
                location.key,
                local_path
            )
            
            logger.info(f"Downloaded to {local_path}")
            return local_path
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f"S3 download failed: {error_code} - {str(e)}")
            
    def upload(self, local_path: str, location: S3Location) -> str:
        """
        上传文件到 S3
        
        Args:
            local_path: 本地文件路径
            location: S3 目标位置
            
        Returns:
            S3 URI
        """
        logger.info(f"Uploading to s3://{location.bucket}/{location.key}")
        
        try:
            # 上传文件
            self.client.upload_file(
                local_path,
                location.bucket,
                location.key,
                ExtraArgs={
                    'ContentType': self._get_content_type(local_path)
                }
            )
            
            s3_uri = f"s3://{location.bucket}/{location.key}"
            logger.info(f"Uploaded to {s3_uri}")
            return s3_uri
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise Exception(f"S3 upload failed: {error_code} - {str(e)}")
            
    def _get_content_type(self, path: str) -> str:
        """根据文件扩展名获取 Content-Type"""
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
        }
        return content_types.get(ext, 'application/octet-stream')
```

### 3.4 配置管理 (`src/config.py`)

```python
"""
Configuration - 服务配置
"""
import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """服务配置"""
    
    # AWS
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_default_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # 模型路径
    models_dir: str = os.getenv("MODELS_DIR", "/app/models")
    swapper_model_path: str = ""
    enhancer_model_path: str = ""
    
    # 处理配置
    execution_provider: str = os.getenv("EXECUTION_PROVIDER", "cuda")
    execution_threads: int = int(os.getenv("EXECUTION_THREADS", "8"))
    
    # 限制
    max_video_duration: int = int(os.getenv("MAX_VIDEO_DURATION", "600"))
    max_video_size_mb: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "2048"))
    
    # 日志
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 临时目录
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp/face_swap_jobs")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.swapper_model_path = os.path.join(
            self.models_dir, "inswapper_128_fp16.onnx"
        )
        self.enhancer_model_path = os.path.join(
            self.models_dir, "GFPGANv1.4.pth"
        )
        
    @property
    def execution_providers(self) -> List[str]:
        """获取 ONNX 执行提供者列表"""
        provider_map = {
            "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
            "cpu": ["CPUExecutionProvider"],
        }
        return provider_map.get(self.execution_provider, ["CPUExecutionProvider"])

settings = Settings()
```

---

## 4. 数据流

### 4.1 视频换脸处理流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Video Face Swap Pipeline                              │
└─────────────────────────────────────────────────────────────────────────────┘

[1. Request Received]
         │
         ▼
┌─────────────────┐
│ Validate Input  │──▶ 400 Error if invalid
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Download Source │◀────▶│     AWS S3      │
│ Image from S3   │      │                 │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Download Target │◀────▶│     AWS S3      │
│ Video from S3   │      │                 │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Analyze Source  │──▶ Error if no face detected
│ Face            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract Frames  │──▶ FFmpeg: video → PNG frames
│ (FFmpeg)        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frame Processing Loop                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  For each frame:                                           │  │
│  │    1. Detect target face(s)                                │  │
│  │    2. Swap face(s) with source                             │  │
│  │    3. Apply mouth mask (optional)                          │  │
│  │    4. Enhance face (optional, GFPGAN)                      │  │
│  │    5. Save processed frame                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────┐
│ Create Video    │──▶ FFmpeg: PNG frames → video
│ (FFmpeg)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Restore Audio   │──▶ FFmpeg: merge audio from original
│ (FFmpeg)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ Upload Result   │──────▶│     AWS S3      │
│ to S3           │      │                 │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Send Webhook    │──▶ POST to callback_url
│ Callback        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cleanup Temp    │──▶ Remove /tmp/jobs/{job_id}/
│ Files           │
└─────────────────┘
```

### 4.2 模型加载流程

```
[Container Start]
         │
         ▼
┌─────────────────┐     N    ┌──────────────────────────────┐
│ Models exist in │─────────▶│ Download from HuggingFace    │
│ /app/models/?   │          │ (only during build)          │
└────────┬────────┘          └──────────────┬───────────────┘
         │ Y                                │
         ▼                                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Load Models to GPU Memory                       │
│                                                              │
│  1. InsightFace FaceAnalyser (buffalo_l)                    │
│     └─▶ ONNX Runtime with CUDAExecutionProvider             │
│                                                              │
│  2. InSwapper Face Swapper (inswapper_128_fp16.onnx)        │
│     └─▶ ONNX Runtime with CUDAExecutionProvider             │
│                                                              │
│  3. GFPGAN Face Enhancer (GFPGANv1.4.pth)                   │
│     └─▶ PyTorch with CUDA                                   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
[Ready to Accept Jobs]
```

---

## 5. 部署架构

### 5.1 Docker 镜像结构

```dockerfile
# Base image with CUDA
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.11 python3-pip ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download models (baked into image)
COPY download_models.py .
RUN python download_models.py

# Application code
COPY . /app
WORKDIR /app

# RunPod handler
CMD ["python", "-u", "src/handler.py"]
```

### 5.2 RunPod 配置

```json
{
  "name": "deep-live-cam-video-swap",
  "docker_image": "your-registry/deep-live-cam-api:latest",
  "gpu_type_id": "NVIDIA A10G",
  "gpu_count": 1,
  "volume_in_gb": 50,
  "container_disk_in_gb": 20,
  "idle_timeout": 60,
  "flashboot": true,
  "env": {
    "AWS_ACCESS_KEY_ID": "{{RUNPOD_SECRET_AWS_ACCESS_KEY_ID}}",
    "AWS_SECRET_ACCESS_KEY": "{{RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY}}",
    "AWS_DEFAULT_REGION": "us-east-1",
    "EXECUTION_PROVIDER": "cuda",
    "LOG_LEVEL": "INFO"
  }
}
```

---

## 6. 错误处理策略

### 6.1 重试机制

| 错误类型 | 重试次数 | 退避策略 |
|----------|----------|----------|
| S3 下载失败 | 3 | 指数退避 (1s, 2s, 4s) |
| S3 上传失败 | 3 | 指数退避 (1s, 2s, 4s) |
| Webhook 回调失败 | 3 | 指数退避 (5s, 15s, 45s) |
| GPU OOM | 0 | 不重试，直接失败 |
| 人脸检测失败 | 0 | 不重试，返回错误 |

### 6.2 资源清理

```python
# TempStorage 确保清理
class TempStorage:
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        
    def cleanup(self):
        """删除所有临时文件"""
        if os.path.exists(self.job_dir):
            shutil.rmtree(self.job_dir)
```
