import { Page, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class HomePage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Tab navigation
  async selectUrlTab() {
    await this.clickTab('Direct URL');
  }

  async selectMarketplaceTab() {
    await this.clickTab('Marketplace');
  }

  async selectFileTab() {
    await this.clickTab('File Upload');
  }

  async selectCompletedTab() {
    await this.clickTab('Completed');
  }

  // URL submission
  async submitUrl(url: string, platform?: string, suffix?: string) {
    await this.selectUrlTab();
    
    const urlInput = this.page.locator('input[placeholder*="Enter URL"]');
    await urlInput.fill(url);

    if (platform) {
      await this.selectPlatform(platform);
    }

    if (suffix) {
      const suffixInput = this.page.locator('input[placeholder*="suffix"]');
      await suffixInput.clear();
      await suffixInput.fill(suffix);
    }

    const submitButton = this.page.locator('button', { hasText: 'Start Repackaging' });
    await submitButton.click();
  }

  // Marketplace submission
  async submitMarketplacePlugin(author: string, name: string, version?: string, platform?: string, suffix?: string) {
    await this.selectMarketplaceTab();
    
    // Search for plugin
    const searchInput = this.page.locator('input[placeholder*="Search plugins"]');
    await searchInput.fill(`${author} ${name}`);
    await this.page.waitForTimeout(500); // Debounce delay

    // Select plugin from results
    const pluginCard = this.page.locator('[data-testid="plugin-card"]', { hasText: name }).first();
    await pluginCard.waitFor({ state: 'visible' });
    
    // Select version if specified
    if (version) {
      const versionDropdown = pluginCard.locator('select');
      await versionDropdown.selectOption(version);
    }

    if (platform) {
      await this.selectPlatform(platform);
    }

    if (suffix) {
      const suffixInput = this.page.locator('input[placeholder*="suffix"]');
      await suffixInput.clear();
      await suffixInput.fill(suffix);
    }

    // Click repackage button on the plugin card
    const repackageButton = pluginCard.locator('button', { hasText: 'Repackage' });
    await repackageButton.click();
  }

  // File upload
  async uploadFile(filePath: string, platform?: string, suffix?: string) {
    await this.selectFileTab();

    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);

    if (platform) {
      await this.selectPlatform(platform);
    }

    if (suffix) {
      const suffixInput = this.page.locator('input[placeholder*="suffix"]');
      await suffixInput.clear();
      await suffixInput.fill(suffix);
    }

    const submitButton = this.page.locator('button', { hasText: 'Start Repackaging' });
    await submitButton.click();
  }

  // Platform selection helper
  async selectPlatform(platform: string) {
    const platformButton = this.page.locator('button', { hasText: 'Select Platform' });
    await platformButton.click();

    const platformOption = this.page.locator('[role="option"]', { hasText: platform });
    await platformOption.click();
  }

  // Get current form values
  async getUrlInputValue() {
    const urlInput = this.page.locator('input[placeholder*="Enter URL"]');
    return await urlInput.inputValue();
  }

  async getSuffixInputValue() {
    const suffixInput = this.page.locator('input[placeholder*="suffix"]');
    return await suffixInput.inputValue();
  }

  // Validation helpers
  async isSubmitButtonEnabled() {
    const submitButton = this.page.locator('button', { hasText: 'Start Repackaging' });
    return await submitButton.isEnabled();
  }

  async getValidationError() {
    const errorMessage = this.page.locator('.text-red-500, .text-red-600').first();
    if (await errorMessage.isVisible()) {
      return await errorMessage.textContent();
    }
    return null;
  }

  // Completed files section
  async getCompletedFileCount() {
    await this.page.waitForTimeout(1000); // Wait for files to load
    const fileItems = this.page.locator('[data-testid="completed-file-item"]');
    return await fileItems.count();
  }

  async downloadCompletedFile(index: number = 0) {
    const downloadButton = this.page.locator('[data-testid="download-button"]').nth(index);
    
    // Set up download promise before clicking
    const downloadPromise = this.page.waitForEvent('download');
    await downloadButton.click();
    
    const download = await downloadPromise;
    return download;
  }

  async deleteCompletedFile(index: number = 0) {
    const deleteButton = this.page.locator('[data-testid="delete-button"]').nth(index);
    await deleteButton.click();
    
    // Confirm deletion in dialog
    const confirmButton = this.page.locator('button', { hasText: 'Delete' }).last();
    await confirmButton.click();
  }

  // Helper to check if how-it-works section is visible
  async isHowItWorksVisible() {
    const howItWorks = this.page.locator('h3', { hasText: 'How it works' });
    return await howItWorks.isVisible();
  }

  // Helper to get supported sources
  async getSupportedSources() {
    const sourcesList = this.page.locator('ul').filter({ hasText: 'Dify Marketplace' });
    const items = sourcesList.locator('li');
    const sources = [];
    const count = await items.count();
    
    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      sources.push(text?.trim() || '');
    }
    
    return sources;
  }
}