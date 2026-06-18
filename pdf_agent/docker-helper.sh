#!/bin/bash
# Docker Helper Script for PDF Agent
# Usage: ./docker-helper.sh [command]

set -e

print_help() {
    echo ""
    echo "PDF Agent Docker Helper"
    echo "======================="
    echo "Usage: ./docker-helper.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build       - Build the Docker image"
    echo "  up          - Start the application"
    echo "  down        - Stop the application"
    echo "  logs        - View application logs"
    echo "  restart     - Restart the application"
    echo "  shell       - Open a shell in the running container"
    echo "  clean       - Remove containers and volumes"
    echo "  setup       - Setup environment file"
    echo "  status      - Check container status"
    echo ""
}

if [ $# -eq 0 ]; then
    print_help
    exit 0
fi

case "$1" in
    build)
        echo "Building Docker image..."
        docker-compose build
        ;;
    up)
        echo "Starting PDF Agent..."
        docker-compose up -d
        sleep 5
        echo ""
        echo "✓ PDF Agent is running at http://localhost:8501"
        ;;
    down)
        echo "Stopping PDF Agent..."
        docker-compose down
        echo "✓ Stopped"
        ;;
    logs)
        echo "Showing application logs (Ctrl+C to exit)..."
        docker-compose logs -f pdf-agent
        ;;
    restart)
        echo "Restarting PDF Agent..."
        docker-compose restart pdf-agent
        echo "✓ Restarted"
        ;;
    shell)
        echo "Opening shell in container..."
        docker-compose exec pdf-agent /bin/bash
        ;;
    clean)
        echo "Cleaning up Docker resources..."
        docker-compose down -v
        echo "✓ Cleaned"
        ;;
    setup)
        if [ -f .env ]; then
            echo ".env file already exists"
        else
            echo "Creating .env from example..."
            cp .env.example .env
            echo "✓ .env created. Edit it and add your GROQ_API_KEY"
        fi
        ;;
    status)
        echo "Checking container status..."
        docker-compose ps
        ;;
    *)
        echo "Unknown command: $1"
        print_help
        exit 1
        ;;
esac
