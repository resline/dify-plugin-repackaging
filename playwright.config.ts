import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

/**
 * Playwright configuration for Dify Plugin Repackaging E2E tests
 */

// Create base configuration
const baseConfig = {
  testDir: './playwright-tests',
  
  // Test execution settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  
  // Test timeout settings
  timeout: 120000, // 2 minutes per test
  expect: {
    timeout: 30000, // 30 seconds for assertions
  },
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
    ...(process.env.CI ? [['github'] as const] : []),
  ] as const,
  
  // Global test settings
  use: {
    // Base URL from environment or default
    baseURL: process.env.BASE_URL || 'http://localhost',
    
    // Artifact collection
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Timeouts
    actionTimeout: 30000,
    navigationTimeout: 30000,
    
    // Context options
    acceptDownloads: true,
    
    // Viewport
    viewport: { width: 1280, height: 720 },
    
    // Permissions
    permissions: ['clipboard-read', 'clipboard-write'],
    
    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept-Language': 'en-US',
    },
  },
  
  // Project configurations for different browsers and devices
  projects: [
    // Setup project for authentication and data preparation
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    
    // Desktop browsers
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Chrome-specific options
        launchOptions: {
          args: ['--disable-web-security'], // For CORS in local testing
        },
      },
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
      name: 'edge',
      use: { 
        ...devices['Desktop Edge'],
        channel: 'msedge',
      },
      dependencies: ['setup'],
    },
    
    // Mobile browsers
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },
    
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },
    
    // Tablet
    {
      name: 'tablet',
      use: { ...devices['iPad Pro'] },
      dependencies: ['setup'],
    },
    
    // API testing project (no browser)
    {
      name: 'api',
      testMatch: /.*api\.spec\.ts/,
      use: {
        baseURL: process.env.API_URL || 'http://localhost/api/v1',
      },
    },
    
    // Visual regression testing
    {
      name: 'visual',
      testMatch: /.*visual\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        // Consistent viewport for visual tests
        viewport: { width: 1920, height: 1080 },
        // Disable animations
        launchOptions: {
          args: ['--force-prefers-reduced-motion'],
        },
      },
    },
    
    // Performance testing
    {
      name: 'performance',
      testMatch: /.*performance\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--enable-precise-memory-info'],
        },
      },
    },
  ],
  
  // Web server configuration for local development
  webServer: process.env.CI ? undefined : {
    command: 'docker-compose up',
    port: 80,
    timeout: 120 * 1000, // 2 minutes to start
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      BACKEND_CORS_ORIGINS: '["http://localhost","http://localhost:80"]',
    },
  },
  
  // Output directories
  outputDir: 'test-results',
  
  // Global setup and teardown
  globalSetup: require.resolve('./playwright-tests/setup/global.setup.ts'),
  globalTeardown: require.resolve('./playwright-tests/setup/global.teardown.ts'),
} as const;

// Apply environment-specific configurations
let config = { ...baseConfig };

// Docker environment overrides
if (process.env.TEST_ENV === 'docker') {
  config = {
    ...config,
    use: {
      ...config.use,
      baseURL: 'http://nginx',
    },
    webServer: {
      command: 'docker-compose -f docker-compose.yml -f docker-compose.test.yml up',
      port: 80,
      timeout: 180 * 1000, // 3 minutes for Docker
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        BACKEND_CORS_ORIGINS: '["http://localhost","http://localhost:80"]',
      },
    },
  };
}

// CI environment overrides
if (process.env.CI) {
  const totalShards = parseInt(process.env.TOTAL_SHARDS || '4');
  const shardIndex = parseInt(process.env.SHARD_INDEX || '1') - 1;
  
  config = {
    ...config,
    shard: {
      total: totalShards,
      current: shardIndex + 1,
    },
    // Increase retries in CI
    retries: 2,
    // Use more workers in CI
    workers: '50%',
  };
}

// Export the final configuration
export default defineConfig(config);