import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('Basic Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load homepage with correct title', async ({ page }) => {
    await expect(page).toHaveTitle(/Dify Plugin Repackaging/i);
    
    const heading = page.locator('h2', { hasText: 'Repackage a Dify Plugin' });
    await expect(heading).toBeVisible();
  });

  test('should display all navigation tabs', async ({ homePage }) => {
    const tabs = ['Direct URL', 'Marketplace', 'File Upload', 'Completed'];
    
    for (const tab of tabs) {
      const tabElement = homePage.page.locator('[role="tab"]', { hasText: tab });
      await expect(tabElement).toBeVisible();
    }
  });

  test('should switch between tabs correctly', async ({ homePage }) => {
    // Start on Direct URL tab
    await expect(await homePage.getCurrentTab()).toContain('Direct URL');
    
    // Switch to Marketplace
    await homePage.selectMarketplaceTab();
    await expect(await homePage.getCurrentTab()).toContain('Marketplace');
    
    // Switch to File Upload
    await homePage.selectFileTab();
    await expect(await homePage.getCurrentTab()).toContain('File Upload');
    
    // Switch to Completed
    await homePage.selectCompletedTab();
    await expect(await homePage.getCurrentTab()).toContain('Completed');
  });

  test('should persist tab selection in localStorage', async ({ page, homePage, testHelpers }) => {
    // Select Marketplace tab
    await homePage.selectMarketplaceTab();
    
    // Check localStorage
    const savedTab = await testHelpers.getLocalStorage(page, 'lastSelectedTab');
    expect(savedTab).toBe('marketplace');
    
    // Reload page
    await page.reload();
    
    // Should remain on Marketplace tab
    await expect(await homePage.getCurrentTab()).toContain('Marketplace');
  });

  test('should toggle theme between light and dark mode', async ({ page, homePage }) => {
    // Start in light mode
    expect(await homePage.isInDarkMode()).toBe(false);
    
    // Toggle to dark mode
    await homePage.toggleTheme();
    expect(await homePage.isInDarkMode()).toBe(true);
    
    // Toggle back to light mode
    await homePage.toggleTheme();
    expect(await homePage.isInDarkMode()).toBe(false);
  });

  test('should display how-it-works section', async ({ homePage }) => {
    await expect(await homePage.isHowItWorksVisible()).toBe(true);
    
    const steps = homePage.page.locator('ol li');
    await expect(steps).toHaveCount(4);
  });

  test('should display supported sources', async ({ homePage }) => {
    const sources = await homePage.getSupportedSources();
    
    expect(sources).toContain('• Dify Marketplace (marketplace.dify.ai)');
    expect(sources).toContain('• GitHub Releases (github.com)');
    expect(sources).toContain('• Direct URLs to .difypkg files');
    expect(sources).toContain('• Local .difypkg files (upload from your computer)');
  });

  test('should have responsive layout', async ({ page }) => {
    // Desktop view
    await page.setViewportSize({ width: 1920, height: 1080 });
    const desktopLayout = page.locator('main.max-w-4xl.mx-auto');
    await expect(desktopLayout).toBeVisible();
    
    // Mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(desktopLayout).toBeVisible();
    
    // Tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(desktopLayout).toBeVisible();
  });

  test('should handle deep links', async ({ page, homePage }) => {
    // Test URL deep link
    await page.goto('/?type=url&url=' + encodeURIComponent(TEST_DATA.urls.validDifypkg));
    await expect(await homePage.getCurrentTab()).toContain('Direct URL');
    await expect(await homePage.getUrlInputValue()).toBe(TEST_DATA.urls.validDifypkg);
    
    // Test marketplace deep link
    await page.goto('/?type=marketplace&author=langgenius&name=agent&version=0.0.9');
    await expect(await homePage.getCurrentTab()).toContain('Marketplace');
  });

  test('should show WebSocket connection status', async ({ page, homePage }) => {
    const wsStatus = page.locator('[data-testid="websocket-status"]');
    await expect(wsStatus).toBeVisible();
  });
});