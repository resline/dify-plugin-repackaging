#!/bin/bash

echo "Running API tests..."
echo "==================="

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Error: Backend server is not running on port 8000"
    echo "Please start the server first with: uvicorn app.main:app --reload"
    exit 1
fi

echo "Server is running. Testing endpoints..."
echo

# Run simple API test
python3 test_simple_api.py

echo
echo "Testing marketplace debug endpoint..."
curl -s http://localhost:8000/api/v1/marketplace/debug | python3 -m json.tool

echo
echo "Testing circuit breaker status..."
curl -s http://localhost:8000/api/v1/marketplace/status | python3 -m json.tool

echo
echo "Tests complete!"