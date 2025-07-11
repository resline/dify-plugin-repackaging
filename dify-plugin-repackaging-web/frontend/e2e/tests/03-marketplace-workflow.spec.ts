import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('Marketplace Workflow', () => {
  test.beforeEach(async ({ page, homePage }) => {
    await page.goto('/');
    await homePage.selectMarketplaceTab();
  });

  test('should search for plugins', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await expect(searchInput).toBeVisible();
    
    // Type search query
    await searchInput.fill(TEST_DATA.marketplace.searchTerms.valid);
    
    // Wait for debounce and results
    await page.waitForTimeout(600);
    
    // Should show plugin cards
    const pluginCards = page.locator('[data-testid="plugin-card"]');
    await expect(pluginCards).toHaveCount(1); // At least one result
  });

  test('should display plugin details', async ({ page }) => {
    // Mock marketplace API
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [{
            author: TEST_DATA.marketplace.validPlugin.author,
            name: TEST_DATA.marketplace.validPlugin.name,
            description: 'Test plugin description',
            latest_version: TEST_DATA.marketplace.validPlugin.version,
            versions: ['0.0.9', '0.0.8', '0.0.7']
          }]
        })
      });
    });
    
    // Search for plugin
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(TEST_DATA.marketplace.searchTerms.valid);
    await page.waitForTimeout(600);
    
    // Check plugin card content
    const pluginCard = page.locator('[data-testid="plugin-card"]').first();
    await expect(pluginCard).toContainText(TEST_DATA.marketplace.validPlugin.name);
    await expect(pluginCard).toContainText(TEST_DATA.marketplace.validPlugin.author);
    
    // Should have version dropdown
    const versionDropdown = pluginCard.locator('select');
    await expect(versionDropdown).toBeVisible();
  });

  test('should handle version selection', async ({ page }) => {
    // Mock marketplace API
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [{
            author: TEST_DATA.marketplace.validPlugin.author,
            name: TEST_DATA.marketplace.validPlugin.name,
            latest_version: '0.0.9',
            versions: ['0.0.9', '0.0.8', '0.0.7']
          }]
        })
      });
    });
    
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(TEST_DATA.marketplace.searchTerms.valid);
    await page.waitForTimeout(600);
    
    const pluginCard = page.locator('[data-testid="plugin-card"]').first();
    const versionDropdown = pluginCard.locator('select');
    
    // Select different version
    await versionDropdown.selectOption('0.0.8');
    await expect(versionDropdown).toHaveValue('0.0.8');
  });

  test('should submit marketplace plugin', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock marketplace API
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [{
            author: TEST_DATA.marketplace.validPlugin.author,
            name: TEST_DATA.marketplace.validPlugin.name,
            latest_version: TEST_DATA.marketplace.validPlugin.version,
            versions: [TEST_DATA.marketplace.validPlugin.version]
          }]
        })
      });
    });
    
    // Mock task creation
    await page.route('**/api/v1/tasks/marketplace', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'pending'
        })
      });
    });
    
    await homePage.submitMarketplacePlugin(
      TEST_DATA.marketplace.validPlugin.author,
      TEST_DATA.marketplace.validPlugin.name,
      TEST_DATA.marketplace.validPlugin.version
    );
    
    // Should navigate to task status
    await taskStatusPage.waitForTaskToStart();
  });

  test('should handle empty search results', async ({ page }) => {
    // Mock empty results
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ plugins: [] })
      });
    });
    
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(TEST_DATA.marketplace.searchTerms.noResults);
    await page.waitForTimeout(600);
    
    // Should show no results message
    const noResults = page.locator('text=No plugins found');
    await expect(noResults).toBeVisible();
  });

  test('should handle marketplace API errors', async ({ page, homePage }) => {
    // Mock API error
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Marketplace unavailable' })
      });
    });
    
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(TEST_DATA.marketplace.searchTerms.valid);
    await page.waitForTimeout(600);
    
    // Should show error message
    const errorMessage = page.locator('text=Failed to load plugins');
    await expect(errorMessage).toBeVisible();
  });

  test('should paginate results', async ({ page }) => {
    // Mock paginated results
    const mockPlugins = Array.from({ length: 25 }, (_, i) => ({
      author: `author${i}`,
      name: `plugin${i}`,
      latest_version: '1.0.0',
      versions: ['1.0.0']
    }));
    
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      const url = new URL(route.request().url());
      const page = parseInt(url.searchParams.get('page') || '1');
      const perPage = 10;
      const start = (page - 1) * perPage;
      const end = start + perPage;
      
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: mockPlugins.slice(start, end),
          total: mockPlugins.length,
          page,
          per_page: perPage
        })
      });
    });
    
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill('plugin');
    await page.waitForTimeout(600);
    
    // Should show first page
    const pluginCards = page.locator('[data-testid="plugin-card"]');
    await expect(pluginCards).toHaveCount(10);
    
    // Should have pagination controls
    const nextButton = page.locator('button', { hasText: 'Next' });
    await expect(nextButton).toBeVisible();
    
    // Go to next page
    await nextButton.click();
    await expect(pluginCards).toHaveCount(10);
  });

  test('should handle marketplace deep links', async ({ page }) => {
    // Mock marketplace API
    await page.route('**/api/v1/marketplace/plugins*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          plugins: [{
            author: TEST_DATA.marketplace.validPlugin.author,
            name: TEST_DATA.marketplace.validPlugin.name,
            latest_version: TEST_DATA.marketplace.validPlugin.version,
            versions: [TEST_DATA.marketplace.validPlugin.version]
          }]
        })
      });
    });
    
    // Mock task creation
    await page.route('**/api/v1/tasks/marketplace', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'test-task-123',
          status: 'pending'
        })
      });
    });
    
    // Navigate with marketplace deep link
    await page.goto(`/?type=marketplace&author=${TEST_DATA.marketplace.validPlugin.author}&name=${TEST_DATA.marketplace.validPlugin.name}&version=${TEST_DATA.marketplace.validPlugin.version}`);
    
    // Should auto-submit and show task status
    const taskStatus = page.locator('[data-testid="task-status"]');
    await expect(taskStatus).toBeVisible({ timeout: 10000 });
  });

  test('should remember last search', async ({ page, testHelpers }) => {
    const searchTerm = 'test plugin search';
    
    // Search for plugin
    const searchInput = page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(searchTerm);
    await page.waitForTimeout(600);
    
    // Switch to another tab
    await page.locator('[role="tab"]', { hasText: 'Direct URL' }).click();
    
    // Come back to marketplace
    await page.locator('[role="tab"]', { hasText: 'Marketplace' }).click();
    
    // Search should be preserved
    await expect(searchInput).toHaveValue(searchTerm);
  });
});