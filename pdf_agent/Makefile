.PHONY: help build up down logs restart shell clean setup status build-prod push test

# Default target
help:
	@echo ""
	@echo "PDF Agent Docker Makefile"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "  make setup           - Setup environment file from example"
	@echo "  make build           - Build the Docker image"
	@echo "  make up              - Start the application"
	@echo "  make down            - Stop the application"
	@echo "  make restart         - Restart the application"
	@echo "  make logs            - View application logs (Ctrl+C to exit)"
	@echo "  make shell           - Open a shell in the running container"
	@echo "  make status          - Check container status"
	@echo "  make clean           - Remove containers and volumes"
	@echo ""
	@echo "  make verify          - Run Docker setup verification"
	@echo "  make test            - Test the Docker build"
	@echo ""
	@echo "  make build-prod      - Build optimized production image"
	@echo "  make push            - Push image to registry"
	@echo ""
	@echo "Example usage:"
	@echo "  make setup && make build && make up"
	@echo ""

# Setup environment
setup:
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "✓ .env created. Edit it and add your GROQ_API_KEY"; \
	else \
		echo ".env file already exists"; \
	fi

# Build Docker image
build:
	@echo "Building Docker image..."
	docker-compose build
	@echo "✓ Build complete"

# Start application
up:
	@echo "Starting PDF Agent..."
	docker-compose up -d
	@sleep 3
	@echo ""
	@echo "✓ PDF Agent is running at http://localhost:8501"
	@echo "  Use 'make logs' to view logs"

# Stop application
down:
	@echo "Stopping PDF Agent..."
	docker-compose down
	@echo "✓ Stopped"

# View logs
logs:
	@echo "Showing application logs (Ctrl+C to exit)..."
	docker-compose logs -f pdf-agent

# Restart application
restart:
	@echo "Restarting PDF Agent..."
	docker-compose restart pdf-agent
	@echo "✓ Restarted"

# Open shell in container
shell:
	@echo "Opening shell in container..."
	docker-compose exec pdf-agent /bin/bash

# Check status
status:
	@echo "Checking container status..."
	docker-compose ps

# Clean up
clean:
	@echo "Cleaning up Docker resources..."
	@echo "This will remove containers and volumes."
	@read -p "Continue? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "✓ Cleaned"; \
	else \
		echo "Cancelled"; \
	fi

# Verify setup
verify:
	@echo "Running Docker setup verification..."
	python verify-docker-setup.py

# Test the build
test: build
	@echo "Testing Docker image..."
	docker-compose run --rm pdf-agent python -c "import streamlit; print('✓ Streamlit imported successfully')"
	@echo "✓ Test complete"

# Build production image
build-prod:
	@echo "Building production image..."
	docker build -f Dockerfile -t pdf-agent:prod .
	@echo "✓ Production build complete"

# Push to registry
push:
	@echo "Pushing image to registry..."
	@read -p "Enter registry (e.g., docker.io/username): " registry; \
	docker tag pdf-agent:latest $$registry/pdf-agent:latest; \
	docker push $$registry/pdf-agent:latest; \
	echo "✓ Pushed to $$registry"

# Full development workflow
dev: setup build verify up
	@echo ""
	@echo "✓ Development environment ready!"
	@echo "  App: http://localhost:8501"
	@echo "  Logs: make logs"
	@echo "  Stop: make down"
