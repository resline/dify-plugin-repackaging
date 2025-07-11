# Comprehensive E2E Testing Plan for Dify Plugin Repackaging Application

## Executive Summary

This document outlines a comprehensive end-to-end testing strategy for the Dify Plugin Repackaging web application using Playwright. The application allows users to repackage Dify plugins with offline dependencies through multiple input methods: URL submission, marketplace browsing, and file upload.

## 1. Application Overview

### Architecture Components
- **Frontend**: React with Tailwind CSS
- **Backend**: FastAPI (Python 3.12)
- **Task Queue**: Celery with Redis
- **WebSocket**: Real-time progress updates
- **Web Server**: Nginx
- **Containerization**: Docker Compose

### Key User Journeys
1. **URL Submission**: User provides direct URL to .difypkg file
2. **Marketplace Browsing**: User browses and selects from Dify Marketplace
3. **File Upload**: User uploads local .difypkg file
4. **Task Monitoring**: Real-time progress tracking via WebSocket
5. **File Download**: Download repackaged plugin with dependencies

## 2. E2E Test Scenarios

### 2.1 Complete User Workflows

#### 2.1.1 URL Submission Journey
```typescript
// Happy Path
- Navigate to application
- Select URL tab
- Enter valid .difypkg URL
- Select platform (optional)
- Submit form
- Monitor WebSocket progress updates
- Download completed file
- Verify file integrity

// Edge Cases
- Invalid URL format
- Non-.difypkg URL
- Unreachable URL
- Rate limit exceeded
- Network timeout during download
```

#### 2.1.2 Marketplace Journey
```typescript
// Happy Path
- Navigate to marketplace tab
- Search for plugin
- Browse plugin cards
- Select specific version
- Choose platform
- Submit repackaging
- Monitor progress
- Download result

// Edge Cases
- Empty search results
- Marketplace API unavailable
- Invalid plugin selection
- Version not found
```

#### 2.1.3 File Upload Journey
```typescript
// Happy Path
- Navigate to file upload tab
- Select valid .difypkg file
- Choose platform
- Upload file
- Monitor progress
- Download result

// Edge Cases
- Non-.difypkg file
- File size exceeds 100MB
- Upload interruption
- Corrupted file
```

### 2.2 Cross-Feature Scenarios

#### 2.2.1 Deep Link Handling
```typescript
// Test scenarios for deep link functionality
- URL deep link: ?url=https://example.com/plugin.difypkg
- Marketplace deep link: ?marketplace=langgenius/agent/0.0.9
- Auto-submission on valid deep links
- Tab switching based on deep link type
```

#### 2.2.2 Session Persistence
```typescript
// Test data persistence across sessions
- Tab selection persistence (localStorage)
- Completed files list persistence
- Theme preference persistence
- Task recovery after page reload
```

### 2.3 WebSocket Real-time Features

#### 2.3.1 Progress Updates
```typescript
// Test real-time progress monitoring
- Connection establishment
- Progress percentage updates
- Status transitions (pending → processing → completed)
- Log streaming
- Error message propagation
- Heartbeat/ping-pong mechanism
```

#### 2.3.2 Connection Resilience
```typescript
// Test WebSocket stability
- Reconnection after network interruption
- Multiple concurrent connections
- Connection cleanup on task completion
- Timeout handling
```

### 2.4 Error Recovery Scenarios

#### 2.4.1 Network Failures
```typescript
- API request failures with retry
- WebSocket disconnection recovery
- Download interruption handling
- Timeout recovery
```

#### 2.4.2 Server Errors
```typescript
- 500 Internal Server Error handling
- 429 Rate Limit response
- 503 Service Unavailable
- Invalid response formats
```

## 3. Playwright Testing Strategy

### 3.1 Page Object Model Design

```typescript
// Base Page Object
abstract class BasePage {
  constructor(protected page: Page) {}
  
  async waitForLoadComplete() {
    await this.page.waitForLoadState('networkidle');
  }
  
  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `screenshots/${name}.png`,
      fullPage: true 
    });
  }
}

// Main Application Page
class RepackagingPage extends BasePage {
  // Locators
  readonly urlTab = this.page.getByRole('tab', { name: 'URL' });
  readonly marketplaceTab = this.page.getByRole('tab', { name: 'Marketplace' });
  readonly fileTab = this.page.getByRole('tab', { name: 'File Upload' });
  readonly urlInput = this.page.getByPlaceholder('https://');
  readonly platformSelect = this.page.getByLabel('Platform');
  readonly submitButton = this.page.getByRole('button', { name: 'Start Repackaging' });
  
  // Methods
  async selectTab(tab: 'url' | 'marketplace' | 'file') {
    const tabMap = {
      url: this.urlTab,
      marketplace: this.marketplaceTab,
      file: this.fileTab
    };
    await tabMap[tab].click();
  }
  
  async submitUrlRepackaging(url: string, platform?: string) {
    await this.urlInput.fill(url);
    if (platform) {
      await this.platformSelect.selectOption(platform);
    }
    await this.submitButton.click();
  }
}

// Task Status Page
class TaskStatusPage extends BasePage {
  readonly progressBar = this.page.getByRole('progressbar');
  readonly logViewer = this.page.getByTestId('log-viewer');
  readonly downloadButton = this.page.getByRole('button', { name: /Download.*\.difypkg/ });
  readonly newTaskButton = this.page.getByRole('button', { name: 'Start New Task' });
  
  async waitForCompletion(timeout = 120000) {
    await this.downloadButton.waitFor({ 
      state: 'visible', 
      timeout 
    });
  }
  
  async getProgress(): Promise<number> {
    const value = await this.progressBar.getAttribute('aria-valuenow');
    return parseInt(value || '0');
  }
  
  async downloadFile(): Promise<Download> {
    const downloadPromise = this.page.waitForEvent('download');
    await this.downloadButton.click();
    return await downloadPromise;
  }
}

// Marketplace Browser Page
class MarketplacePage extends BasePage {
  readonly searchInput = this.page.getByPlaceholder('Search plugins');
  readonly pluginCards = this.page.getByTestId('plugin-card');
  readonly loadMoreButton = this.page.getByRole('button', { name: 'Load More' });
  
  async searchPlugin(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(500); // Debounce
  }
  
  async selectPlugin(author: string, name: string) {
    await this.page
      .getByTestId('plugin-card')
      .filter({ hasText: `${author}/${name}` })
      .click();
  }
  
  async selectVersion(version: string) {
    await this.page.getByLabel('Version').selectOption(version);
  }
}
```

### 3.2 Test Data Management

```typescript
// Test data factory
class TestDataFactory {
  static validUrls = [
    'https://github.com/org/repo/releases/download/v1.0/plugin.difypkg',
    'https://marketplace.dify.ai/api/v1/plugins/author/name/versions/1.0.0/download'
  ];
  
  static invalidUrls = [
    'https://example.com/not-a-plugin.zip',
    'ftp://invalid-protocol.com/plugin.difypkg',
    'https://unreachable-domain-12345.com/plugin.difypkg'
  ];
  
  static testPlugins = [
    { author: 'langgenius', name: 'agent', version: '0.0.9' },
    { author: 'antv', name: 'visualization', version: '0.1.7' }
  ];
  
  static platforms = [
    { value: 'manylinux2014_x86_64', label: 'Linux x86_64' },
    { value: 'manylinux2014_aarch64', label: 'Linux ARM64' },
    { value: 'macosx_10_9_x86_64', label: 'macOS x86_64' }
  ];
  
  static generateTestFile(sizeMB: number = 1): Buffer {
    return Buffer.alloc(sizeMB * 1024 * 1024);
  }
}

// Environment configuration
interface TestEnvironment {
  baseUrl: string;
  apiUrl: string;
  wsUrl: string;
  dockerized: boolean;
  services: {
    backend: string;
    frontend: string;
    redis: string;
    worker: string;
  };
}

const environments: Record<string, TestEnvironment> = {
  local: {
    baseUrl: 'http://localhost',
    apiUrl: 'http://localhost/api/v1',
    wsUrl: 'ws://localhost/ws',
    dockerized: true,
    services: {
      backend: 'dify-repack-backend',
      frontend: 'dify-repack-frontend',
      redis: 'dify-repack-redis',
      worker: 'dify-repack-worker'
    }
  },
  ci: {
    baseUrl: 'http://nginx',
    apiUrl: 'http://nginx/api/v1',
    wsUrl: 'ws://nginx/ws',
    dockerized: true,
    services: {
      backend: 'backend',
      frontend: 'frontend',
      redis: 'redis',
      worker: 'worker'
    }
  }
};
```

### 3.3 WebSocket Testing Utilities

```typescript
// WebSocket test helper
class WebSocketTestHelper {
  private ws: WebSocket;
  private messages: any[] = [];
  
  async connect(taskId: string, baseUrl: string) {
    const wsUrl = `${baseUrl}/ws/tasks/${taskId}`;
    this.ws = new WebSocket(wsUrl);
    
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve(this);
      this.ws.onerror = reject;
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.messages.push(data);
      };
    });
  }
  
  async waitForMessage(predicate: (msg: any) => boolean, timeout = 30000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const message = this.messages.find(predicate);
      if (message) return message;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    throw new Error('Timeout waiting for WebSocket message');
  }
  
  async waitForCompletion() {
    return this.waitForMessage(msg => msg.status === 'completed');
  }
  
  disconnect() {
    this.ws.close();
  }
}
```

## 4. Cross-browser Testing Strategy

### 4.1 Browser Matrix
```typescript
const browsers = [
  { name: 'chromium', channel: 'chrome' },
  { name: 'firefox' },
  { name: 'webkit' }, // Safari
  { name: 'chromium', channel: 'msedge' }
];

// Mobile viewports
const devices = [
  'iPhone 12',
  'iPhone SE',
  'Pixel 5',
  'iPad Pro',
  'Galaxy S21'
];
```

### 4.2 Responsive Testing
```typescript
describe('Responsive Design', () => {
  const viewports = [
    { width: 375, height: 667 },  // Mobile
    { width: 768, height: 1024 }, // Tablet
    { width: 1920, height: 1080 } // Desktop
  ];
  
  viewports.forEach(viewport => {
    test(`Layout at ${viewport.width}x${viewport.height}`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');
      
      // Test responsive elements
      await expect(page.getByRole('navigation')).toBeVisible();
      await expect(page.getByRole('main')).toBeVisible();
      
      // Mobile-specific tests
      if (viewport.width < 768) {
        await expect(page.getByRole('button', { name: 'Menu' })).toBeVisible();
      }
    });
  });
});
```

## 5. Visual Regression Testing

```typescript
// Visual regression configuration
import { test as base } from '@playwright/test';
import { expect as baseExpect } from '@playwright/test';

export const test = base.extend({
  // Custom fixture for visual testing
  visualTest: async ({ page }, use) => {
    await use({
      async compareScreenshot(name: string, options = {}) {
        await baseExpect(page).toHaveScreenshot(name, {
          maxDiffPixels: 100,
          threshold: 0.2,
          animations: 'disabled',
          ...options
        });
      }
    });
  }
});

// Visual regression tests
test.describe('Visual Regression', () => {
  test('Homepage appearance', async ({ page, visualTest }) => {
    await page.goto('/');
    await visualTest.compareScreenshot('homepage.png');
  });
  
  test('Dark mode appearance', async ({ page, visualTest }) => {
    await page.goto('/');
    await page.click('[data-testid="theme-toggle"]');
    await visualTest.compareScreenshot('homepage-dark.png');
  });
  
  test('Task progress states', async ({ page, visualTest }) => {
    // Mock different progress states
    const states = ['pending', 'processing', 'completed', 'failed'];
    
    for (const state of states) {
      await page.route('**/api/v1/tasks/*', route => {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            status: state,
            progress: state === 'processing' ? 45 : 100
          })
        });
      });
      
      await page.goto('/task/test-id');
      await visualTest.compareScreenshot(`task-${state}.png`);
    }
  });
});
```

## 6. Performance Testing

```typescript
// Performance monitoring
test.describe('Performance', () => {
  test('Page load performance', async ({ page, browser }) => {
    const client = await page.context().newCDPSession(page);
    await client.send('Performance.enable');
    
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(3000); // 3 second threshold
    
    // Measure Web Vitals
    const metrics = await page.evaluate(() => {
      return {
        FCP: performance.getEntriesByName('first-contentful-paint')[0]?.startTime,
        LCP: performance.getEntriesByType('largest-contentful-paint').pop()?.startTime,
        CLS: 0, // Would need more complex calculation
        FID: 0  // Would need user interaction
      };
    });
    
    expect(metrics.FCP).toBeLessThan(1500);
    expect(metrics.LCP).toBeLessThan(2500);
  });
  
  test('File upload performance', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="file-tab"]');
    
    const uploadTime = await page.evaluate(async () => {
      const file = new File(['x'.repeat(10 * 1024 * 1024)], 'test.difypkg');
      const startTime = performance.now();
      
      // Simulate upload
      const input = document.querySelector('input[type="file"]');
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      
      return performance.now() - startTime;
    });
    
    expect(uploadTime).toBeLessThan(1000); // Should be instant for local file
  });
});
```

## 7. Docker Environment Setup

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  playwright:
    build:
      context: .
      dockerfile: Dockerfile.playwright
    volumes:
      - ./tests:/tests
      - ./test-results:/test-results
      - ./playwright-report:/playwright-report
    environment:
      - BASE_URL=http://nginx
      - CI=true
    depends_on:
      - nginx
      - backend
      - frontend
      - redis
      - worker
    networks:
      - app-network
    command: npx playwright test

  # Include all app services from main docker-compose.yml
  backend:
    extends:
      file: docker-compose.yml
      service: backend
  
  frontend:
    extends:
      file: docker-compose.yml
      service: frontend
  
  # ... other services
```

```dockerfile
# Dockerfile.playwright
FROM mcr.microsoft.com/playwright:v1.40.0-focal

WORKDIR /tests

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy test files
COPY tests/ ./tests/
COPY playwright.config.ts ./

# Install browsers
RUN npx playwright install --with-deps

CMD ["npx", "playwright", "test"]
```

## 8. CI/CD Integration

### 8.1 GitHub Actions Workflow

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        browser: [chromium, firefox, webkit]
        shard: [1, 2, 3, 4]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
          ./scripts/wait-for-services.sh
      
      - name: Run E2E tests
        run: |
          docker-compose -f docker-compose.test.yml run \
            -e BROWSER=${{ matrix.browser }} \
            -e SHARD=${{ matrix.shard }}/4 \
            playwright
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-results-${{ matrix.browser }}-${{ matrix.shard }}
          path: |
            test-results/
            playwright-report/
      
      - name: Upload coverage
        if: matrix.browser == 'chromium' && matrix.shard == 1
        uses: codecov/codecov-action@v3
```

### 8.2 Parallel Execution Strategy

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'junit.xml' }],
    ['github']
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Global timeout
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },
  ],
  
  webServer: process.env.CI ? undefined : {
    command: 'docker-compose up',
    port: 80,
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
  },
});
```

## 9. Test Organization and Execution

### 9.1 Test Suite Structure
```
tests/
├── setup/
│   ├── global.setup.ts      # Global setup (auth, data)
│   └── docker.setup.ts      # Docker environment setup
├── e2e/
│   ├── url-submission.spec.ts
│   ├── marketplace.spec.ts
│   ├── file-upload.spec.ts
│   ├── websocket.spec.ts
│   └── deep-links.spec.ts
├── integration/
│   ├── api.spec.ts
│   ├── celery-tasks.spec.ts
│   └── redis.spec.ts
├── visual/
│   ├── homepage.spec.ts
│   ├── task-status.spec.ts
│   └── marketplace.spec.ts
├── performance/
│   ├── page-load.spec.ts
│   └── file-operations.spec.ts
├── fixtures/
│   ├── test-files/
│   └── mock-data/
└── utils/
    ├── helpers.ts
    ├── page-objects/
    └── websocket-helper.ts
```

### 9.2 Test Execution Commands

```bash
# Run all tests
npm test

# Run specific test suite
npm test -- tests/e2e/url-submission.spec.ts

# Run tests in headed mode
npm test -- --headed

# Run tests with specific browser
npm test -- --project=firefox

# Run tests in debug mode
npm test -- --debug

# Run visual regression tests only
npm test -- tests/visual/

# Run tests with custom base URL
BASE_URL=https://staging.example.com npm test

# Generate and open HTML report
npm run test:report
```

## 10. Key Playwright Dependencies

```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.10.0",
    "typescript": "^5.3.0"
  },
  "dependencies": {
    "@faker-js/faker": "^8.3.0",
    "dotenv": "^16.3.0",
    "winston": "^3.11.0"
  }
}
```

## 11. Best Practices and Guidelines

### 11.1 Test Writing Guidelines
- Use descriptive test names that explain the scenario
- Follow AAA pattern (Arrange, Act, Assert)
- Use Page Object Model for maintainability
- Implement proper error handling and logging
- Add appropriate waits and timeouts
- Use test fixtures for common setup

### 11.2 Debugging Strategies
- Use Playwright Inspector for debugging
- Enable trace recording for failed tests
- Capture screenshots and videos on failure
- Use browser DevTools integration
- Implement custom reporters for better insights

### 11.3 Maintenance Considerations
- Regular update of selectors and locators
- Monitor test execution time
- Review and refactor flaky tests
- Keep test data independent
- Version control test artifacts
- Regular dependency updates

## Conclusion

This comprehensive E2E testing plan provides a robust framework for testing the Dify Plugin Repackaging application. By implementing these test scenarios and strategies with Playwright, you can ensure high quality, reliability, and user satisfaction across all supported platforms and browsers.