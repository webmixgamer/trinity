#!/bin/bash

set -e

cd "$(dirname "$0")/../.."

echo "====================================="
echo "Trinity Agent Platform - Starting"
echo "====================================="
echo ""

if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file. Please update with your configuration."
    echo ""
fi

echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

echo ""
echo "====================================="
echo "Trinity Agent Platform - Ready!"
echo "====================================="
echo ""
echo "Access points:"
echo "  - Web UI:       http://localhost:3000 (login: admin/password)"
echo "  - Backend API:  http://localhost:8000/docs"
echo "  - Audit Logger: http://localhost:8001/docs"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""

