#!/usr/bin/env python3
"""
Model Download Script

Downloads required models for Deep-Live-Cam Video Face Swap API:
1. inswapper_128_fp16.onnx - Face swap model
2. GFPGANv1.4.pth - Face enhancement model
"""

import os
import sys
import time
import hashlib
from pathlib import Path

# Try to import requests, fall back to urllib
try:
    import requests
    USE_REQUESTS = True
except ImportError:
    import urllib.request
    USE_REQUESTS = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Required models
MODELS = [
    {
        "name": "inswapper_128_fp16.onnx",
        "url": "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128_fp16.onnx",
        "size_mb": 550,
        "required": True,
    },
    {
        "name": "inswapper_128.onnx",
        "url": "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128.onnx",
        "size_mb": 550,
        "required": True,
    },
    {
        "name": "GFPGANv1.4.pth",
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
        "size_mb": 350,
        "required": True,
    },
]

# Default models directory
DEFAULT_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def download_with_requests(url: str, output_path: str, max_retries: int = 3) -> bool:
    """Download using requests library with retry"""
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                if HAS_TQDM and total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(output_path)) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  Progress: {percent:.1f}%", end="", flush=True)
                    print()
            
            return True
            
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in 5 seconds...")
                time.sleep(5)
            else:
                return False
    
    return False


def download_with_urllib(url: str, output_path: str, max_retries: int = 3) -> bool:
    """Download using urllib with retry"""
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries}...")
            
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = (block_num * block_size / total_size) * 100
                    print(f"\r  Progress: {min(percent, 100):.1f}%", end="", flush=True)
            
            urllib.request.urlretrieve(url, output_path, reporthook=report_progress)
            print()
            return True
            
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in 5 seconds...")
                time.sleep(5)
            else:
                return False
    
    return False


def download_file(url: str, output_path: str) -> bool:
    """Download a file with retries"""
    if USE_REQUESTS:
        return download_with_requests(url, output_path)
    else:
        return download_with_urllib(url, output_path)


def verify_model(path: str, expected_size_mb: int) -> bool:
    """Verify model file exists and has reasonable size"""
    if not os.path.exists(path):
        return False
    
    size_mb = os.path.getsize(path) / (1024 * 1024)
    
    # Allow 20% variance for compressed downloads
    min_size = expected_size_mb * 0.8
    max_size = expected_size_mb * 1.2
    
    return min_size <= size_mb <= max_size


def download_models(models_dir: str = None):
    """Download all required models"""
    if models_dir is None:
        models_dir = DEFAULT_MODELS_DIR
    
    # Create models directory
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Models directory: {models_dir}")
    print("=" * 60)
    
    success_count = 0
    required_count = sum(1 for m in MODELS if m.get("required", True))
    
    for model in MODELS:
        model_path = os.path.join(models_dir, model["name"])
        is_required = model.get("required", True)
        
        # Check if already exists and valid
        if verify_model(model_path, model["size_mb"]):
            print(f"✓ {model['name']} - Already exists")
            success_count += 1
            continue
        
        print(f"\nDownloading {model['name']} (~{model['size_mb']} MB)...")
        print(f"  URL: {model['url']}")
        
        if download_file(model["url"], model_path):
            if verify_model(model_path, model["size_mb"]):
                print(f"✓ {model['name']} - Downloaded successfully")
                success_count += 1
            else:
                print(f"✗ {model['name']} - Size verification failed")
                if os.path.exists(model_path):
                    actual_size = os.path.getsize(model_path) / (1024 * 1024)
                    print(f"  Expected: ~{model['size_mb']} MB, Got: {actual_size:.1f} MB")
                    # Accept anyway if file is not empty
                    if actual_size > 10:
                        print(f"  Accepting file anyway (size > 10 MB)")
                        success_count += 1
                    else:
                        os.remove(model_path)
        else:
            print(f"✗ {model['name']} - Download failed")
    
    print("\n" + "=" * 60)
    print(f"Downloaded {success_count}/{len(MODELS)} models")
    
    # Only fail if required models are missing
    required_success = sum(1 for m in MODELS 
                          if m.get("required", True) and 
                          os.path.exists(os.path.join(models_dir, m["name"])))
    
    if required_success < required_count:
        print(f"\n✗ Missing required models ({required_success}/{required_count})")
        return False
    
    return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Deep-Live-Cam models")
    parser.add_argument(
        "--models-dir",
        default=DEFAULT_MODELS_DIR,
        help=f"Models directory (default: {DEFAULT_MODELS_DIR})"
    )
    parser.add_argument(
        "--skip-insightface",
        action="store_true",
        help="Skip InsightFace model initialization"
    )
    
    args = parser.parse_args()
    
    print("Deep-Live-Cam Model Downloader")
    print("=" * 60)
    
    # Download main models
    success = download_models(args.models_dir)
    
    if success:
        print("\n✓ All required models ready!")
        sys.exit(0)
    else:
        print("\n✗ Some required models missing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
