import { Page, expect } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async navigateTo(path: string = '/') {
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  async getToastMessage() {
    const toast = this.page.locator('[role="alert"]').first();
    await toast.waitFor({ state: 'visible' });
    return await toast.textContent();
  }

  async waitForToast(expectedMessage: string) {
    const toast = this.page.locator('[role="alert"]', { hasText: expectedMessage });
    await toast.waitFor({ state: 'visible' });
    return toast;
  }

  async closeToast() {
    const closeButton = this.page.locator('[role="alert"] button[aria-label="Close"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
  }

  async toggleTheme() {
    const themeToggle = this.page.locator('button[aria-label*="theme"]');
    await themeToggle.click();
  }

  async isInDarkMode() {
    const html = this.page.locator('html');
    const classes = await html.getAttribute('class');
    return classes?.includes('dark') || false;
  }

  async waitForWebSocketConnection() {
    // Wait for WebSocket status indicator to show connected
    const wsStatus = this.page.locator('[data-testid="websocket-status"]');
    await expect(wsStatus).toHaveAttribute('data-connected', 'true', { timeout: 10000 });
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true });
  }

  async waitForElementWithText(selector: string, text: string) {
    const element = this.page.locator(selector, { hasText: text });
    await element.waitFor({ state: 'visible' });
    return element;
  }

  async clickTab(tabName: string) {
    const tab = this.page.locator(`[role="tab"]`, { hasText: tabName });
    await tab.click();
    await expect(tab).toHaveAttribute('aria-selected', 'true');
  }

  async getCurrentTab() {
    const selectedTab = this.page.locator('[role="tab"][aria-selected="true"]');
    return await selectedTab.textContent();
  }

  async waitForLoadingToComplete() {
    // Wait for any loading spinners to disappear
    const loadingIndicators = this.page.locator('[data-testid="loading-spinner"], .animate-spin');
    await expect(loadingIndicators).toHaveCount(0);
  }
}