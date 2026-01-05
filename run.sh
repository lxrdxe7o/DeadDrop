#!/bin/bash

# DeadDrop Local Development Runner
# Usage: ./run.sh [option]
# Options:
#   start   - Start all services (default)
#   stop    - Stop all services
#   restart - Restart all services
#   logs    - Show logs from all services
#   status  - Show service status

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[DeadDrop]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_dependencies() {
    local missing_deps=0
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        missing_deps=1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        missing_deps=1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        missing_deps=1
    fi
    
    if [ $missing_deps -eq 1 ]; then
        exit 1
    fi
}

start_backend() {
    print_status "Starting backend services (Redis + API)..."
    docker-compose up -d
    
    # Wait for backend to be ready
    print_status "Waiting for backend to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            print_success "Backend is ready!"
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_warning "Backend may not be fully ready, check logs with: docker-compose logs -f"
    fi
}

start_frontend() {
    print_status "Starting frontend development server..."
    cd "$PROJECT_DIR/src/web"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    
    # Start Vite dev server
    print_success "Starting Vite dev server on http://localhost:3000"
    npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PROJECT_DIR/.frontend.pid"
}

stop_services() {
    print_status "Stopping all services..."
    
    # Stop frontend if running
    if [ -f "$PROJECT_DIR/.frontend.pid" ]; then
        local frontend_pid=$(cat "$PROJECT_DIR/.frontend.pid")
        if kill -0 $frontend_pid 2>/dev/null; then
            kill $frontend_pid
            print_success "Frontend server stopped"
        fi
        rm -f "$PROJECT_DIR/.frontend.pid"
    fi
    
    # Kill any npm/vite processes related to this project
    pkill -f "vite.*DeadDrop" 2>/dev/null || true
    
    # Stop backend
    cd "$PROJECT_DIR"
    docker-compose down
    print_success "Backend services stopped"
}

show_status() {
    print_status "Service Status:"
    echo ""
    
    # Check Docker services
    echo -e "${BLUE}Docker Services:${NC}"
    docker-compose ps
    echo ""
    
    # Check frontend
    echo -e "${BLUE}Frontend:${NC}"
    if [ -f "$PROJECT_DIR/.frontend.pid" ]; then
        local frontend_pid=$(cat "$PROJECT_DIR/.frontend.pid")
        if kill -0 $frontend_pid 2>/dev/null; then
            print_success "Running (PID: $frontend_pid)"
        else
            print_warning "Not running (stale PID file)"
        fi
    else
        print_warning "Not running"
    fi
    echo ""
    
    # Check endpoints
    echo -e "${BLUE}Endpoints:${NC}"
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        print_success "Backend API: http://localhost:8000/api/docs"
    else
        print_warning "Backend API: Not responding"
    fi
    
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend: http://localhost:3000"
    else
        print_warning "Frontend: Not responding"
    fi
}

show_logs() {
    print_status "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

case "${1:-start}" in
    start)
        check_dependencies
        print_status "Starting DeadDrop local development environment..."
        echo ""
        start_backend
        start_frontend
        echo ""
        print_success "DeadDrop is running!"
        echo -e "  ${BLUE}Frontend:${NC} http://localhost:3000"
        echo -e "  ${BLUE}Backend API:${NC} http://localhost:8000/api/docs"
        echo ""
        print_status "Press Ctrl+C to stop the frontend dev server"
        wait $FRONTEND_PID
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        check_dependencies
        start_backend
        start_frontend
        echo ""
        print_success "DeadDrop restarted!"
        wait $FRONTEND_PID
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status}"
        exit 1
        ;;
esac
