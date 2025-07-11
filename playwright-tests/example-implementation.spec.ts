import { test, expect, Page, Download } from '@playwright/test';
import { WebSocketTestHelper } from './utils/websocket-helper';
import { RepackagingPage, TaskStatusPage, MarketplacePage } from './page-objects';

// Test configuration
const TEST_TIMEOUT = 120000; // 2 minutes for repackaging operations

test.describe('Dify Plugin Repackaging E2E Tests', () => {
  let repackagingPage: RepackagingPage;
  let taskStatusPage: TaskStatusPage;
  let marketplacePage: MarketplacePage;

  test.beforeEach(async ({ page }) => {
    // Initialize page objects
    repackagingPage = new RepackagingPage(page);
    taskStatusPage = new TaskStatusPage(page);
    marketplacePage = new MarketplacePage(page);
    
    // Navigate to application
    await page.goto('/');
    await repackagingPage.waitForLoadComplete();
  });

  test.describe('URL Submission Journey', () => {
    test('should successfully repackage plugin from direct URL', async ({ page }) => {
      test.setTimeout(TEST_TIMEOUT);
      
      // Arrange
      const testUrl = 'https://github.com/langgenius/dify-plugin-agent/releases/download/v0.0.9/agent.difypkg';
      
      // Act
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging(testUrl, 'manylinux2014_x86_64');
      
      // Assert - Check task creation
      await expect(page.getByText('Task created successfully!')).toBeVisible();
      
      // Wait for task page
      await expect(taskStatusPage.progressBar).toBeVisible();
      
      // Monitor WebSocket updates
      const taskId = await page.url().match(/task\/([^/]+)/)?.[1];
      expect(taskId).toBeTruthy();
      
      const wsHelper = new WebSocketTestHelper();
      await wsHelper.connect(taskId!, page.url());
      
      // Wait for completion
      await taskStatusPage.waitForCompletion();
      
      // Verify download button
      await expect(taskStatusPage.downloadButton).toBeVisible();
      await expect(taskStatusPage.downloadButton).toContainText('.difypkg');
      
      // Download and verify file
      const download = await taskStatusPage.downloadFile();
      expect(download.suggestedFilename()).toMatch(/.*-offline\.difypkg$/);
      
      // Cleanup
      wsHelper.disconnect();
    });

    test('should handle invalid URL gracefully', async ({ page }) => {
      // Arrange
      const invalidUrl = 'https://example.com/not-a-plugin.zip';
      
      // Act
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging(invalidUrl);
      
      // Assert
      await expect(page.getByText(/URL must point to a \.difypkg file/)).toBeVisible();
    });

    test('should handle network timeout', async ({ page, context }) => {
      // Mock slow network
      await context.route('**/api/v1/tasks', async route => {
        await page.waitForTimeout(35000); // Exceed timeout
        await route.abort();
      });
      
      // Act
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging('https://example.com/plugin.difypkg');
      
      // Assert
      await expect(page.getByText(/Request timeout|Failed to create task/)).toBeVisible({ timeout: 40000 });
    });
  });

  test.describe('Marketplace Journey', () => {
    test('should browse and repackage marketplace plugin', async ({ page }) => {
      test.setTimeout(TEST_TIMEOUT);
      
      // Act
      await repackagingPage.selectTab('marketplace');
      
      // Search for plugin
      await marketplacePage.searchPlugin('agent');
      await page.waitForTimeout(1000); // Wait for search debounce
      
      // Select plugin
      await marketplacePage.selectPlugin('langgenius', 'agent');
      
      // Select version
      await marketplacePage.selectVersion('0.0.9');
      
      // Submit
      await page.getByRole('button', { name: 'Repackage Plugin' }).click();
      
      // Assert
      await expect(page.getByText('Marketplace task created successfully!')).toBeVisible();
      await expect(taskStatusPage.progressBar).toBeVisible();
      
      // Verify marketplace metadata in task
      await expect(page.getByText('langgenius/agent')).toBeVisible();
      await expect(page.getByText('v0.0.9')).toBeVisible();
    });

    test('should handle empty search results', async ({ page }) => {
      await repackagingPage.selectTab('marketplace');
      await marketplacePage.searchPlugin('nonexistentplugin12345');
      await page.waitForTimeout(1000);
      
      await expect(page.getByText(/No plugins found/)).toBeVisible();
    });

    test('should load more plugins on scroll', async ({ page }) => {
      await repackagingPage.selectTab('marketplace');
      
      // Count initial plugins
      const initialCount = await marketplacePage.pluginCards.count();
      
      // Scroll to bottom
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      
      // Click load more if visible
      if (await marketplacePage.loadMoreButton.isVisible()) {
        await marketplacePage.loadMoreButton.click();
        await page.waitForTimeout(1000);
        
        // Verify more plugins loaded
        const newCount = await marketplacePage.pluginCards.count();
        expect(newCount).toBeGreaterThan(initialCount);
      }
    });
  });

  test.describe('File Upload Journey', () => {
    test('should upload and repackage local .difypkg file', async ({ page }) => {
      test.setTimeout(TEST_TIMEOUT);
      
      // Arrange - Create test file
      const fileName = 'test-plugin.difypkg';
      const fileContent = Buffer.from('test content'); // In real test, use actual .difypkg
      
      // Act
      await repackagingPage.selectTab('file');
      
      // Upload file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: fileName,
        mimeType: 'application/octet-stream',
        buffer: fileContent
      });
      
      // Select platform
      await page.getByLabel('Platform').selectOption('manylinux2014_aarch64');
      
      // Submit
      await page.getByRole('button', { name: 'Upload and Repackage' }).click();
      
      // Assert
      await expect(page.getByText('File upload task created successfully!')).toBeVisible();
      await expect(taskStatusPage.progressBar).toBeVisible();
      
      // Verify file info displayed
      await expect(page.getByText(fileName)).toBeVisible();
    });

    test('should reject non-.difypkg files', async ({ page }) => {
      await repackagingPage.selectTab('file');
      
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'wrong-file.zip',
        mimeType: 'application/zip',
        buffer: Buffer.from('zip content')
      });
      
      await page.getByRole('button', { name: 'Upload and Repackage' }).click();
      
      await expect(page.getByText(/Invalid file type.*\.difypkg/)).toBeVisible();
    });

    test('should enforce file size limit', async ({ page }) => {
      await repackagingPage.selectTab('file');
      
      // Create 101MB file (exceeds 100MB limit)
      const largeBuffer = Buffer.alloc(101 * 1024 * 1024);
      
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'large-plugin.difypkg',
        mimeType: 'application/octet-stream',
        buffer: largeBuffer
      });
      
      await page.getByRole('button', { name: 'Upload and Repackage' }).click();
      
      await expect(page.getByText(/File size exceeds 100MB limit/)).toBeVisible();
    });
  });

  test.describe('Deep Link Handling', () => {
    test('should auto-submit URL from deep link', async ({ page }) => {
      const deepLinkUrl = '?url=https://github.com/example/plugin/releases/download/v1.0/plugin.difypkg';
      
      await page.goto('/' + deepLinkUrl);
      await repackagingPage.waitForLoadComplete();
      
      // Verify URL is pre-filled
      await expect(repackagingPage.urlInput).toHaveValue('https://github.com/example/plugin/releases/download/v1.0/plugin.difypkg');
      
      // Should auto-submit
      await expect(taskStatusPage.progressBar).toBeVisible({ timeout: 10000 });
    });

    test('should handle marketplace deep link', async ({ page }) => {
      const deepLinkUrl = '?marketplace=langgenius/agent/0.0.9';
      
      await page.goto('/' + deepLinkUrl);
      await repackagingPage.waitForLoadComplete();
      
      // Should switch to marketplace tab and auto-submit
      await expect(page.getByRole('tab', { name: 'Marketplace' })).toHaveAttribute('aria-selected', 'true');
      await expect(taskStatusPage.progressBar).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('WebSocket Real-time Features', () => {
    test('should receive real-time progress updates', async ({ page }) => {
      test.setTimeout(TEST_TIMEOUT);
      
      // Start a task
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging('https://example.com/plugin.difypkg');
      
      // Monitor progress updates
      const progressValues: number[] = [];
      
      page.on('websocket', ws => {
        ws.on('framereceived', event => {
          const data = JSON.parse(event.payload as string);
          if (data.progress !== undefined) {
            progressValues.push(data.progress);
          }
        });
      });
      
      // Wait for some progress
      await page.waitForTimeout(5000);
      
      // Verify progress increased
      expect(progressValues.length).toBeGreaterThan(0);
      expect(Math.max(...progressValues)).toBeGreaterThan(0);
    });

    test('should handle WebSocket reconnection', async ({ page, context }) => {
      // Start a task
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging('https://example.com/plugin.difypkg');
      
      // Simulate network interruption
      await context.setOffline(true);
      await page.waitForTimeout(2000);
      
      // Restore connection
      await context.setOffline(false);
      await page.waitForTimeout(2000);
      
      // Should reconnect and continue receiving updates
      await expect(taskStatusPage.progressBar).toBeVisible();
      
      // Eventually should complete
      await taskStatusPage.waitForCompletion();
    });
  });

  test.describe('Error Recovery', () => {
    test('should handle rate limiting gracefully', async ({ page, context }) => {
      // Mock rate limit response
      let requestCount = 0;
      await context.route('**/api/v1/tasks', async route => {
        requestCount++;
        if (requestCount > 2) {
          await route.fulfill({
            status: 429,
            body: JSON.stringify({ detail: 'Rate limit exceeded. Please try again later.' })
          });
        } else {
          await route.continue();
        }
      });
      
      // Make multiple requests
      for (let i = 0; i < 3; i++) {
        await repackagingPage.selectTab('url');
        await repackagingPage.submitUrlRepackaging(`https://example.com/plugin${i}.difypkg`);
        
        if (i < 2) {
          await page.getByRole('button', { name: 'Start New Task' }).click();
        }
      }
      
      // Should show rate limit error
      await expect(page.getByText(/Rate limit exceeded/)).toBeVisible();
    });

    test('should recover from server errors', async ({ page, context }) => {
      let attemptCount = 0;
      
      await context.route('**/api/v1/tasks', async route => {
        attemptCount++;
        if (attemptCount === 1) {
          await route.fulfill({ status: 500, body: 'Internal Server Error' });
        } else {
          await route.continue();
        }
      });
      
      await repackagingPage.selectTab('url');
      await repackagingPage.submitUrlRepackaging('https://example.com/plugin.difypkg');
      
      // Should show error
      await expect(page.getByText(/Failed to create task/)).toBeVisible();
      
      // Retry
      await repackagingPage.submitUrlRepackaging('https://example.com/plugin.difypkg');
      
      // Should succeed on retry
      await expect(page.getByText('Task created successfully!')).toBeVisible();
    });
  });

  test.describe('Cross-browser Compatibility', () => {
    test('should work across different browsers', async ({ page, browserName }) => {
      // Basic smoke test for each browser
      await expect(repackagingPage.urlTab).toBeVisible();
      await expect(repackagingPage.marketplaceTab).toBeVisible();
      await expect(repackagingPage.fileTab).toBeVisible();
      
      // Test tab switching
      await repackagingPage.selectTab('marketplace');
      await expect(page.getByRole('tab', { name: 'Marketplace' })).toHaveAttribute('aria-selected', 'true');
      
      // Log browser for debugging
      console.log(`Test passed on ${browserName}`);
    });
  });

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      // Tab through interface
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toBeVisible();
      
      // Navigate tabs with keyboard
      await page.getByRole('tab', { name: 'URL' }).focus();
      await page.keyboard.press('ArrowRight');
      await expect(page.getByRole('tab', { name: 'Marketplace' })).toBeFocused();
      
      // Submit form with Enter
      await repackagingPage.urlInput.fill('https://example.com/plugin.difypkg');
      await repackagingPage.urlInput.press('Enter');
      
      await expect(page.getByText(/Task created|must point to/)).toBeVisible();
    });

    test('should have proper ARIA labels', async ({ page }) => {
      const violations = await page.evaluate(() => {
        // Simple accessibility check
        const elements = document.querySelectorAll('button, input, select, [role]');
        const issues: string[] = [];
        
        elements.forEach(el => {
          if (el.tagName === 'BUTTON' && !el.textContent && !el.getAttribute('aria-label')) {
            issues.push(`Button without label: ${el.outerHTML}`);
          }
          if (el.tagName === 'INPUT' && el.getAttribute('type') !== 'hidden' && !el.getAttribute('aria-label') && !el.id) {
            issues.push(`Input without label: ${el.outerHTML}`);
          }
        });
        
        return issues;
      });
      
      expect(violations).toHaveLength(0);
    });
  });
});