# Deep-Live-Cam Video Face Swap API - Specification

> 内部服务规范文档  
> Version: 1.0.0  
> Last Updated: 2026-01-12

---

## 1. 项目概述

### 1.1 目标

将 Deep-Live-Cam 项目封装成可部署于 RunPod Serverless GPU 平台的 **视频换脸 API 服务**，提供以下核心能力：

- **视频换脸 (Video Face Swap)**: 将源人脸替换到目标视频中的所有帧
- **可选人脸增强**: 对换脸后的视频进行 GFPGAN 增强处理
- **S3 集成**: 通过 AWS S3 进行视频输入/输出

### 1.2 服务定位

| 属性 | 说明 |
|------|------|
| 服务类型 | 内部 API 服务 |
| 部署平台 | RunPod Serverless |
| GPU 要求 | NVIDIA GPU with CUDA 12.x |
| 使用场景 | 批量视频换脸处理 |

### 1.3 非目标 (Out of Scope)

- ❌ 图片换脸 (仅支持视频)
- ❌ 实时 Webcam 换脸
- ❌ GUI 界面
- ❌ Base64 输入/输出 (使用 S3)
- ❌ 公开 API (内部服务无需复杂认证)

---

## 2. 功能需求

### 2.1 核心 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查，返回 GPU 状态 |
| `/swap/video` | POST | 视频换脸主接口 |
| `/job/{job_id}` | GET | 查询任务状态 |

### 2.2 视频换脸 API (`/swap/video`)

#### 请求格式

```json
{
  "job_id": "uuid-xxxx-xxxx",
  "source_image_s3": {
    "bucket": "my-bucket",
    "key": "inputs/source_face.jpg",
    "region": "us-east-1"
  },
  "target_video_s3": {
    "bucket": "my-bucket",
    "key": "inputs/target_video.mp4",
    "region": "us-east-1"
  },
  "output_s3": {
    "bucket": "my-bucket",
    "key": "outputs/result_video.mp4",
    "region": "us-east-1"
  },
  "options": {
    "many_faces": false,
    "face_enhancer": true,
    "keep_fps": true,
    "keep_audio": true,
    "video_quality": 18,
    "video_encoder": "libx264",
    "mouth_mask": false,
    "execution_threads": 8
  },
  "callback_url": "https://api.internal.com/webhook/face-swap-complete"
}
```

#### 请求参数说明

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `job_id` | string | ✅ | - | 任务唯一标识，由调用方生成 |
| `source_image_s3` | S3Location | ✅ | - | 源人脸图片 S3 位置 |
| `target_video_s3` | S3Location | ✅ | - | 目标视频 S3 位置 |
| `output_s3` | S3Location | ✅ | - | 输出视频 S3 位置 |
| `options.many_faces` | boolean | ❌ | false | 是否处理所有检测到的人脸 |
| `options.face_enhancer` | boolean | ❌ | true | 是否启用 GFPGAN 增强 |
| `options.keep_fps` | boolean | ❌ | true | 保持原始帧率 |
| `options.keep_audio` | boolean | ❌ | true | 保持原始音频 |
| `options.video_quality` | int | ❌ | 18 | 视频质量 CRF (0-51, 越小质量越高) |
| `options.video_encoder` | string | ❌ | "libx264" | 视频编码器 |
| `options.mouth_mask` | boolean | ❌ | false | 保留原始嘴部动作 |
| `options.execution_threads` | int | ❌ | 8 | 并行处理线程数 |
| `callback_url` | string | ❌ | null | 任务完成回调 URL |

#### S3Location 对象

```json
{
  "bucket": "bucket-name",
  "key": "path/to/file",
  "region": "us-east-1"
}
```

#### 同步响应 (处理开始)

```json
{
  "success": true,
  "job_id": "uuid-xxxx-xxxx",
  "status": "processing",
  "message": "Video face swap job started"
}
```

#### Webhook 回调 (处理完成)

```json
{
  "job_id": "uuid-xxxx-xxxx",
  "status": "completed",
  "result": {
    "output_s3": {
      "bucket": "my-bucket",
      "key": "outputs/result_video.mp4",
      "region": "us-east-1"
    },
    "processing_time_seconds": 145.5,
    "frames_processed": 1800,
    "fps": 30,
    "duration_seconds": 60,
    "faces_detected": 1,
    "face_enhancer_applied": true
  }
}
```

#### 错误回调

```json
{
  "job_id": "uuid-xxxx-xxxx",
  "status": "failed",
  "error": {
    "code": "NO_FACE_DETECTED",
    "message": "No face detected in source image",
    "details": {}
  }
}
```

### 2.3 健康检查 API (`/health`)

#### 响应

```json
{
  "status": "healthy",
  "gpu": {
    "available": true,
    "name": "NVIDIA A10G",
    "memory_total_gb": 24,
    "memory_used_gb": 8.5,
    "cuda_version": "12.8"
  },
  "models": {
    "face_analyser": "loaded",
    "face_swapper": "loaded",
    "face_enhancer": "loaded"
  },
  "version": "1.0.0"
}
```

### 2.4 任务状态查询 (`/job/{job_id}`)

#### 响应

```json
{
  "job_id": "uuid-xxxx-xxxx",
  "status": "processing",
  "progress": {
    "current_frame": 450,
    "total_frames": 1800,
    "percentage": 25,
    "eta_seconds": 108
  },
  "created_at": "2026-01-12T10:00:00Z",
  "updated_at": "2026-01-12T10:01:30Z"
}
```

---

## 3. 技术规范

### 3.1 运行环境要求

| 组件 | 规格 |
|------|------|
| GPU | NVIDIA GPU with CUDA 12.x (推荐 A10G/A100) |
| VRAM | ≥ 16GB (推荐 24GB for 4K) |
| Python | 3.10 - 3.11 |
| CUDA | 12.8 |
| 系统依赖 | ffmpeg |

### 3.2 模型文件

| 模型 | 文件 | 大小 | 用途 |
|------|------|------|------|
| InSwapper | `inswapper_128_fp16.onnx` | ~550MB | 换脸核心模型 |
| GFPGAN | `GFPGANv1.4.pth` | ~350MB | 人脸增强模型 |
| InsightFace | `buffalo_l` | ~300MB | 人脸检测/分析 |

### 3.3 输入限制

| 参数 | 限制 |
|------|------|
| 源图片最大尺寸 | 4096x4096 |
| 源图片最大文件大小 | 10MB |
| 目标视频最大时长 | 10分钟 (600秒) |
| 目标视频最大文件大小 | 2GB |
| 目标视频最大分辨率 | 4K (3840x2160) |
| 支持的图片格式 | PNG, JPG, JPEG, WEBP |
| 支持的视频格式 | MP4, MKV, AVI, MOV, WEBM |

### 3.4 错误码定义

| 状态码 | 错误代码 | 描述 |
|--------|----------|------|
| 400 | `INVALID_REQUEST` | 请求格式错误 |
| 400 | `INVALID_S3_LOCATION` | S3 位置无效 |
| 400 | `NO_FACE_IN_SOURCE` | 源图片中未检测到人脸 |
| 400 | `NO_FACE_IN_VIDEO` | 视频中未检测到人脸 |
| 400 | `UNSUPPORTED_FORMAT` | 不支持的文件格式 |
| 413 | `FILE_TOO_LARGE` | 文件超过大小限制 |
| 413 | `VIDEO_TOO_LONG` | 视频超过时长限制 |
| 500 | `S3_DOWNLOAD_ERROR` | S3 下载失败 |
| 500 | `S3_UPLOAD_ERROR` | S3 上传失败 |
| 500 | `PROCESSING_ERROR` | 处理过程错误 |
| 500 | `FFMPEG_ERROR` | FFmpeg 处理错误 |
| 503 | `MODEL_LOADING_ERROR` | 模型加载失败 |
| 503 | `GPU_NOT_AVAILABLE` | GPU 不可用 |

---

## 4. 非功能性需求

### 4.1 性能指标

| 指标 | 目标值 |
|------|--------|
| 视频处理速度 | ≥ 15 fps (1080p, A10G) |
| 1分钟视频处理时间 | < 180s (含增强) |
| 冷启动时间 | < 60s |
| 模型加载时间 | < 30s |

### 4.2 可靠性

- 任务失败自动重试 (最多 2 次)
- 处理过程中断点续传支持 (未来)
- 详细错误日志记录
- Webhook 回调失败重试 (3 次，指数退避)

### 4.3 存储

- 处理完成后自动清理临时文件
- 不持久化任何用户数据
- 日志保留 7 天

### 4.4 监控

- 任务状态实时更新
- 处理进度百分比
- GPU 内存使用监控
- 错误率告警

---

## 5. AWS S3 集成规范

### 5.1 IAM 权限要求

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket/*"
      ]
    }
  ]
}
```

### 5.2 认证方式

通过环境变量配置 AWS 凭证：

```bash
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_DEFAULT_REGION=us-east-1
```

或使用 IAM Role (推荐生产环境)。

### 5.3 S3 文件命名建议

```
inputs/
  source_images/
    {job_id}_source.jpg
  target_videos/
    {job_id}_target.mp4

outputs/
  {job_id}/
    result.mp4
    metadata.json
```

---

## 6. 部署配置

### 6.1 RunPod 配置

```json
{
  "name": "deep-live-cam-video-swap",
  "gpu_type": "NVIDIA A10G",
  "gpu_count": 1,
  "volume_size_gb": 50,
  "container_disk_gb": 20,
  "idle_timeout_seconds": 60,
  "max_workers": 1,
  "env_vars": {
    "AWS_DEFAULT_REGION": "us-east-1",
    "LOG_LEVEL": "INFO",
    "EXECUTION_PROVIDER": "cuda"
  }
}
```

### 6.2 环境变量

| 变量名 | 必填 | 默认值 | 描述 |
|--------|------|--------|------|
| `AWS_ACCESS_KEY_ID` | ✅ | - | AWS Access Key |
| `AWS_SECRET_ACCESS_KEY` | ✅ | - | AWS Secret Key |
| `AWS_DEFAULT_REGION` | ❌ | us-east-1 | AWS 默认区域 |
| `EXECUTION_PROVIDER` | ❌ | cuda | ONNX 执行提供者 |
| `EXECUTION_THREADS` | ❌ | 8 | 默认并行线程数 |
| `LOG_LEVEL` | ❌ | INFO | 日志级别 |
| `MAX_VIDEO_DURATION` | ❌ | 600 | 最大视频时长(秒) |
| `MAX_VIDEO_SIZE_MB` | ❌ | 2048 | 最大视频大小(MB) |
