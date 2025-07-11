# E2E Tests for Dify Plugin Repackaging

This directory contains comprehensive end-to-end tests for the Dify Plugin Repackaging application using Playwright.

## Test Structure

```
e2e/
├── fixtures/           # Test fixtures and constants
├── pages/             # Page Object Models
├── utils/             # Helper utilities
├── tests/             # Test specifications
│   ├── 01-basic-navigation.spec.ts    # Navigation and UI tests
│   ├── 02-url-submission.spec.ts      # URL submission workflow
│   ├── 03-marketplace-workflow.spec.ts # Marketplace functionality
│   ├── 04-file-upload.spec.ts         # File upload tests
│   ├── 05-websocket-realtime.spec.ts  # WebSocket real-time updates
│   ├── 06-file-download.spec.ts       # Download functionality
│   ├── 07-error-recovery.spec.ts      # Error handling and recovery
│   └── 08-visual-regression.spec.ts   # Visual regression tests
├── test-data/         # Test files (generated)
├── downloads/         # Downloaded files (generated)
└── screenshots/       # Screenshots (generated)
```

## Running Tests

### Prerequisites

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install
   ```

3. Ensure the application is running:
   ```bash
   npm run dev
   ```

### Running All Tests

```bash
# Run all tests in headless mode
npm run test:e2e

# Run tests with UI mode (recommended for development)
npm run test:e2e:ui

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# Debug tests
npm run test:e2e:debug
```

### Running Specific Tests

```bash
# Run a specific test file
npx playwright test e2e/tests/02-url-submission.spec.ts

# Run tests matching a pattern
npx playwright test -g "should submit URL successfully"

# Run tests for a specific browser
npx playwright test --project=chromium
```

### Visual Regression Tests

```bash
# Update visual snapshots
npm run test:e2e:update-snapshots

# Run visual tests only
npx playwright test e2e/tests/08-visual-regression.spec.ts
```

## Test Reports

After running tests, view the HTML report:

```bash
npm run test:e2e:report
```

## Configuration

The tests are configured in `playwright.config.ts`:

- **Base URL**: Default is `http://localhost:3000`
- **Browsers**: Chrome, Firefox, Safari, and mobile viewports
- **Parallel execution**: Enabled by default
- **Retries**: 2 retries on CI, 0 locally
- **Timeouts**: 30s navigation, 10s actions

### Environment Variables

```bash
# Custom base URL
PLAYWRIGHT_BASE_URL=http://localhost:8080 npm run test:e2e

# Run in CI mode
CI=true npm run test:e2e
```

## Writing Tests

### Page Object Model

Use the Page Object Models for consistent interactions:

```typescript
import { test, expect } from '../fixtures/test-fixtures';

test('example test', async ({ homePage, taskStatusPage }) => {
  // Use page objects
  await homePage.submitUrl('https://example.com/plugin.difypkg');
  await taskStatusPage.waitForTaskCompletion();
});
```

### WebSocket Testing

Use the WebSocket helper for real-time testing:

```typescript
test('websocket test', async ({ wsHelper }) => {
  await wsHelper.waitForConnection();
  await wsHelper.waitForTaskStatus('completed');
});
```

### Test Data

Use the TEST_DATA constants for consistent test data:

```typescript
import { TEST_DATA } from '../fixtures/test-fixtures';

await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
```

## Best Practices

1. **Use Page Objects**: Always use page objects instead of direct selectors
2. **Wait for Elements**: Use proper waits instead of arbitrary timeouts
3. **Test Isolation**: Each test should be independent
4. **Meaningful Names**: Use descriptive test and variable names
5. **Error Messages**: Include helpful error messages in assertions
6. **Clean Up**: Clean up test data after tests

## Debugging

### Debug a Single Test

```bash
# Using VS Code debugger
npx playwright test --debug e2e/tests/02-url-submission.spec.ts
```

### View Browser Console

Console logs are captured automatically. Check the test report for logs.

### Take Screenshots

```typescript
await page.screenshot({ path: 'debug-screenshot.png' });
```

### Trace Viewer

Traces are captured on test failure. View them with:

```bash
npx playwright show-trace trace.zip
```

## CI/CD Integration

The tests are configured to run in CI environments:

```yaml
# Example GitHub Actions
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npm run test:e2e
  env:
    CI: true

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Troubleshooting

### Tests Failing Locally

1. Ensure the dev server is running: `npm run dev`
2. Clear test data: `rm -rf e2e/test-data e2e/downloads`
3. Update browsers: `npx playwright install`

### WebSocket Tests Failing

1. Check if WebSocket server is running
2. Verify WebSocket URL in browser DevTools
3. Check for CORS issues

### Visual Tests Failing

1. Update snapshots if UI changed: `npm run test:e2e:update-snapshots`
2. Check for OS-specific rendering differences
3. Ensure consistent viewport sizes

## Contributing

When adding new tests:

1. Follow the existing file naming convention
2. Add page objects for new pages
3. Update this README with new test descriptions
4. Ensure tests pass on all browsers
5. Add appropriate test data cleanup