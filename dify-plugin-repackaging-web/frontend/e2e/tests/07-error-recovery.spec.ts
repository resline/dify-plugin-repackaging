import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('Error Recovery and Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should recover from task failure', async ({ page, homePage, taskStatusPage }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'failure-test-123',
          status: 'processing'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Simulate task failure via WebSocket
    await page.evaluate(() => {
      setTimeout(() => {
        const ws = (window as any).__wsInstance;
        if (ws) {
          ws.dispatchEvent(new MessageEvent('message', {
            data: JSON.stringify({
              type: 'status',
              status: 'failed',
              error: 'Failed to download dependencies: Connection timeout'
            })
          }));
        }
      }, 1000);
    });
    
    await taskStatusPage.waitForTaskError();
    
    // Should show error message
    const errorMessage = await taskStatusPage.getErrorMessage();
    expect(errorMessage).toContain('Failed to download dependencies');
    
    // Should show retry button
    const retryButton = page.locator('button', { hasText: 'Retry' });
    await expect(retryButton).toBeVisible();
    
    // Mock successful retry
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'retry-success-123',
          status: 'pending'
        })
      });
    });
    
    // Retry task
    await taskStatusPage.clickRetryButton();
    
    // Should create new task
    await taskStatusPage.waitForTaskToStart();
  });

  test('should handle server disconnection', async ({ page, homePage, testHelpers }) => {
    // Start with working server
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Simulate server going offline
    await testHelpers.simulateOffline(page);
    
    // Try to perform action
    const newTaskButton = page.locator('button', { hasText: 'New Task' });
    if (await newTaskButton.isVisible()) {
      await newTaskButton.click();
    }
    
    // Should show offline indicator
    const offlineIndicator = page.locator('text=Connection lost');
    await expect(offlineIndicator).toBeVisible({ timeout: 10000 });
    
    // Restore connection
    await testHelpers.simulateOnline(page);
    
    // Should recover
    await page.waitForTimeout(2000);
    await expect(offlineIndicator).not.toBeVisible();
  });

  test('should handle session timeout', async ({ page, homePage, testHelpers }) => {
    // Submit initial task
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Simulate session timeout
    await page.route('**/api/v1/**', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Session expired' })
      });
    });
    
    // Try to create new task
    await page.locator('button', { hasText: 'New Task' }).click();
    await homePage.submitUrl(TEST_DATA.urls.githubRelease);
    
    // Should show session error
    const errorToast = await homePage.waitForToast('Session expired');
    await expect(errorToast).toBeVisible();
  });

  test('should handle rate limiting', async ({ page, homePage }) => {
    let requestCount = 0;
    
    await page.route('**/api/v1/tasks', (route) => {
      requestCount++;
      if (requestCount > 3) {
        route.fulfill({
          status: 429,
          contentType: 'application/json',
          headers: {
            'X-RateLimit-Limit': '100',
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': String(Date.now() + 60000)
          },
          body: JSON.stringify({ detail: 'Rate limit exceeded. Please wait 60 seconds.' })
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            task_id: `task-${requestCount}`,
            status: 'pending'
          })
        });
      }
    });
    
    // Submit multiple tasks rapidly
    for (let i = 0; i < 5; i++) {
      await homePage.submitUrl(`${TEST_DATA.urls.validDifypkg}?v=${i}`);
      if (i < 4) {
        await page.locator('button', { hasText: 'New Task' }).click();
      }
    }
    
    // Should show rate limit error
    const errorToast = await homePage.waitForToast('Rate limit exceeded');
    await expect(errorToast).toBeVisible();
  });

  test('should handle corrupt response data', async ({ page, homePage }) => {
    // Mock corrupt JSON response
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: 'invalid json {{'
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Should show error
    const errorToast = await homePage.getToastMessage();
    expect(errorToast).toContain('error');
  });

  test('should handle browser back/forward navigation', async ({ page, homePage }) => {
    // Navigate through tabs
    await homePage.selectUrlTab();
    await homePage.selectMarketplaceTab();
    await homePage.selectFileTab();
    
    // Go back
    await page.goBack();
    expect(await homePage.getCurrentTab()).toContain('Marketplace');
    
    // Go back again
    await page.goBack();
    expect(await homePage.getCurrentTab()).toContain('Direct URL');
    
    // Go forward
    await page.goForward();
    expect(await homePage.getCurrentTab()).toContain('Marketplace');
  });

  test('should preserve state on page refresh', async ({ page, homePage, testHelpers }) => {
    // Set custom values
    const customUrl = 'https://example.com/custom.difypkg';
    const customSuffix = 'test-suffix';
    
    await homePage.page.locator('input[placeholder*="Enter URL"]').fill(customUrl);
    const suffixInput = homePage.page.locator('input[placeholder*="suffix"]');
    await suffixInput.clear();
    await suffixInput.fill(customSuffix);
    
    // Store in localStorage
    await testHelpers.setLocalStorage(page, 'lastUrl', customUrl);
    await testHelpers.setLocalStorage(page, 'lastSuffix', customSuffix);
    
    // Refresh page
    await page.reload();
    
    // Check if tab selection is preserved
    const savedTab = await testHelpers.getLocalStorage(page, 'lastSelectedTab');
    expect(savedTab).toBe('url');
  });

  test('should handle JavaScript errors gracefully', async ({ page, homePage, testHelpers }) => {
    const jsErrors = await testHelpers.checkForJsErrors(page);
    
    // Inject error
    await page.evaluate(() => {
      throw new Error('Test error - should be caught');
    });
    
    // App should continue functioning
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Check that the error was logged but didn't break the app
    const errors = await testHelpers.checkForJsErrors(page);
    expect(errors.some(e => e.includes('Test error'))).toBe(true);
  });

  test('should handle memory leaks in long-running sessions', async ({ page, homePage }) => {
    // Monitor memory usage
    const initialMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Perform multiple operations
    for (let i = 0; i < 10; i++) {
      await homePage.selectUrlTab();
      await homePage.selectMarketplaceTab();
      await homePage.selectFileTab();
      await homePage.selectCompletedTab();
    }
    
    // Check memory hasn't increased significantly
    const finalMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Memory increase should be reasonable (less than 50MB)
    const memoryIncrease = finalMemory - initialMemory;
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
  });

  test('should handle concurrent operations', async ({ page, homePage }) => {
    // Mock endpoints
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: `concurrent-${Date.now()}`,
          status: 'pending'
        })
      });
    });
    
    await page.route('**/api/v1/files', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ files: [] })
      });
    });
    
    // Start multiple operations concurrently
    const operations = [
      homePage.submitUrl(TEST_DATA.urls.validDifypkg),
      homePage.selectCompletedTab(),
      homePage.toggleTheme(),
      homePage.selectMarketplaceTab()
    ];
    
    // All operations should complete without errors
    await Promise.all(operations);
    
    // App should remain functional
    const heading = page.locator('h2');
    await expect(heading).toBeVisible();
  });

  test('should handle XSS attempts', async ({ page, homePage }) => {
    const xssPayload = '<script>alert("XSS")</script>';
    
    // Try XSS in URL input
    await homePage.page.locator('input[placeholder*="Enter URL"]').fill(xssPayload);
    
    // No alert should appear
    let alertFired = false;
    page.on('dialog', () => {
      alertFired = true;
    });
    
    await page.waitForTimeout(1000);
    expect(alertFired).toBe(false);
    
    // Try XSS in search
    await homePage.selectMarketplaceTab();
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(xssPayload);
    
    await page.waitForTimeout(1000);
    expect(alertFired).toBe(false);
  });

  test('should handle CSRF protection', async ({ page }) => {
    // Mock CSRF error
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'CSRF token invalid' })
      });
    });
    
    const homePage = new (await import('../pages/HomePage')).HomePage(page);
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Should show security error
    const errorToast = await homePage.waitForToast('CSRF token invalid');
    await expect(errorToast).toBeVisible();
  });
});