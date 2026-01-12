#!/usr/bin/env python3
"""
Model Download Script

Downloads required models for Deep-Live-Cam Video Face Swap API:
1. inswapper_128_fp16.onnx - Face swap model
2. GFPGANv1.4.pth - Face enhancement model
3. buffalo_l - InsightFace face analysis model (auto-downloaded)
"""

import os
import sys
import urllib.request
from pathlib import Path
from tqdm import tqdm

# Model definitions
MODELS = [
    {
        "name": "inswapper_128_fp16.onnx",
        "url": "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128_fp16.onnx",
        "size_mb": 550,
    },
    {
        "name": "inswapper_128.onnx",
        "url": "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128.onnx",
        "size_mb": 550,
    },
    {
        "name": "GFPGANv1.4.pth",
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
        "size_mb": 350,
    },
]

# Default models directory
DEFAULT_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


class DownloadProgressBar(tqdm):
    """Progress bar for downloads"""
    
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url: str, output_path: str) -> bool:
    """
    Download a file with progress bar
    
    Args:
        url: Download URL
        output_path: Local file path
        
    Returns:
        True if successful
    """
    try:
        with DownloadProgressBar(
            unit='B',
            unit_scale=True,
            miniters=1,
            desc=os.path.basename(output_path)
        ) as pbar:
            urllib.request.urlretrieve(
                url,
                output_path,
                reporthook=pbar.update_to
            )
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def verify_model(path: str, expected_size_mb: int) -> bool:
    """
    Verify model file exists and has reasonable size
    
    Args:
        path: Model file path
        expected_size_mb: Expected size in MB
        
    Returns:
        True if valid
    """
    if not os.path.exists(path):
        return False
    
    size_mb = os.path.getsize(path) / (1024 * 1024)
    
    # Allow 10% variance
    min_size = expected_size_mb * 0.9
    max_size = expected_size_mb * 1.1
    
    return min_size <= size_mb <= max_size


def download_models(models_dir: str = None):
    """
    Download all required models
    
    Args:
        models_dir: Directory to save models
    """
    if models_dir is None:
        models_dir = DEFAULT_MODELS_DIR
    
    # Create models directory
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Models directory: {models_dir}")
    print("=" * 60)
    
    success_count = 0
    
    for model in MODELS:
        model_path = os.path.join(models_dir, model["name"])
        
        # Check if already exists and valid
        if verify_model(model_path, model["size_mb"]):
            print(f"✓ {model['name']} - Already exists")
            success_count += 1
            continue
        
        print(f"\nDownloading {model['name']} ({model['size_mb']} MB)...")
        
        if download_file(model["url"], model_path):
            if verify_model(model_path, model["size_mb"]):
                print(f"✓ {model['name']} - Downloaded successfully")
                success_count += 1
            else:
                print(f"✗ {model['name']} - Download verification failed")
                os.remove(model_path)
        else:
            print(f"✗ {model['name']} - Download failed")
    
    print("\n" + "=" * 60)
    print(f"Downloaded {success_count}/{len(MODELS)} models")
    
    if success_count < len(MODELS):
        print("\nWarning: Some models failed to download.")
        print("Please download manually from the URLs above.")
        return False
    
    return True


def download_insightface_model():
    """
    Trigger InsightFace buffalo_l model download
    
    This model is auto-downloaded by insightface when first used,
    but we can trigger it here for Docker build caching.
    """
    print("\nInitializing InsightFace (buffalo_l model)...")
    
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        # This will download the model if not present
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        print("✓ InsightFace buffalo_l - Ready")
        return True
        
    except Exception as e:
        print(f"✗ InsightFace initialization failed: {e}")
        print("  The model will be downloaded on first use.")
        return False


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
    
    # Download InsightFace model
    if not args.skip_insightface:
        download_insightface_model()
    
    if success:
        print("\n✓ All models ready!")
        sys.exit(0)
    else:
        print("\n✗ Some models missing. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
