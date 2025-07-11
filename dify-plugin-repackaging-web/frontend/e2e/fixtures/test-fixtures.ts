import { test as base } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { TaskStatusPage } from '../pages/TaskStatusPage';
import { WebSocketHelper } from '../utils/websocket';
import { TestHelpers } from '../utils/test-helpers';

// Define custom fixtures
type TestFixtures = {
  homePage: HomePage;
  taskStatusPage: TaskStatusPage;
  wsHelper: WebSocketHelper;
  testHelpers: typeof TestHelpers;
};

// Extend base test with our fixtures
export const test = base.extend<TestFixtures>({
  homePage: async ({ page }, use) => {
    const homePage = new HomePage(page);
    await use(homePage);
  },

  taskStatusPage: async ({ page }, use) => {
    const taskStatusPage = new TaskStatusPage(page);
    await use(taskStatusPage);
  },

  wsHelper: async ({ page }, use) => {
    const wsHelper = new WebSocketHelper(page);
    await wsHelper.interceptWebSocket();
    await use(wsHelper);
  },

  testHelpers: async ({}, use) => {
    await use(TestHelpers);
  },
});

export { expect } from '@playwright/test';

// Test data constants
export const TEST_DATA = {
  urls: {
    validDifypkg: 'https://example.com/test-plugin.difypkg',
    marketplacePlugin: 'https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9',
    githubRelease: 'https://github.com/example/plugin/releases/download/v1.0.0/plugin.difypkg',
    invalidUrl: 'https://example.com/not-a-plugin.txt',
    malformedUrl: 'not-a-valid-url',
  },
  marketplace: {
    validPlugin: {
      author: 'langgenius',
      name: 'agent',
      version: '0.0.9'
    },
    searchTerms: {
      valid: 'agent',
      noResults: 'nonexistentplugin123456',
    }
  },
  platforms: [
    'manylinux2014_x86_64',
    'manylinux2014_aarch64',
    'manylinux_2_17_x86_64',
    'win_amd64',
    'macosx_10_9_x86_64',
    'macosx_11_0_arm64'
  ],
  suffixes: {
    default: 'offline',
    custom: 'custom-suffix',
    empty: '',
  },
  timeouts: {
    short: 5000,
    medium: 15000,
    long: 30000,
    veryLong: 60000,
  },
  errorMessages: {
    networkError: 'Network error - no response received',
    serverError: 'Server error',
    invalidFile: 'Invalid file type',
    taskFailed: 'Task failed',
  }
};