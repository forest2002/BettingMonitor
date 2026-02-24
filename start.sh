#!/bin/bash

echo "======================================"
echo "Each-Way Tracker - Quick Start"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your credentials:"
    echo "   - PROFIT_MAXIMISER_EMAIL"
    echo "   - PROFIT_MAXIMISER_PASSWORD"
    echo ""
    read -p "Press Enter after you've updated .env..."
fi

echo "Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "======================================"
echo "Services Started!"
echo "======================================"
echo ""
echo "Frontend:       http://localhost:3000"
echo "API Docs:       http://localhost:8000/docs"
echo "Health Check:   http://localhost:8000/status/health"
echo ""
echo "View logs with:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services with:"
echo "  docker-compose down"
echo ""
echo "======================================"
