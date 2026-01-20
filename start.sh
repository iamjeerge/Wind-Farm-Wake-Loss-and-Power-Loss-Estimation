#!/bin/bash
# Wind Wake Loss Tool - Quick Start Script
# Run this script to start the entire application with one command

set -e

echo "🌬️ Wind Wake Loss & Power Loss Estimation Tool"
echo "================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
fi

# Build and start containers
echo "🔨 Building and starting containers..."
echo ""

docker compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."

# Wait for backend to be healthy
RETRIES=30
until docker compose exec backend curl -sf http://localhost:8000/health > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "   Waiting for backend... ($RETRIES attempts remaining)"
    sleep 2
    RETRIES=$((RETRIES-1))
done

if [ $RETRIES -eq 0 ]; then
    echo "❌ Backend failed to start. Check logs with: docker compose logs backend"
    exit 1
fi

echo ""
echo "✅ All services are running!"
echo ""
echo "================================================"
echo "🌐 Application URLs:"
echo "   - Frontend:    http://localhost"
echo "   - API Docs:    http://localhost:8000/api/docs"
echo "   - Health:      http://localhost:8000/health"
echo ""
echo "📊 Database:"
echo "   - Host:        localhost:5432"
echo "   - Database:    windwake"
echo "   - User:        windwake"
echo ""
echo "🛠️  Useful commands:"
echo "   - View logs:   docker compose logs -f"
echo "   - Stop:        docker compose down"
echo "   - Restart:     docker compose restart"
echo "   - Rebuild:     docker compose up --build -d"
echo "================================================"
