import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';
import * as path from 'path';

test.describe('File Upload Workflow', () => {
  test.beforeEach(async ({ page, homePage, testHelpers }) => {
    await page.goto('/');
    await homePage.selectFileTab();
    
    // Create test file
    await testHelpers.createTestDifypkgFile();
  });

  test.afterEach(async ({ testHelpers }) => {
    // Cleanup test files
    await testHelpers.cleanupTestData();
  });

  test('should display file upload interface', async ({ page }) => {
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    
    const dropZone = page.locator('[data-testid="drop-zone"], .border-dashed');
    await expect(dropZone).toBeVisible();
    
    const uploadText = page.locator('text=Drop your .difypkg file here');
    await expect(uploadText).toBeVisible();
  });

  test('should accept file via file input', async ({ page, homePage, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('test-upload.difypkg');
    
    await homePage.uploadFile(testFile);
    
    // Should start processing
    const taskStatus = page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should validate file type', async ({ page, homePage }) => {
    // Try to upload non-.difypkg file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('test content')
    });
    
    // Should show error
    const errorToast = await homePage.waitForToast('Invalid file type');
    await expect(errorToast).toBeVisible();
  });

  test('should enforce file size limit', async ({ page, homePage }) => {
    // Create large file (over 100MB)
    const largeBuffer = Buffer.alloc(101 * 1024 * 1024); // 101MB
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'large.difypkg',
      mimeType: 'application/octet-stream',
      buffer: largeBuffer
    });
    
    // Should show error
    const errorToast = await homePage.waitForToast('File size exceeds 100MB limit');
    await expect(errorToast).toBeVisible();
  });

  test('should handle drag and drop', async ({ page, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('drag-drop.difypkg');
    
    // Create data transfer
    const dataTransfer = await page.evaluateHandle(() => new DataTransfer());
    
    // Dispatch drag events
    const dropZone = page.locator('[data-testid="drop-zone"], .border-dashed');
    
    await dropZone.dispatchEvent('dragenter', { dataTransfer });
    await expect(dropZone).toHaveClass(/border-blue-500|hover/);
    
    await dropZone.dispatchEvent('dragleave', { dataTransfer });
    await expect(dropZone).not.toHaveClass(/border-blue-500|hover/);
  });

  test('should show file preview after selection', async ({ page, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('preview.difypkg');
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFile);
    
    // Should show file name
    const fileName = page.locator('text=preview.difypkg');
    await expect(fileName).toBeVisible();
    
    // Should enable submit button
    const submitButton = page.locator('button', { hasText: 'Start Repackaging' });
    await expect(submitButton).toBeEnabled();
  });

  test('should handle upload with platform selection', async ({ homePage, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('platform-test.difypkg');
    
    await homePage.uploadFile(testFile, TEST_DATA.platforms[0]);
    
    // Should start processing with selected platform
    const taskStatus = homePage.page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should handle upload with custom suffix', async ({ homePage, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('suffix-test.difypkg');
    
    await homePage.uploadFile(testFile, undefined, TEST_DATA.suffixes.custom);
    
    // Should start processing with custom suffix
    const taskStatus = homePage.page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should handle upload errors', async ({ page, homePage, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('error-test.difypkg');
    
    // Mock upload error
    await page.route('**/api/v1/tasks/upload', (route) => {
      route.fulfill({
        status: 413,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'File too large' })
      });
    });
    
    await homePage.uploadFile(testFile);
    
    // Should show error
    const errorToast = await homePage.waitForToast('File too large');
    await expect(errorToast).toBeVisible();
  });

  test('should clear file selection', async ({ page, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('clear-test.difypkg');
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFile);
    
    // Should show file name
    await expect(page.locator('text=clear-test.difypkg')).toBeVisible();
    
    // Clear selection
    const clearButton = page.locator('button[aria-label="Clear file"]');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      
      // File should be cleared
      await expect(page.locator('text=clear-test.difypkg')).not.toBeVisible();
    }
  });

  test('should handle network interruption during upload', async ({ page, homePage, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('network-test.difypkg');
    
    // Simulate network error
    await page.route('**/api/v1/tasks/upload', async (route) => {
      await page.waitForTimeout(1000); // Simulate upload in progress
      await route.abort('failed');
    });
    
    await homePage.uploadFile(testFile);
    
    // Should show network error
    const errorToast = await homePage.getToastMessage();
    expect(errorToast).toContain('error');
  });

  test('should show upload progress', async ({ page, testHelpers }) => {
    const testFile = await testHelpers.createTestDifypkgFile('progress-test.difypkg');
    
    // Mock slow upload
    await page.route('**/api/v1/tasks/upload', async (route) => {
      await page.waitForTimeout(2000); // Simulate slow upload
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ task_id: 'test-123', status: 'pending' })
      });
    });
    
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFile);
    
    const submitButton = page.locator('button', { hasText: 'Start Repackaging' });
    await submitButton.click();
    
    // Should show loading state
    const loadingIndicator = page.locator('[data-testid="loading-spinner"], .animate-spin');
    await expect(loadingIndicator).toBeVisible();
  });

  test('should support multiple file formats', async ({ page, testHelpers }) => {
    // Test that only .difypkg files are accepted
    const fileInput = page.locator('input[type="file"]');
    const acceptAttribute = await fileInput.getAttribute('accept');
    expect(acceptAttribute).toBe('.difypkg');
  });
});