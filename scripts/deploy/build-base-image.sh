#!/bin/bash

set -e

cd "$(dirname "$0")/../.."

echo "====================================="
echo "Building Trinity Agent Base Image"
echo "====================================="
echo ""

docker build -t trinity-agent-base:latest -f docker/base-image/Dockerfile docker/base-image/

echo ""
echo "✅ Base image built successfully: trinity-agent-base:latest"
echo ""

