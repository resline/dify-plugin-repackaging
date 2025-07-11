# E2E Tests with Mock Server

This document explains how to run E2E tests with the mock API server.

## Overview

The mock server provides a lightweight API backend for E2E tests, allowing tests to run independently without requiring the full backend infrastructure.

## Components

1. **Mock API Server** (`e2e/mock-api-server.js`)
   - Runs on port 8000
   - Provides mock responses for all API endpoints used by the frontend
   - Supports CORS for cross-origin requests

2. **Mock Server Control Script** (`run-mock-server.sh`)
   - Manages the mock server lifecycle
   - Commands: start, stop, status, restart
   - Tracks server process with PID file

3. **Test Vite Configuration** (`vite.config.test.js`)
   - Proxies API requests to localhost:8000 instead of backend:8000
   - Used when running `npm run dev:test`

## Usage

### Method 1: Manual Server Control

1. Start the mock server:
   ```bash
   npm run mock:start
   # or
   ./run-mock-server.sh start
   ```

2. In a separate terminal, run the frontend with test config:
   ```bash
   npm run dev:test
   ```

3. In another terminal, run E2E tests:
   ```bash
   npm run test:e2e
   ```

4. Stop the mock server when done:
   ```bash
   npm run mock:stop
   # or
   ./run-mock-server.sh stop
   ```

### Method 2: Automated Test Running

Use the all-in-one script that handles server lifecycle:

```bash
./run-e2e-with-mock.sh
```

This script will:
1. Start the mock server
2. Run the E2E tests
3. Stop the mock server (even if tests fail)

You can pass additional playwright arguments:
```bash
./run-e2e-with-mock.sh --headed
./run-e2e-with-mock.sh --project=chromium
```

### Method 3: Using npm scripts

The playwright config is set up to automatically start the dev server with test config:

```bash
npm run test:e2e
```

This will:
1. Start vite dev server with test config (which proxies to localhost:8000)
2. Run playwright tests
3. Stop the dev server

**Note**: You still need to start the mock server separately:
```bash
npm run mock:start
npm run test:e2e
npm run mock:stop
```

## Mock Server Management

Check server status:
```bash
npm run mock:status
# or
./run-mock-server.sh status
```

Restart the server:
```bash
npm run mock:restart
# or
./run-mock-server.sh restart
```

## Mock API Endpoints

The mock server provides the following endpoints:

- `GET /api/v1/health` - Health check endpoint
- `GET /api/v1/tasks` - List tasks (returns empty array)
- `GET /api/v1/tasks/completed` - List completed tasks
- `GET /api/v1/files` - List files
- `GET /api/v1/marketplace/plugins` - List marketplace plugins

All endpoints return appropriate JSON responses with CORS headers enabled.

## Troubleshooting

1. **Port 8000 already in use**
   - Check if another process is using port 8000
   - Stop the mock server: `npm run mock:stop`
   - Kill any stale processes: `lsof -ti:8000 | xargs kill -9`

2. **Mock server not responding**
   - Check server status: `npm run mock:status`
   - Check logs: The mock server outputs to console
   - Restart the server: `npm run mock:restart`

3. **E2E tests can't connect to frontend**
   - Ensure you're using `npm run dev:test` (not `npm run dev`)
   - Check that vite is running on port 3000
   - Verify the mock server is running on port 8000

## CI/CD Integration

For CI environments, you can use the automated script:

```yaml
- name: Run E2E tests with mock
  run: |
    cd frontend
    npm ci
    ./run-e2e-with-mock.sh
```

Or manage the servers separately:

```yaml
- name: Start mock server
  run: |
    cd frontend
    npm run mock:start
    
- name: Run E2E tests
  run: |
    cd frontend
    npm run test:e2e
    
- name: Stop mock server
  if: always()
  run: |
    cd frontend
    npm run mock:stop
```