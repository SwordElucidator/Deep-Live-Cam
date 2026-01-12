# 🚀 RunPod 部署指南

## 前置条件

1. **Docker Hub 账户** - 用于推送镜像
2. **GitHub 账户** - 用于 CI/CD
3. **RunPod 账户** - 已配置 API Key
4. **AWS 账户** - 用于 S3 存储视频

## 部署步骤

### Step 1: 配置 RunPod Secrets

在 RunPod 控制台配置 AWS 凭证：

1. 访问 https://www.runpod.io/console/user/secrets
2. 添加以下 Secrets：
   - `AWS_ACCESS_KEY_ID`: 你的 AWS Access Key
   - `AWS_SECRET_ACCESS_KEY`: 你的 AWS Secret Key

### Step 2: 配置 GitHub Actions (推荐)

#### 2.1 创建 Docker Hub Access Token

1. 访问 https://hub.docker.com/settings/security
2. 点击 "New Access Token"
3. 描述: `github-actions`
4. 权限: `Read & Write`
5. 复制生成的 Token

#### 2.2 配置 GitHub Secrets

在你的 GitHub 仓库中：

1. 访问 Settings → Secrets and variables → Actions
2. 添加以下 Secrets：
   - `DOCKERHUB_USERNAME`: `swordelucidator`
   - `DOCKERHUB_TOKEN`: 你刚创建的 Access Token

#### 2.3 触发构建

推送代码到 main 分支，或在 GitHub Actions 页面手动触发 "Build and Push Serverless API"

### Step 2 (备选): 本地构建

```bash
# 设置变量
export DOCKER_USERNAME="your_dockerhub_username"
export IMAGE_TAG="latest"

# 进入 serverless 目录
cd Deep-Live-Cam/serverless

# 构建镜像 (需要 ~30 分钟，镜像约 15GB)
docker build --platform linux/amd64 -t $DOCKER_USERNAME/deep-live-cam-api:$IMAGE_TAG .

# 登录 Docker Hub
docker login

# 推送镜像
docker push $DOCKER_USERNAME/deep-live-cam-api:$IMAGE_TAG
```

### Step 3: 在 RunPod 创建 Serverless Endpoint

1. 访问 https://www.runpod.io/console/serverless
2. 点击 "New Endpoint"
3. 配置如下：

| 设置 | 值 |
|------|-----|
| Name | `deep-live-cam-video-swap` |
| Docker Image | `<your_username>/deep-live-cam-api:latest` |
| GPU Type | RTX 4090 (24GB) 或 L4 (24GB) |
| Min Workers | 0 |
| Max Workers | 3 |
| Idle Timeout | 60s |
| Container Disk | 30 GB |
| Volume | 50 GB |
| Flash Boot | ✅ Enabled |

4. 添加环境变量：

```
MODELS_DIR=/app/models
EXECUTION_PROVIDER=cuda
EXECUTION_THREADS=8
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID={{ RUNPOD_SECRET_AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY={{ RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY }}
```

5. 点击 "Create Endpoint"

### Step 4: 测试 Endpoint

```bash
export RUNPOD_API_KEY="your_api_key"
export ENDPOINT_ID="your_endpoint_id"

# 健康检查
python deploy/deploy.py test $ENDPOINT_ID
```

## API 使用示例

### 视频换脸请求

```bash
curl -X POST "https://api.runpod.ai/v2/${ENDPOINT_ID}/run" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "swap_video",
      "job_id": "job-001",
      "source_image": {
        "bucket": "your-bucket",
        "key": "faces/source.jpg",
        "region": "us-east-1"
      },
      "target_video": {
        "bucket": "your-bucket",
        "key": "videos/target.mp4",
        "region": "us-east-1"
      },
      "output": {
        "bucket": "your-bucket",
        "key": "results/output.mp4",
        "region": "us-east-1"
      },
      "options": {
        "face_enhancer": true,
        "keep_audio": true,
        "video_quality": 18
      }
    }
  }'
```

### 查询任务状态

```bash
curl "https://api.runpod.ai/v2/${ENDPOINT_ID}/status/${JOB_ID}" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}"
```

## 费用估算

| GPU | 价格 | 推荐场景 |
|-----|------|---------|
| RTX 4090 | ~$0.44/hr | 生产环境 |
| L4 | ~$0.24/hr | 开发测试 |
| RTX 3090 | ~$0.22/hr | 低成本 |

> 处理一个 1 分钟视频约需 2-5 分钟 GPU 时间

## 故障排除

### 镜像拉取失败
确保 Docker 镜像是公开的，或配置 Docker Hub 凭证。

### AWS 凭证错误
检查 RunPod Secrets 是否正确配置。

### GPU 内存不足
使用至少 16GB VRAM 的 GPU。

### 处理超时
默认超时 600 秒，如需处理更长视频，在创建 Endpoint 时增加 Execution Timeout。
