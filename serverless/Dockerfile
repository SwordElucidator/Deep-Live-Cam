# Deep-Live-Cam Video Face Swap API
# RunPod Serverless Dockerfile
#
# Build:
#   docker build -t deep-live-cam-api:latest .
#
# Run locally:
#   docker run --gpus all \
#     -e AWS_ACCESS_KEY_ID=xxx \
#     -e AWS_SECRET_ACCESS_KEY=xxx \
#     -e AWS_DEFAULT_REGION=us-east-1 \
#     deep-live-cam-api:latest

# ============================================
# Stage 1: Base Image with CUDA
# ============================================
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# ============================================
# Stage 2: Python Dependencies
# ============================================
FROM base AS dependencies

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (with CUDA support)
RUN pip install --no-cache-dir torch==2.1.0+cu121 torchvision==0.16.0+cu121 \
    --extra-index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies
RUN pip install --no-cache-dir \
    runpod==1.6.0 \
    boto3==1.34.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    onnxruntime-gpu==1.16.3 \
    onnx==1.15.0 \
    insightface==0.7.3 \
    opencv-python==4.8.1.78 \
    numpy>=1.23.5,<2 \
    pillow==10.1.0 \
    tqdm==4.66.1 \
    requests==2.31.0

# Install GFPGAN and dependencies
RUN pip install --no-cache-dir \
    basicsr==1.4.2 \
    facexlib==0.3.0 \
    gfpgan==1.3.8

# ============================================
# Stage 3: Download Models
# ============================================
FROM dependencies AS models

WORKDIR /app

# Copy model download script
COPY download_models.py .

# Create models directory and download models
RUN mkdir -p /app/models && \
    python download_models.py --models-dir /app/models --skip-insightface

# InsightFace model will be downloaded on first use
# Pre-download to bake into image
RUN python -c "from insightface.app import FaceAnalysis; \
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
    app.prepare(ctx_id=0, det_size=(640, 640)); \
    print('InsightFace model cached')"

# ============================================
# Stage 4: Final Image
# ============================================
FROM dependencies AS final

WORKDIR /app

# Copy models from models stage
COPY --from=models /app/models /app/models
COPY --from=models /root/.insightface /root/.insightface

# Copy application source code
COPY src/ /app/src/

# ============================================
# Environment Configuration
# ============================================

# Python settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Models directory
ENV MODELS_DIR=/app/models

# GPU settings
ENV EXECUTION_PROVIDER=cuda
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Processing defaults
ENV EXECUTION_THREADS=8
ENV MAX_VIDEO_DURATION=600
ENV MAX_VIDEO_SIZE_MB=2048

# Logging
ENV LOG_LEVEL=INFO

# Temp directory
ENV TEMP_DIR=/tmp/face_swap_jobs

# ============================================
# Health Check
# ============================================
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" || exit 1

# ============================================
# Entry Point
# ============================================
CMD ["python", "-u", "src/handler.py"]
