import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('URL Submission Workflow', () => {
  test.beforeEach(async ({ page, homePage }) => {
    await page.goto('/');
    await homePage.selectUrlTab();
  });

  test('should validate URL input', async ({ homePage }) => {
    // Test empty URL
    const submitButton = homePage.page.locator('button', { hasText: 'Start Repackaging' });
    await expect(submitButton).toBeDisabled();
    
    // Test invalid URL
    await homePage.page.locator('input[placeholder*="Enter URL"]').fill(TEST_DATA.urls.malformedUrl);
    await expect(submitButton).toBeDisabled();
    
    // Test valid URL
    await homePage.page.locator('input[placeholder*="Enter URL"]').fill(TEST_DATA.urls.validDifypkg);
    await expect(submitButton).toBeEnabled();
  });

  test('should submit URL successfully', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Submit URL
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Should navigate to task status
    await taskStatusPage.waitForTaskToStart();
    
    // Check WebSocket connection
    await wsHelper.waitForConnection();
    const wsState = await wsHelper.getConnectionState();
    expect(wsState).toBe('open');
    
    // Should show processing status
    const status = await taskStatusPage.getTaskStatus();
    expect(status).toBeTruthy();
  });

  test('should handle platform selection', async ({ homePage }) => {
    // Select platform
    await homePage.selectPlatform(TEST_DATA.platforms[0]);
    
    // Verify platform is selected
    const platformButton = homePage.page.locator('button', { hasText: TEST_DATA.platforms[0] });
    await expect(platformButton).toBeVisible();
    
    // Submit with platform
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg, TEST_DATA.platforms[0]);
  });

  test('should handle custom suffix', async ({ homePage }) => {
    // Default suffix should be 'offline'
    const suffixValue = await homePage.getSuffixInputValue();
    expect(suffixValue).toBe(TEST_DATA.suffixes.default);
    
    // Change suffix
    await homePage.submitUrl(
      TEST_DATA.urls.validDifypkg, 
      undefined, 
      TEST_DATA.suffixes.custom
    );
  });

  test('should show error for invalid URL', async ({ page, homePage }) => {
    // Mock API error
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid URL format' })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.invalidUrl);
    
    // Should show error toast
    const toast = await homePage.waitForToast('Invalid URL format');
    await expect(toast).toBeVisible();
  });

  test('should handle network errors gracefully', async ({ page, homePage, testHelpers }) => {
    // Simulate network error
    await page.route('**/api/v1/tasks', (route) => route.abort());
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Should show error toast
    const toast = await homePage.getToastMessage();
    expect(toast).toContain('error');
  });

  test('should auto-submit marketplace URLs', async ({ page }) => {
    // Navigate with marketplace URL in query params
    await page.goto('/?type=url&url=' + encodeURIComponent(TEST_DATA.urls.marketplacePlugin));
    
    // Should auto-submit and show task status
    const taskStatus = page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should auto-submit .difypkg URLs', async ({ page }) => {
    // Navigate with .difypkg URL in query params
    await page.goto('/?type=url&url=' + encodeURIComponent(TEST_DATA.urls.validDifypkg));
    
    // Should auto-submit and show task status
    const taskStatus = page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should handle GitHub release URLs', async ({ homePage }) => {
    await homePage.submitUrl(TEST_DATA.urls.githubRelease);
    
    // Should accept GitHub URLs
    const taskStatus = homePage.page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should preserve form state on error', async ({ page, homePage }) => {
    const testUrl = TEST_DATA.urls.validDifypkg;
    const testPlatform = TEST_DATA.platforms[0];
    const testSuffix = TEST_DATA.suffixes.custom;
    
    // Fill form
    await homePage.page.locator('input[placeholder*="Enter URL"]').fill(testUrl);
    await homePage.selectPlatform(testPlatform);
    const suffixInput = homePage.page.locator('input[placeholder*="suffix"]');
    await suffixInput.clear();
    await suffixInput.fill(testSuffix);
    
    // Mock API error
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Server error' })
      });
    });
    
    // Submit
    const submitButton = homePage.page.locator('button', { hasText: 'Start Repackaging' });
    await submitButton.click();
    
    // Form values should be preserved
    expect(await homePage.getUrlInputValue()).toBe(testUrl);
    expect(await homePage.getSuffixInputValue()).toBe(testSuffix);
  });
});