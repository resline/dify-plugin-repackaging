#!/bin/bash

# Script to run the mock API server for E2E tests

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PID file to track the server process
PID_FILE="/tmp/mock-api-server.pid"

# Function to start the mock server
start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}Mock server is already running with PID $PID${NC}"
            return 1
        else
            rm "$PID_FILE"
        fi
    fi

    echo -e "${GREEN}Starting mock API server on port 8000...${NC}"
    
    # Start the mock server in the background
    node e2e/mock-api-server.js &
    PID=$!
    
    # Save the PID
    echo $PID > "$PID_FILE"
    
    # Wait a moment for the server to start
    sleep 2
    
    # Check if the server is running
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}Mock server started successfully with PID $PID${NC}"
        echo -e "${GREEN}Server running at: http://localhost:8000${NC}"
        return 0
    else
        echo -e "${RED}Failed to start mock server${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the mock server
stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping mock server with PID $PID...${NC}"
            kill "$PID"
            sleep 1
            
            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID"
            fi
            
            rm -f "$PID_FILE"
            echo -e "${GREEN}Mock server stopped${NC}"
        else
            echo -e "${YELLOW}Mock server is not running (stale PID file)${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}Mock server is not running${NC}"
    fi
}

# Function to check server status
status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${GREEN}Mock server is running with PID $PID${NC}"
            
            # Test the health endpoint
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health | grep -q "200"; then
                echo -e "${GREEN}Health check: OK${NC}"
            else
                echo -e "${YELLOW}Health check: Failed${NC}"
            fi
        else
            echo -e "${YELLOW}Mock server is not running (stale PID file)${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}Mock server is not running${NC}"
    fi
}

# Function to restart the server
restart_server() {
    echo -e "${YELLOW}Restarting mock server...${NC}"
    stop_server
    sleep 1
    start_server
}

# Main script logic
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        status_server
        ;;
    restart)
        restart_server
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        echo ""
        echo "  start   - Start the mock API server on port 8000"
        echo "  stop    - Stop the mock API server"
        echo "  status  - Check if the mock API server is running"
        echo "  restart - Restart the mock API server"
        echo ""
        echo "Example:"
        echo "  $0 start   # Start the server"
        echo "  $0 status  # Check server status"
        echo "  $0 stop    # Stop the server"
        exit 1
        ;;
esac

exit 0