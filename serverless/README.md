# Deep-Live-Cam Video Face Swap API

> 基于 Deep-Live-Cam 的 Serverless GPU 视频换脸 API 服务  
> 部署平台: RunPod Serverless

---

## 📚 文档

| 文档 | 描述 |
|------|------|
| [SPEC.md](./SPEC.md) | 服务规范 - API 定义、技术要求、限制 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 技术架构 - 系统设计、组件、数据流 |
| [TASKS.md](./TASKS.md) | 任务拆解 - 开发计划、依赖关系 |

---

## 🚀 快速开始

### 本地开发

```bash
# 1. 进入 serverless 目录
cd Deep-Live-Cam/serverless

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载模型 (如果不在 ../models 目录)
python download_models.py

# 5. 设置环境变量
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# 6. 运行测试
pytest tests/
```

### Docker 构建

```bash
# 构建镜像 (包含模型)
docker build -t deep-live-cam-api:latest .

# 本地测试运行
docker run --gpus all \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=xxx \
  -p 8000:8000 \
  deep-live-cam-api:latest
```

### RunPod 部署

```bash
# 推送镜像到 DockerHub 或 ECR
docker tag deep-live-cam-api:latest your-registry/deep-live-cam-api:latest
docker push your-registry/deep-live-cam-api:latest

# 在 RunPod 创建 Serverless Endpoint
# 使用 runpod_config.json 中的配置
```

---

## 📡 API 使用

### 视频换脸请求

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "job_id": "my-job-001",
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
        "key": "outputs/result.mp4",
        "region": "us-east-1"
      },
      "options": {
        "face_enhancer": true,
        "keep_fps": true,
        "keep_audio": true
      },
      "callback_url": "https://your-api.com/webhook"
    }
  }'
```

### 响应示例

```json
{
  "id": "runpod-job-id",
  "status": "IN_QUEUE"
}
```

### Webhook 回调

任务完成后，系统会向 `callback_url` 发送 POST 请求:

```json
{
  "job_id": "my-job-001",
  "status": "completed",
  "result": {
    "output_s3": {
      "bucket": "my-bucket",
      "key": "outputs/result.mp4",
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

---

## ⚙️ 配置选项

| 选项 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `many_faces` | bool | false | 替换所有检测到的人脸 |
| `face_enhancer` | bool | true | 启用 GFPGAN 人脸增强 |
| `keep_fps` | bool | true | 保持原始帧率 |
| `keep_audio` | bool | true | 保持原始音频 |
| `video_quality` | int | 18 | 视频质量 CRF (0-51) |
| `video_encoder` | string | "libx264" | 视频编码器 |
| `mouth_mask` | bool | false | 保留原始嘴部动作 |
| `execution_threads` | int | 8 | 并行处理线程数 |

---

## 🔧 环境变量

| 变量 | 必填 | 描述 |
|------|------|------|
| `AWS_ACCESS_KEY_ID` | ✅ | AWS Access Key |
| `AWS_SECRET_ACCESS_KEY` | ✅ | AWS Secret Key |
| `AWS_DEFAULT_REGION` | ❌ | AWS 默认区域 (默认: us-east-1) |
| `EXECUTION_PROVIDER` | ❌ | ONNX 执行提供者 (默认: cuda) |
| `LOG_LEVEL` | ❌ | 日志级别 (默认: INFO) |

---

## 📁 项目结构

```
serverless/
├── README.md               # 本文件
├── SPEC.md                 # 服务规范
├── ARCHITECTURE.md         # 技术架构
├── TASKS.md                # 任务拆解
│
├── src/                    # 源代码
│   ├── handler.py          # RunPod Handler 入口
│   ├── config.py           # 配置管理
│   ├── api/                # API 相关
│   ├── core/               # 核心处理引擎
│   ├── services/           # 外部服务集成
│   └── utils/              # 工具模块
│
├── Dockerfile              # Docker 构建文件
├── requirements.txt        # Python 依赖
├── download_models.py      # 模型下载脚本
│
└── tests/                  # 测试
```

---

## 📊 性能指标

| 指标 | 目标值 | GPU |
|------|--------|-----|
| 1分钟视频处理时间 | < 180s | A10G |
| 1分钟视频处理时间 | < 120s | A100 |
| 处理速度 | ≥ 15 fps | A10G |
| 冷启动时间 | < 60s | - |

---

## 🔒 限制

| 参数 | 限制 |
|------|------|
| 视频最大时长 | 10分钟 |
| 视频最大大小 | 2GB |
| 视频最大分辨率 | 4K |
| 源图片最大大小 | 10MB |

---

## 📝 License

本项目基于 Deep-Live-Cam 开发，仅供内部使用。
