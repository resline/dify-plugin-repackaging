import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for fonts and animations to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
  });

  test('should match homepage layout', async ({ page }) => {
    await expect(page).toHaveScreenshot('homepage-default.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match dark mode appearance', async ({ page, homePage }) => {
    await homePage.toggleTheme();
    await page.waitForTimeout(500); // Wait for transition
    
    await expect(page).toHaveScreenshot('homepage-dark-mode.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match Direct URL tab appearance', async ({ page, homePage }) => {
    await homePage.selectUrlTab();
    
    // Fill in form
    await page.locator('input[placeholder*="Enter URL"]').fill(TEST_DATA.urls.validDifypkg);
    await homePage.selectPlatform(TEST_DATA.platforms[0]);
    
    await expect(page).toHaveScreenshot('url-tab-filled.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match marketplace tab appearance', async ({ page, homePage }) => {
    await homePage.selectMarketplaceTab();
    
    // Mock marketplace data
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [
            {
              author: 'langgenius',
              name: 'agent',
              description: 'AI Agent plugin for enhanced capabilities',
              latest_version: '0.0.9',
              versions: ['0.0.9', '0.0.8', '0.0.7']
            },
            {
              author: 'community',
              name: 'translator',
              description: 'Multi-language translation plugin',
              latest_version: '1.2.0',
              versions: ['1.2.0', '1.1.0', '1.0.0']
            }
          ]
        })
      });
    });
    
    // Search for plugins
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill('plugin');
    await page.waitForTimeout(600);
    
    await expect(page).toHaveScreenshot('marketplace-with-results.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match file upload tab appearance', async ({ page, homePage }) => {
    await homePage.selectFileTab();
    
    await expect(page).toHaveScreenshot('file-upload-tab.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match completed tab appearance', async ({ page, homePage }) => {
    await homePage.selectCompletedTab();
    
    // Mock completed files
    await page.route('**/api/v1/files', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          files: [
            {
              id: 'file-1',
              filename: 'my-plugin-offline.difypkg',
              size: 2048000,
              created_at: new Date().toISOString(),
              platform: 'manylinux2014_x86_64'
            },
            {
              id: 'file-2',
              filename: 'another-plugin-offline.difypkg',
              size: 1536000,
              created_at: new Date(Date.now() - 3600000).toISOString(),
              platform: 'win_amd64'
            }
          ]
        })
      });
    });
    
    await page.reload();
    await homePage.selectCompletedTab();
    
    await expect(page).toHaveScreenshot('completed-tab-with-files.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match task processing state', async ({ page, homePage, taskStatusPage }) => {
    // Mock task in progress
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'visual-test-123',
          status: 'processing',
          progress: 45,
          current_step: 'Downloading dependencies...'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await taskStatusPage.waitForTaskToStart();
    
    await expect(page).toHaveScreenshot('task-processing.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match task completion state', async ({ page, homePage }) => {
    // Mock completed task
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'completed-visual-test',
          status: 'completed',
          progress: 100,
          result: {
            filename: 'test-plugin-offline.difypkg',
            size: 3072000,
            platform: 'manylinux2014_x86_64'
          },
          processing_time: 45.3
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Wait for completion UI
    await page.waitForTimeout(2000);
    
    await expect(page).toHaveScreenshot('task-completed.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match error state appearance', async ({ page, homePage }) => {
    // Mock task failure
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'error-visual-test',
          status: 'failed',
          error: 'Failed to download plugin: Network timeout'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('task-error-state.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match toast notifications appearance', async ({ page, homePage }) => {
    // Trigger multiple toasts
    await page.evaluate(() => {
      // Inject toast trigger
      const event1 = new CustomEvent('show-toast', { 
        detail: { type: 'success', message: 'Task completed successfully!' }
      });
      window.dispatchEvent(event1);
      
      setTimeout(() => {
        const event2 = new CustomEvent('show-toast', { 
          detail: { type: 'error', message: 'Failed to connect to server' }
        });
        window.dispatchEvent(event2);
      }, 100);
      
      setTimeout(() => {
        const event3 = new CustomEvent('show-toast', { 
          detail: { type: 'info', message: 'Processing your request...' }
        });
        window.dispatchEvent(event3);
      }, 200);
    });
    
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('toast-notifications.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match mobile responsive layout', async ({ page }) => {
    // Test different viewport sizes
    const viewports = [
      { name: 'mobile-portrait', width: 375, height: 667 },
      { name: 'mobile-landscape', width: 667, height: 375 },
      { name: 'tablet-portrait', width: 768, height: 1024 },
      { name: 'tablet-landscape', width: 1024, height: 768 }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.waitForTimeout(500); // Wait for responsive adjustments
      
      await expect(page).toHaveScreenshot(`responsive-${viewport.name}.png`, {
        fullPage: true,
        animations: 'disabled'
      });
    }
  });

  test('should match loading states', async ({ page }) => {
    // Test skeleton loading state
    await page.route('**/api/v1/files', async (route) => {
      await page.waitForTimeout(2000); // Delay to capture loading state
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ files: [] })
      });
    });
    
    await page.goto('/?tab=completed');
    
    // Capture loading skeleton
    await expect(page).toHaveScreenshot('loading-skeleton.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match form validation states', async ({ page, homePage }) => {
    // Test various validation states
    const urlInput = page.locator('input[placeholder*="Enter URL"]');
    
    // Invalid URL
    await urlInput.fill('not-a-valid-url');
    await urlInput.blur();
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('form-validation-error.png', {
      fullPage: true,
      animations: 'disabled'
    });
    
    // Valid URL
    await urlInput.fill(TEST_DATA.urls.validDifypkg);
    await urlInput.blur();
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('form-validation-success.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match hover states', async ({ page, homePage }) => {
    // Test button hover states
    const submitButton = page.locator('button', { hasText: 'Start Repackaging' });
    await submitButton.hover();
    
    await expect(page).toHaveScreenshot('button-hover-state.png', {
      fullPage: true,
      animations: 'disabled'
    });
    
    // Test tab hover states
    const marketplaceTab = page.locator('[role="tab"]', { hasText: 'Marketplace' });
    await marketplaceTab.hover();
    
    await expect(page).toHaveScreenshot('tab-hover-state.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });

  test('should match focus states', async ({ page }) => {
    // Test keyboard navigation focus states
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    await expect(page).toHaveScreenshot('focus-states.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });
});