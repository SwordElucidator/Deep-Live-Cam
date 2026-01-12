# Deep-Live-Cam Video Face Swap API - Task Breakdown

> 任务拆解文档  
> Version: 1.0.0  
> Last Updated: 2026-01-12

---

## 总览

| Phase | 名称 | 任务数 | 预估工时 | 优先级 |
|-------|------|--------|----------|--------|
| P1 | 项目初始化 | 5 | 4h | 🔴 Critical |
| P2 | 核心引擎封装 | 6 | 12h | 🔴 Critical |
| P3 | S3 集成 | 4 | 6h | 🔴 Critical |
| P4 | RunPod Handler | 4 | 8h | 🔴 Critical |
| P5 | 视频处理流程 | 5 | 10h | 🔴 Critical |
| P6 | Docker 部署 | 4 | 6h | 🟡 High |
| P7 | 测试 | 4 | 8h | 🟡 High |
| **Total** | | **32** | **54h** | |

---

## Phase 1: 项目初始化

### T1.1 创建目录结构
**预估时间**: 0.5h  
**依赖**: 无

创建 `serverless/src/` 目录结构:
```
serverless/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── tests/
│   └── __init__.py
└── requirements.txt
```

**验收标准**:
- [ ] 所有目录和 `__init__.py` 文件已创建
- [ ] Python import 路径正确

---

### T1.2 配置 requirements.txt
**预估时间**: 0.5h  
**依赖**: T1.1

```
# Core
runpod==1.6.0
boto3==1.34.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Deep Learning
torch==2.1.0+cu121
torchvision==0.16.0+cu121
onnxruntime-gpu==1.16.3
insightface==0.7.3
gfpgan==1.3.8

# Image/Video Processing
opencv-python==4.8.1.78
numpy>=1.23.5,<2
pillow==10.1.0

# Utilities
tqdm==4.66.1
requests==2.31.0
```

**验收标准**:
- [ ] 所有依赖版本锁定
- [ ] CUDA 12.1 兼容版本

---

### T1.3 创建配置管理模块
**预估时间**: 1h  
**依赖**: T1.2

**文件**: `src/config.py`

**功能**:
- 环境变量读取
- 默认值设置
- 配置验证

**验收标准**:
- [ ] 支持从环境变量加载配置
- [ ] 配置项有合理默认值
- [ ] 包含所有 AWS/GPU/限制相关配置

---

### T1.4 创建日志工具模块
**预估时间**: 1h  
**依赖**: T1.1

**文件**: `src/utils/logger.py`

**功能**:
- 结构化 JSON 日志
- 日志级别控制
- Job ID 上下文

**验收标准**:
- [ ] 支持 INFO/DEBUG/ERROR 级别
- [ ] 日志包含 timestamp, level, message
- [ ] 支持 job_id 上下文注入

---

### T1.5 创建 Pydantic Schemas
**预估时间**: 1h  
**依赖**: T1.1

**文件**: `src/api/schemas.py`

**模型**:
- `S3Location`
- `ProcessingOptions`
- `SwapVideoRequest`
- `SwapVideoResponse`
- `ProcessingResult`
- `ErrorResponse`

**验收标准**:
- [ ] 所有字段类型正确
- [ ] 包含字段验证
- [ ] 支持 `.dict()` 序列化

---

## Phase 2: 核心引擎封装

### T2.1 封装 FaceAnalyser
**预估时间**: 2h  
**依赖**: T1.3

**文件**: `src/core/face_analyser.py`

**功能**:
- 从原项目 `modules/face_analyser.py` 提取
- 无状态化设计
- 支持 CUDA 执行提供者

**接口**:
```python
class FaceAnalyser:
    def __init__(self, providers: List[str]): ...
    def get_one_face(self, frame: np.ndarray) -> Optional[Face]: ...
    def get_many_faces(self, frame: np.ndarray) -> List[Face]: ...
```

**验收标准**:
- [ ] 能正确检测人脸
- [ ] 支持 CUDA 加速
- [ ] 单例模式，模型只加载一次

---

### T2.2 封装 FaceSwapper
**预估时间**: 3h  
**依赖**: T2.1

**文件**: `src/core/face_swapper.py`

**功能**:
- 从原项目 `modules/processors/frame/face_swapper.py` 提取
- 简化接口，移除 UI 相关代码
- 支持 mouth_mask 选项

**接口**:
```python
class FaceSwapper:
    def __init__(self, model_path: str, providers: List[str]): ...
    def swap(
        self, 
        source_face: Face, 
        target_face: Face, 
        frame: np.ndarray,
        mouth_mask: bool = False
    ) -> np.ndarray: ...
```

**验收标准**:
- [ ] 换脸效果与原项目一致
- [ ] 支持 mouth_mask 选项
- [ ] CUDA 加速正常工作

---

### T2.3 封装 FaceEnhancer
**预估时间**: 2h  
**依赖**: T1.3

**文件**: `src/core/face_enhancer.py`

**功能**:
- 从原项目 `modules/processors/frame/face_enhancer.py` 提取
- GFPGAN 增强

**接口**:
```python
class FaceEnhancer:
    def __init__(self, model_path: str): ...
    def enhance(self, frame: np.ndarray) -> np.ndarray: ...
```

**验收标准**:
- [ ] 增强效果与原项目一致
- [ ] GPU/CUDA 支持
- [ ] 处理失败时返回原始帧

---

### T2.4 创建 FFmpeg 工具模块
**预估时间**: 2h  
**依赖**: T1.1

**文件**: `src/utils/ffmpeg.py`

**功能**:
- 视频信息获取 (fps, duration, resolution)
- 帧提取 (video → PNG frames)
- 视频合成 (PNG frames → video)
- 音频恢复

**接口**:
```python
def get_video_info(video_path: str) -> VideoInfo: ...
def extract_frames(video_path: str, output_dir: str) -> List[str]: ...
def create_video(frames_dir: str, output_path: str, fps: float, encoder: str, quality: int): ...
def restore_audio(source_video: str, target_video: str): ...
```

**验收标准**:
- [ ] 支持 MP4/MKV/AVI/MOV
- [ ] 帧提取质量高 (PNG lossless)
- [ ] 音频完整恢复

---

### T2.5 创建 VideoProcessor 模块
**预估时间**: 2h  
**依赖**: T2.4

**文件**: `src/core/video_processor.py`

**功能**:
- 整合 FFmpeg 工具
- 视频处理流程编排
- 进度报告

**接口**:
```python
class VideoProcessor:
    def get_video_info(self, video_path: str) -> dict: ...
    def extract_frames(self, video_path: str, output_dir: str) -> List[str]: ...
    def create_video(self, frames_dir: str, output_path: str, **kwargs): ...
    def restore_audio(self, source_video: str, target_video: str): ...
```

**验收标准**:
- [ ] 完整的视频处理流程
- [ ] 错误处理完善

---

### T2.6 创建统一 Engine
**预估时间**: 1h  
**依赖**: T2.1, T2.2, T2.3, T2.5

**文件**: `src/core/engine.py`

**功能**:
- 整合所有核心组件
- 模型加载管理
- 视频换脸主流程

**接口**:
```python
class FaceSwapEngine:
    def load_models(self): ...
    def process_video(
        self,
        source_image_path: str,
        target_video_path: str,
        output_video_path: str,
        options: ProcessingOptions
    ) -> ProcessingResult: ...
```

**验收标准**:
- [ ] 端到端视频换脸工作正常
- [ ] 模型只加载一次

---

## Phase 3: S3 集成

### T3.1 创建 S3Service
**预估时间**: 2h  
**依赖**: T1.3, T1.5

**文件**: `src/services/s3_service.py`

**功能**:
- S3 文件下载
- S3 文件上传
- 错误处理和重试

**接口**:
```python
class S3Service:
    def __init__(self): ...
    def download(self, location: S3Location, local_path: str) -> str: ...
    def upload(self, local_path: str, location: S3Location) -> str: ...
    def check_exists(self, location: S3Location) -> bool: ...
```

**验收标准**:
- [ ] 支持跨 Region 访问
- [ ] 下载/上传重试机制
- [ ] 正确的 Content-Type 设置

---

### T3.2 创建 TempStorage
**预估时间**: 1h  
**依赖**: T1.3

**文件**: `src/services/temp_storage.py`

**功能**:
- Job 临时目录管理
- 自动清理

**接口**:
```python
class TempStorage:
    def __init__(self, job_id: str): ...
    def get_path(self, filename: str) -> str: ...
    def cleanup(self): ...
```

**验收标准**:
- [ ] 每个 Job 独立目录
- [ ] 支持 context manager
- [ ] 清理可靠

---

### T3.3 创建 CallbackService
**预估时间**: 1.5h  
**依赖**: T1.3, T1.4

**文件**: `src/services/callback_service.py`

**功能**:
- Webhook 回调发送
- 重试机制
- 超时处理

**接口**:
```python
class CallbackService:
    @staticmethod
    def send(url: str, payload: dict, max_retries: int = 3): ...
```

**验收标准**:
- [ ] 指数退避重试
- [ ] 请求超时设置
- [ ] 失败日志记录

---

### T3.4 创建输入验证器
**预估时间**: 1.5h  
**依赖**: T1.5

**文件**: `src/api/validators.py`

**功能**:
- 请求格式验证
- S3 位置验证
- 文件大小/时长限制检查

**接口**:
```python
def validate_request(input_data: dict) -> SwapVideoRequest: ...
def validate_s3_location(location: S3Location): ...
def validate_video_constraints(video_info: dict): ...
```

**验收标准**:
- [ ] 完整的字段验证
- [ ] 清晰的错误消息
- [ ] 限制检查完整

---

## Phase 4: RunPod Handler

### T4.1 创建 Handler 骨架
**预估时间**: 2h  
**依赖**: T1.3, T1.5

**文件**: `src/handler.py`

**功能**:
- RunPod 入口点
- 初始化逻辑
- 基本请求处理框架

**验收标准**:
- [ ] `runpod.serverless.start()` 正确调用
- [ ] 初始化在启动时执行
- [ ] 基本错误处理

---

### T4.2 实现 Job 处理流程
**预估时间**: 3h  
**依赖**: T4.1, T2.6, T3.1, T3.2

**文件**: `src/handler.py`

**功能**:
- 完整的任务处理流程
- S3 下载 → 处理 → S3 上传
- 回调发送

**验收标准**:
- [ ] 端到端流程工作
- [ ] 进度日志完整
- [ ] 临时文件清理

---

### T4.3 实现错误处理
**预估时间**: 2h  
**依赖**: T4.2

**文件**: `src/handler.py`

**功能**:
- 异常捕获和分类
- 错误响应格式化
- 失败回调发送

**验收标准**:
- [ ] 所有异常被捕获
- [ ] 错误码正确
- [ ] 回调发送可靠

---

### T4.4 实现健康检查
**预估时间**: 1h  
**依赖**: T4.1

**文件**: `src/handler.py`

**功能**:
- GPU 状态检测
- 模型加载状态
- 版本信息

**验收标准**:
- [ ] GPU 信息准确
- [ ] 模型状态正确

---

## Phase 5: 视频处理流程

### T5.1 帧处理循环优化
**预估时间**: 2h  
**依赖**: T2.6

**文件**: `src/core/engine.py`

**功能**:
- 批量帧处理
- 内存管理优化
- 进度报告

**验收标准**:
- [ ] 内存使用稳定
- [ ] 不出现 OOM
- [ ] 进度准确

---

### T5.2 多线程帧处理
**预估时间**: 3h  
**依赖**: T5.1

**文件**: `src/core/engine.py`

**功能**:
- 并行帧处理
- 线程池管理
- 顺序保证

**验收标准**:
- [ ] 并行处理有效提速
- [ ] 输出顺序正确
- [ ] 线程安全

---

### T5.3 many_faces 支持
**预估时间**: 2h  
**依赖**: T5.1

**文件**: `src/core/engine.py`

**功能**:
- 多人脸检测
- 多人脸替换
- 性能优化

**验收标准**:
- [ ] 支持多人脸场景
- [ ] 所有人脸都被替换

---

### T5.4 mouth_mask 支持
**预估时间**: 2h  
**依赖**: T5.1

**文件**: `src/core/face_swapper.py`

**功能**:
- 嘴部区域保留
- 平滑混合

**验收标准**:
- [ ] 嘴部动作自然
- [ ] 边缘平滑

---

### T5.5 GPU 内存管理
**预估时间**: 1h  
**依赖**: T5.2

**文件**: `src/utils/gpu.py`

**功能**:
- GPU 内存监控
- 及时释放
- OOM 预防

**验收标准**:
- [ ] 处理完成后内存释放
- [ ] 长时间运行稳定

---

## Phase 6: Docker 部署

### T6.1 创建 Dockerfile
**预估时间**: 2h  
**依赖**: T1.2

**文件**: `serverless/Dockerfile`

**功能**:
- CUDA 基础镜像
- 系统依赖安装
- Python 环境配置

**验收标准**:
- [ ] 镜像构建成功
- [ ] CUDA 可用
- [ ] FFmpeg 可用

---

### T6.2 创建模型下载脚本
**预估时间**: 1h  
**依赖**: T6.1

**文件**: `serverless/download_models.py`

**功能**:
- 从 HuggingFace 下载模型
- 验证模型完整性
- 放置到正确目录

**验收标准**:
- [ ] 所有模型下载成功
- [ ] 文件校验通过

---

### T6.3 烘焙模型到镜像
**预估时间**: 1h  
**依赖**: T6.1, T6.2

**文件**: `serverless/Dockerfile`

**功能**:
- 构建时下载模型
- 模型预置到镜像

**验收标准**:
- [ ] 镜像包含所有模型
- [ ] 冷启动无需下载

---

### T6.4 RunPod 部署配置
**预估时间**: 2h  
**依赖**: T6.3

**文件**: `serverless/runpod_config.json`

**功能**:
- RunPod 模板配置
- 环境变量配置
- GPU 类型选择

**验收标准**:
- [ ] 成功部署到 RunPod
- [ ] GPU 正确识别
- [ ] 环境变量生效

---

## Phase 7: 测试

### T7.1 核心模块单元测试
**预估时间**: 2h  
**依赖**: P2 完成

**文件**: `tests/test_core.py`

**测试范围**:
- FaceAnalyser
- FaceSwapper
- FaceEnhancer
- VideoProcessor

**验收标准**:
- [ ] 所有模块测试覆盖
- [ ] 测试通过率 100%

---

### T7.2 S3 服务测试
**预估时间**: 2h  
**依赖**: P3 完成

**文件**: `tests/test_s3_service.py`

**测试范围**:
- 下载功能
- 上传功能
- 错误处理

**验收标准**:
- [ ] 支持 mock S3
- [ ] 错误场景覆盖

---

### T7.3 Handler 集成测试
**预估时间**: 2h  
**依赖**: P4 完成

**文件**: `tests/test_handler.py`

**测试范围**:
- 请求验证
- 完整处理流程
- 错误响应

**验收标准**:
- [ ] 端到端测试通过
- [ ] 错误场景覆盖

---

### T7.4 性能测试
**预估时间**: 2h  
**依赖**: P6 完成

**测试范围**:
- 1分钟 1080p 视频处理时间
- 内存使用监控
- GPU 利用率

**验收标准**:
- [ ] 达到性能目标 (< 180s/1min video)
- [ ] 内存使用稳定

---

## 依赖关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Task Dependencies                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1: Project Init
T1.1 ──┬──▶ T1.2 ──▶ T1.3 ──┬──▶ T1.4
       │                     │
       └─────────────────────┴──▶ T1.5

Phase 2: Core Engine
T1.3 ──▶ T2.1 ──┬──▶ T2.2 ──┐
                │           │
                └──▶ T2.3   │
                            │
T1.1 ──▶ T2.4 ──▶ T2.5 ────┼──▶ T2.6
                            │
                            │
Phase 3: S3 Integration     │
T1.3, T1.5 ──▶ T3.1 ────────┼──▶ T4.2
                            │
T1.3 ──▶ T3.2 ──────────────┤
                            │
T1.3, T1.4 ──▶ T3.3 ────────┤
                            │
T1.5 ──▶ T3.4 ──────────────┘

Phase 4: RunPod Handler
T1.3, T1.5 ──▶ T4.1 ──▶ T4.2 ──▶ T4.3
                  │
                  └──▶ T4.4

Phase 5: Video Processing
T2.6 ──▶ T5.1 ──┬──▶ T5.2 ──▶ T5.5
                │
                ├──▶ T5.3
                │
                └──▶ T5.4

Phase 6: Docker Deploy
T1.2 ──▶ T6.1 ──▶ T6.2 ──▶ T6.3 ──▶ T6.4

Phase 7: Testing
P2 ──▶ T7.1
P3 ──▶ T7.2
P4 ──▶ T7.3
P6 ──▶ T7.4
```

---

## 里程碑

| 里程碑 | 完成标准 | 预计完成 |
|--------|----------|----------|
| M1: 核心引擎可用 | P1 + P2 完成，本地测试通过 | Day 3 |
| M2: S3 集成完成 | P3 完成，能从 S3 下载上传 | Day 4 |
| M3: Handler 可用 | P4 完成，RunPod 本地测试通过 | Day 5 |
| M4: 视频处理优化 | P5 完成，性能达标 | Day 6 |
| M5: 部署就绪 | P6 完成，RunPod 部署成功 | Day 7 |
| M6: 测试通过 | P7 完成，所有测试通过 | Day 8 |

---

## Checklist 总览

```
Phase 1: Project Init
[ ] T1.1 创建目录结构
[ ] T1.2 配置 requirements.txt
[ ] T1.3 创建配置管理模块
[ ] T1.4 创建日志工具模块
[ ] T1.5 创建 Pydantic Schemas

Phase 2: Core Engine
[ ] T2.1 封装 FaceAnalyser
[ ] T2.2 封装 FaceSwapper
[ ] T2.3 封装 FaceEnhancer
[ ] T2.4 创建 FFmpeg 工具模块
[ ] T2.5 创建 VideoProcessor 模块
[ ] T2.6 创建统一 Engine

Phase 3: S3 Integration
[ ] T3.1 创建 S3Service
[ ] T3.2 创建 TempStorage
[ ] T3.3 创建 CallbackService
[ ] T3.4 创建输入验证器

Phase 4: RunPod Handler
[ ] T4.1 创建 Handler 骨架
[ ] T4.2 实现 Job 处理流程
[ ] T4.3 实现错误处理
[ ] T4.4 实现健康检查

Phase 5: Video Processing
[ ] T5.1 帧处理循环优化
[ ] T5.2 多线程帧处理
[ ] T5.3 many_faces 支持
[ ] T5.4 mouth_mask 支持
[ ] T5.5 GPU 内存管理

Phase 6: Docker Deploy
[ ] T6.1 创建 Dockerfile
[ ] T6.2 创建模型下载脚本
[ ] T6.3 烘焙模型到镜像
[ ] T6.4 RunPod 部署配置

Phase 7: Testing
[ ] T7.1 核心模块单元测试
[ ] T7.2 S3 服务测试
[ ] T7.3 Handler 集成测试
[ ] T7.4 性能测试
```
