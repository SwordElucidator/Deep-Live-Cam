#!/usr/bin/env python3
"""
RunPod Serverless Deployment Script

Deploy the Deep-Live-Cam Video Face Swap API to RunPod.

Usage:
    python deploy_runpod.py --docker-image <image_name>

Requirements:
    pip install runpod requests
"""

import os
import sys
import argparse
import json
import time
import requests

# RunPod API Base URL
RUNPOD_API_BASE = "https://api.runpod.io/graphql"


def get_api_key() -> str:
    """Get RunPod API key from environment or prompt"""
    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        print("❌ RUNPOD_API_KEY environment variable not set")
        sys.exit(1)
    return api_key


def graphql_request(api_key: str, query: str, variables: dict = None) -> dict:
    """Make a GraphQL request to RunPod API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(RUNPOD_API_BASE, json=payload, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    if "errors" in result:
        print(f"❌ GraphQL Error: {result['errors']}")
        sys.exit(1)
    
    return result.get("data", {})


def get_gpu_types(api_key: str) -> list:
    """Get available GPU types"""
    query = """
    query GpuTypes {
        gpuTypes {
            id
            displayName
            memoryInGb
        }
    }
    """
    data = graphql_request(api_key, query)
    return data.get("gpuTypes", [])


def create_template(api_key: str, docker_image: str, template_name: str) -> str:
    """Create a new template for the serverless endpoint"""
    query = """
    mutation CreateTemplate($input: PodTemplateInput!) {
        saveTemplate(input: $input) {
            id
            name
        }
    }
    """
    
    variables = {
        "input": {
            "name": template_name,
            "imageName": docker_image,
            "dockerArgs": "",
            "containerDiskInGb": 30,
            "volumeInGb": 50,
            "env": [
                {"key": "MODELS_DIR", "value": "/app/models"},
                {"key": "EXECUTION_PROVIDER", "value": "cuda"},
                {"key": "EXECUTION_THREADS", "value": "8"},
                {"key": "MAX_VIDEO_DURATION", "value": "600"},
                {"key": "MAX_VIDEO_SIZE_MB", "value": "2048"},
                {"key": "LOG_LEVEL", "value": "INFO"},
                {"key": "AWS_DEFAULT_REGION", "value": "us-east-1"},
                {"key": "AWS_ACCESS_KEY_ID", "value": "{{ RUNPOD_SECRET_AWS_ACCESS_KEY_ID }}"},
                {"key": "AWS_SECRET_ACCESS_KEY", "value": "{{ RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY }}"},
            ],
            "isServerless": True,
        }
    }
    
    data = graphql_request(api_key, query, variables)
    template = data.get("saveTemplate", {})
    return template.get("id")


def create_endpoint(
    api_key: str,
    name: str,
    template_id: str = None,
    docker_image: str = None,
    gpu_ids: str = "AMPERE_16",  # Default: A10G or similar
    workers_min: int = 0,
    workers_max: int = 3,
    idle_timeout: int = 60,
    flash_boot: bool = True,
) -> dict:
    """Create a serverless endpoint"""
    
    query = """
    mutation CreateEndpoint($input: EndpointInput!) {
        saveEndpoint(input: $input) {
            id
            name
            templateId
            gpuIds
            workersMin
            workersMax
            idleTimeout
            flashboot
        }
    }
    """
    
    variables = {
        "input": {
            "name": name,
            "gpuIds": gpu_ids,
            "workersMin": workers_min,
            "workersMax": workers_max,
            "idleTimeout": idle_timeout,
            "flashboot": flash_boot,
            "scalerType": "QUEUE_DELAY",
            "scalerValue": 4,
        }
    }
    
    # Use template if provided, otherwise use docker image directly
    if template_id:
        variables["input"]["templateId"] = template_id
    elif docker_image:
        # Create inline template
        variables["input"]["template"] = {
            "imageName": docker_image,
            "containerDiskInGb": 30,
            "volumeInGb": 50,
            "env": [
                {"key": "MODELS_DIR", "value": "/app/models"},
                {"key": "EXECUTION_PROVIDER", "value": "cuda"},
                {"key": "EXECUTION_THREADS", "value": "8"},
                {"key": "MAX_VIDEO_DURATION", "value": "600"},
                {"key": "MAX_VIDEO_SIZE_MB", "value": "2048"},
                {"key": "LOG_LEVEL", "value": "INFO"},
                {"key": "AWS_DEFAULT_REGION", "value": "us-east-1"},
                {"key": "AWS_ACCESS_KEY_ID", "value": "{{ RUNPOD_SECRET_AWS_ACCESS_KEY_ID }}"},
                {"key": "AWS_SECRET_ACCESS_KEY", "value": "{{ RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY }}"},
            ],
        }
    
    data = graphql_request(api_key, query, variables)
    return data.get("saveEndpoint", {})


def list_endpoints(api_key: str) -> list:
    """List all serverless endpoints"""
    query = """
    query Endpoints {
        myself {
            serverlessDiscount
            endpoints {
                id
                name
                templateId
                gpuIds
                workersMin
                workersMax
                idleTimeout
                flashboot
            }
        }
    }
    """
    data = graphql_request(api_key, query)
    return data.get("myself", {}).get("endpoints", [])


def get_endpoint_status(api_key: str, endpoint_id: str) -> dict:
    """Get endpoint status"""
    query = """
    query Endpoint($endpointId: String!) {
        endpoint(id: $endpointId) {
            id
            name
            workersMin
            workersMax
            workers {
                id
                status
            }
            jobs {
                id
                status
            }
        }
    }
    """
    variables = {"endpointId": endpoint_id}
    data = graphql_request(api_key, query, variables)
    return data.get("endpoint", {})


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Deep-Live-Cam to RunPod Serverless"
    )
    parser.add_argument(
        "--docker-image", "-i",
        default=None,
        help="Docker image name (e.g., username/deep-live-cam-api:latest)"
    )
    parser.add_argument(
        "--name", "-n",
        default="deep-live-cam-video-swap",
        help="Endpoint name"
    )
    parser.add_argument(
        "--gpu",
        default="AMPERE_16",
        help="GPU type ID (default: AMPERE_16 for A10G)"
    )
    parser.add_argument(
        "--min-workers",
        type=int,
        default=0,
        help="Minimum workers (default: 0)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum workers (default: 3)"
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=60,
        help="Idle timeout in seconds (default: 60)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing endpoints"
    )
    parser.add_argument(
        "--list-gpus",
        action="store_true",
        help="List available GPU types"
    )
    
    args = parser.parse_args()
    api_key = get_api_key()
    
    # List GPUs
    if args.list_gpus:
        print("\n📊 Available GPU Types:\n")
        gpus = get_gpu_types(api_key)
        for gpu in gpus:
            print(f"  {gpu['id']:20} | {gpu['displayName']:30} | {gpu['memoryInGb']}GB VRAM")
        return
    
    # List endpoints
    if args.list:
        print("\n📋 Your Serverless Endpoints:\n")
        endpoints = list_endpoints(api_key)
        if not endpoints:
            print("  No endpoints found")
        else:
            for ep in endpoints:
                print(f"  ID: {ep['id']}")
                print(f"  Name: {ep['name']}")
                print(f"  GPU: {ep['gpuIds']}")
                print(f"  Workers: {ep['workersMin']} - {ep['workersMax']}")
                print(f"  Flash Boot: {ep['flashboot']}")
                print()
        return
    
    # Create endpoint - requires docker image
    if not args.docker_image:
        print("❌ --docker-image is required for deployment")
        print("   Example: python deploy_runpod.py -i username/deep-live-cam-api:latest")
        sys.exit(1)
    
    print("=" * 60)
    print("🚀 Deep-Live-Cam RunPod Deployment")
    print("=" * 60)
    print()
    print(f"📦 Docker Image: {args.docker_image}")
    print(f"📛 Endpoint Name: {args.name}")
    print(f"🖥️  GPU Type: {args.gpu}")
    print(f"👷 Workers: {args.min_workers} - {args.max_workers}")
    print(f"⏱️  Idle Timeout: {args.idle_timeout}s")
    print()
    
    # Confirm
    confirm = input("Continue with deployment? [y/N]: ")
    if confirm.lower() != 'y':
        print("Deployment cancelled")
        return
    
    print()
    print("🔧 Creating serverless endpoint...")
    
    endpoint = create_endpoint(
        api_key=api_key,
        name=args.name,
        docker_image=args.docker_image,
        gpu_ids=args.gpu,
        workers_min=args.min_workers,
        workers_max=args.max_workers,
        idle_timeout=args.idle_timeout,
        flash_boot=True,
    )
    
    if endpoint:
        print()
        print("✅ Endpoint created successfully!")
        print()
        print("=" * 60)
        print("📋 Endpoint Details")
        print("=" * 60)
        print(f"  ID: {endpoint.get('id')}")
        print(f"  Name: {endpoint.get('name')}")
        print(f"  GPU: {endpoint.get('gpuIds')}")
        print()
        print("🔗 API Endpoints:")
        endpoint_id = endpoint.get('id')
        print(f"  Run:    https://api.runpod.ai/v2/{endpoint_id}/run")
        print(f"  RunSync: https://api.runpod.ai/v2/{endpoint_id}/runsync")
        print(f"  Status: https://api.runpod.ai/v2/{endpoint_id}/status/<job_id>")
        print()
        print("📝 Example request:")
        print("""
curl -X POST https://api.runpod.ai/v2/{endpoint_id}/run \\
  -H "Authorization: Bearer $RUNPOD_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "input": {{
      "operation": "swap_video",
      "job_id": "test-001",
      "source_image": {{
        "bucket": "your-bucket",
        "key": "source-face.jpg"
      }},
      "target_video": {{
        "bucket": "your-bucket",
        "key": "target-video.mp4"
      }},
      "output": {{
        "bucket": "your-bucket",
        "key": "output/result.mp4"
      }}
    }}
  }}'
""".format(endpoint_id=endpoint_id))
    else:
        print("❌ Failed to create endpoint")


if __name__ == "__main__":
    main()
