#!/usr/bin/env python3
"""
RunPod Serverless Deployment Script (using runpod SDK)

Deploy the Deep-Live-Cam Video Face Swap API to RunPod.

Usage:
    python deploy.py create --image <docker_image>
    python deploy.py list
    python deploy.py status <endpoint_id>
    python deploy.py test <endpoint_id>
"""

import os
import sys
import argparse
import json
import time

try:
    import runpod
except ImportError:
    print("❌ Please install runpod: pip install runpod")
    sys.exit(1)


def setup_api_key():
    """Setup RunPod API key"""
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        print("❌ RUNPOD_API_KEY environment variable not set")
        sys.exit(1)
    runpod.api_key = api_key
    return api_key


def list_endpoints():
    """List all serverless endpoints"""
    print("\n📋 Your Serverless Endpoints:\n")
    
    endpoints = runpod.get_endpoints()
    
    if not endpoints:
        print("  No endpoints found")
        return
    
    for ep in endpoints:
        print(f"  ID: {ep.endpoint_id}")
        print(f"  URL: https://api.runpod.ai/v2/{ep.endpoint_id}/run")
        print()


def create_endpoint(docker_image: str, name: str = "deep-live-cam-video-swap"):
    """Create a new serverless endpoint"""
    print("=" * 60)
    print("🚀 Deep-Live-Cam RunPod Deployment")
    print("=" * 60)
    print()
    print(f"📦 Docker Image: {docker_image}")
    print(f"📛 Endpoint Name: {name}")
    print()
    
    # RunPod requires creating endpoint via web console or GraphQL
    # The SDK doesn't have direct endpoint creation
    print("⚠️  Note: RunPod endpoint creation requires the web console")
    print()
    print("📝 Please follow these steps:")
    print()
    print("1. Go to https://www.runpod.io/console/serverless")
    print()
    print("2. Click 'New Endpoint'")
    print()
    print("3. Configure:")
    print(f"   - Name: {name}")
    print(f"   - Docker Image: {docker_image}")
    print("   - GPU: RTX 4090 (24GB) or L4 (24GB) recommended")
    print("   - Min Workers: 0")
    print("   - Max Workers: 3")
    print("   - Idle Timeout: 60s")
    print("   - Container Disk: 30GB")
    print("   - Volume Disk: 50GB")
    print()
    print("4. Add Environment Variables:")
    print("   - MODELS_DIR = /app/models")
    print("   - EXECUTION_PROVIDER = cuda")
    print("   - EXECUTION_THREADS = 8")
    print("   - AWS_DEFAULT_REGION = us-east-1")
    print("   - AWS_ACCESS_KEY_ID = {{ RUNPOD_SECRET_AWS_ACCESS_KEY_ID }}")
    print("   - AWS_SECRET_ACCESS_KEY = {{ RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY }}")
    print()
    print("5. ⚠️  Before deploying, add RunPod Secrets:")
    print("   Go to: https://www.runpod.io/console/user/secrets")
    print("   - AWS_ACCESS_KEY_ID: <your aws key>")
    print("   - AWS_SECRET_ACCESS_KEY: <your aws secret>")
    print()
    print("6. Click 'Create Endpoint'")
    print()


def test_endpoint(endpoint_id: str):
    """Test an endpoint with a health check"""
    print(f"\n🧪 Testing endpoint: {endpoint_id}\n")
    
    endpoint = runpod.Endpoint(endpoint_id)
    
    # Send health check request
    test_input = {
        "operation": "health",
        "job_id": "health-check-test"
    }
    
    print("📤 Sending health check request...")
    
    try:
        run_request = endpoint.run(test_input)
        print(f"   Job ID: {run_request.job_id}")
        print(f"   Status: {run_request.status()}")
        
        # Wait for result
        print("\n⏳ Waiting for result (timeout: 120s)...")
        result = run_request.output(timeout=120)
        
        print("\n✅ Response received:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def run_job(endpoint_id: str, input_data: dict):
    """Run a job on the endpoint"""
    endpoint = runpod.Endpoint(endpoint_id)
    
    print(f"\n📤 Sending job to endpoint: {endpoint_id}")
    print(f"   Input: {json.dumps(input_data, indent=2)}")
    
    run_request = endpoint.run(input_data)
    job_id = run_request.job_id
    
    print(f"\n✅ Job submitted: {job_id}")
    print(f"   Status URL: https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}")
    
    return job_id


def check_status(endpoint_id: str, job_id: str):
    """Check job status"""
    endpoint = runpod.Endpoint(endpoint_id)
    
    # Get job status
    status = endpoint.status(job_id)
    print(f"\n📊 Job Status: {job_id}")
    print(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Deep-Live-Cam to RunPod Serverless"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List endpoints")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create endpoint (shows instructions)")
    create_parser.add_argument(
        "--image", "-i",
        required=True,
        help="Docker image name"
    )
    create_parser.add_argument(
        "--name", "-n",
        default="deep-live-cam-video-swap",
        help="Endpoint name"
    )
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test endpoint")
    test_parser.add_argument("endpoint_id", help="Endpoint ID")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a job")
    run_parser.add_argument("endpoint_id", help="Endpoint ID")
    run_parser.add_argument("--input", "-i", required=True, help="Input JSON file or string")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("endpoint_id", help="Endpoint ID")
    status_parser.add_argument("job_id", help="Job ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    setup_api_key()
    
    if args.command == "list":
        list_endpoints()
    
    elif args.command == "create":
        create_endpoint(args.image, args.name)
    
    elif args.command == "test":
        test_endpoint(args.endpoint_id)
    
    elif args.command == "run":
        # Parse input
        if os.path.isfile(args.input):
            with open(args.input) as f:
                input_data = json.load(f)
        else:
            input_data = json.loads(args.input)
        run_job(args.endpoint_id, input_data)
    
    elif args.command == "status":
        check_status(args.endpoint_id, args.job_id)


if __name__ == "__main__":
    main()
