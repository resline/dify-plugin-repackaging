#!/bin/bash

# Script to run E2E tests with mock server

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting E2E tests with mock server...${NC}"

# Start the mock server
echo -e "${YELLOW}Starting mock API server...${NC}"
./run-mock-server.sh start

# Check if mock server started successfully
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start mock server${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    ./run-mock-server.sh stop
}

# Set up trap to ensure cleanup happens on script exit
trap cleanup EXIT INT TERM

# Give the server a moment to fully start
sleep 2

# Run the E2E tests
echo -e "${GREEN}Running E2E tests...${NC}"
npm run test:e2e "$@"

# Capture the test exit code
TEST_EXIT_CODE=$?

# The cleanup will happen automatically due to the trap
exit $TEST_EXIT_CODE