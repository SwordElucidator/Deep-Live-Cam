#!/bin/bash
# =============================================================================
# Build and Push Docker Image to Docker Hub
# =============================================================================
#
# Usage:
#   ./build_and_push.sh <docker_username> [tag]
#
# Example:
#   ./build_and_push.sh myusername latest
#   ./build_and_push.sh myusername v1.0.0
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Arguments
DOCKER_USERNAME="${1:-}"
TAG="${2:-latest}"
IMAGE_NAME="deep-live-cam-api"

# Check arguments
if [ -z "$DOCKER_USERNAME" ]; then
    echo -e "${RED}❌ Error: Docker username required${NC}"
    echo ""
    echo "Usage: $0 <docker_username> [tag]"
    echo "Example: $0 myusername latest"
    exit 1
fi

FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${TAG}"

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}🐳 Deep-Live-Cam Docker Build & Push${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "📦 Image: ${GREEN}${FULL_IMAGE_NAME}${NC}"
echo ""

# Navigate to serverless directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

echo -e "${YELLOW}📁 Working directory: $(pwd)${NC}"
echo ""

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Error: Dockerfile not found${NC}"
    exit 1
fi

# Build image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
echo ""
docker build \
    --platform linux/amd64 \
    -t "${FULL_IMAGE_NAME}" \
    -f Dockerfile \
    .

echo ""
echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Login check
echo -e "${YELLOW}🔐 Checking Docker Hub login...${NC}"
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo -e "${YELLOW}Please login to Docker Hub:${NC}"
    docker login
fi
echo ""

# Push image
echo -e "${BLUE}📤 Pushing to Docker Hub...${NC}"
echo ""
docker push "${FULL_IMAGE_NAME}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ Successfully pushed: ${FULL_IMAGE_NAME}${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Set RunPod secrets in the console:"
echo -e "     - AWS_ACCESS_KEY_ID"
echo -e "     - AWS_SECRET_ACCESS_KEY"
echo ""
echo -e "  2. Deploy to RunPod:"
echo -e "     ${BLUE}export RUNPOD_API_KEY=your_api_key${NC}"
echo -e "     ${BLUE}python deploy/deploy_runpod.py -i ${FULL_IMAGE_NAME}${NC}"
echo ""
