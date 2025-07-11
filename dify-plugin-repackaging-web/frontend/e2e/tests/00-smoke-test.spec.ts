import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should load the application', async ({ page }) => {
    await page.goto('/');
    
    // Check if page loads
    await expect(page).toHaveTitle(/Dify Plugin Repackaging/);
    
    // Check if main heading is visible
    const heading = page.locator('h2', { hasText: 'Repackage a Dify Plugin' });
    await expect(heading).toBeVisible();
    
    // Check if tabs are present
    const tabs = ['Direct URL', 'Marketplace', 'File Upload', 'Completed'];
    for (const tab of tabs) {
      const tabElement = page.locator('[role="tab"]', { hasText: tab });
      await expect(tabElement).toBeVisible();
    }
  });

  test('should have no console errors', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    expect(errors).toHaveLength(0);
  });

  test('should be responsive', async ({ page }) => {
    // Desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await expect(page.locator('main.max-w-4xl.mx-auto')).toBeVisible();
    
    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('main.max-w-4xl.mx-auto')).toBeVisible();
  });
});