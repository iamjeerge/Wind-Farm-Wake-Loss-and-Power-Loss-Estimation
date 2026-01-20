# Makefile for Wind Wake Loss Tool
.PHONY: help start stop restart build logs clean seed test dev

# Default target
help:
	@echo "Wind Wake Loss Tool - Available Commands"
	@echo "========================================="
	@echo ""
	@echo "Docker Commands:"
	@echo "  make start     - Start all services (builds if needed)"
	@echo "  make stop      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make build     - Rebuild all containers"
	@echo "  make logs      - View container logs"
	@echo "  make clean     - Stop and remove all containers, volumes"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev       - Start in development mode (hot reload)"
	@echo "  make test      - Run backend tests"
	@echo "  make seed      - Seed database with fixtures"
	@echo "  make shell     - Open shell in backend container"
	@echo ""

# Start all services
start:
	@echo "🚀 Starting Wind Wake Loss Tool..."
	docker compose up -d
	@echo "✅ Services started!"
	@echo "   Frontend: http://localhost"
	@echo "   API Docs: http://localhost:8000/api/docs"

# Stop all services
stop:
	@echo "🛑 Stopping services..."
	docker compose down
	@echo "✅ Services stopped"

# Restart services
restart: stop start

# Build containers
build:
	@echo "🔨 Building containers..."
	docker compose build --no-cache
	@echo "✅ Build complete"

# View logs
logs:
	docker compose logs -f

# View specific service logs
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-db:
	docker compose logs -f db

# Clean everything
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete"

# Development mode with hot reload
dev:
	@echo "🔧 Starting in development mode..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run tests
test:
	@echo "🧪 Running tests..."
	docker compose exec backend pytest -v --cov=app

# Seed database
seed:
	@echo "🌱 Seeding database..."
	docker compose exec backend python -m app.db.fixtures
	@echo "✅ Database seeded"

# Open shell in backend container
shell:
	docker compose exec backend /bin/bash

# Database shell
db-shell:
	docker compose exec db psql -U windwake -d windwake

# Check health
health:
	@echo "Checking service health..."
	@curl -sf http://localhost:8000/health && echo "✅ Backend: Healthy" || echo "❌ Backend: Unhealthy"
	@curl -sf http://localhost/ > /dev/null && echo "✅ Frontend: Healthy" || echo "❌ Frontend: Unhealthy"
