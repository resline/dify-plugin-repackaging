import { Page, Locator, Download } from '@playwright/test';

// Base Page Object
export abstract class BasePage {
  constructor(protected page: Page) {}
  
  async waitForLoadComplete() {
    await this.page.waitForLoadState('networkidle');
  }
  
  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `screenshots/${name}.png`,
      fullPage: true 
    });
  }

  async waitForToast(message: string, timeout = 5000) {
    await this.page.getByText(message).waitFor({ state: 'visible', timeout });
  }
}

// Main Repackaging Page
export class RepackagingPage extends BasePage {
  // Tab locators
  readonly urlTab = this.page.getByRole('tab', { name: 'URL' });
  readonly marketplaceTab = this.page.getByRole('tab', { name: 'Marketplace' });
  readonly fileTab = this.page.getByRole('tab', { name: 'File Upload' });
  readonly completedTab = this.page.getByRole('tab', { name: 'Completed' });
  
  // URL form elements
  readonly urlInput = this.page.getByPlaceholder('https://github.com/.../plugin.difypkg or https://marketplace.dify.ai/plugins/...');
  readonly platformSelect = this.page.getByLabel('Platform (optional)');
  readonly suffixInput = this.page.getByLabel('Suffix');
  readonly submitButton = this.page.getByRole('button', { name: 'Start Repackaging' });
  
  // Theme toggle
  readonly themeToggle = this.page.getByTestId('theme-toggle');
  
  async selectTab(tab: 'url' | 'marketplace' | 'file' | 'completed') {
    const tabMap = {
      url: this.urlTab,
      marketplace: this.marketplaceTab,
      file: this.fileTab,
      completed: this.completedTab
    };
    await tabMap[tab].click();
    await this.page.waitForTimeout(300); // Wait for tab animation
  }
  
  async submitUrlRepackaging(url: string, platform?: string, suffix?: string) {
    await this.urlInput.fill(url);
    
    if (platform) {
      await this.platformSelect.selectOption(platform);
    }
    
    if (suffix) {
      await this.suffixInput.clear();
      await this.suffixInput.fill(suffix);
    }
    
    await this.submitButton.click();
  }

  async toggleTheme() {
    await this.themeToggle.click();
  }

  async isDarkMode(): Promise<boolean> {
    const htmlClass = await this.page.locator('html').getAttribute('class');
    return htmlClass?.includes('dark') || false;
  }
}

// Task Status Page
export class TaskStatusPage extends BasePage {
  readonly progressBar = this.page.getByRole('progressbar');
  readonly statusText = this.page.getByTestId('task-status');
  readonly logViewer = this.page.getByTestId('log-viewer');
  readonly downloadButton = this.page.getByRole('button', { name: /Download.*\.difypkg/ });
  readonly newTaskButton = this.page.getByRole('button', { name: 'Start New Task' });
  readonly copyLinkButton = this.page.getByRole('button', { name: /Copy (Download )?Link/ });
  
  async waitForCompletion(timeout = 120000) {
    await this.downloadButton.waitFor({ 
      state: 'visible', 
      timeout 
    });
  }
  
  async getProgress(): Promise<number> {
    const value = await this.progressBar.getAttribute('aria-valuenow');
    return parseInt(value || '0');
  }
  
  async getStatus(): Promise<string> {
    return await this.statusText.textContent() || '';
  }
  
  async getLogs(): Promise<string[]> {
    const logLines = await this.logViewer.locator('.log-line').allTextContents();
    return logLines;
  }
  
  async downloadFile(): Promise<Download> {
    const downloadPromise = this.page.waitForEvent('download');
    await this.downloadButton.click();
    return await downloadPromise;
  }

  async copyDownloadLink() {
    await this.copyLinkButton.click();
    // Verify clipboard content if needed
    const clipboardText = await this.page.evaluate(() => navigator.clipboard.readText());
    return clipboardText;
  }

  async startNewTask() {
    await this.newTaskButton.click();
  }
}

// Marketplace Browser Page
export class MarketplacePage extends BasePage {
  readonly searchInput = this.page.getByPlaceholder('Search plugins...');
  readonly pluginCards = this.page.getByTestId('plugin-card');
  readonly loadMoreButton = this.page.getByRole('button', { name: 'Load More' });
  readonly loadingSpinner = this.page.getByTestId('loading-spinner');
  readonly noResultsMessage = this.page.getByText('No plugins found');
  
  // Plugin detail modal
  readonly versionSelect = this.page.getByLabel('Version');
  readonly platformSelectModal = this.page.getByLabel('Platform', { exact: true });
  readonly repackageButton = this.page.getByRole('button', { name: 'Repackage Plugin' });
  readonly closeModalButton = this.page.getByRole('button', { name: 'Close' });
  
  async searchPlugin(query: string) {
    await this.searchInput.clear();
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(500); // Wait for debounce
    
    // Wait for loading to complete
    await this.waitForSearchResults();
  }
  
  async waitForSearchResults() {
    // Wait for loading spinner to appear and disappear
    await this.loadingSpinner.waitFor({ state: 'visible', timeout: 2000 }).catch(() => {});
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
  }
  
  async selectPlugin(author: string, name: string) {
    const pluginCard = this.page
      .getByTestId('plugin-card')
      .filter({ hasText: `${author}/${name}` });
    
    await pluginCard.click();
    
    // Wait for modal to open
    await this.versionSelect.waitFor({ state: 'visible' });
  }
  
  async getPluginCount(): Promise<number> {
    return await this.pluginCards.count();
  }
  
  async selectVersion(version: string) {
    await this.versionSelect.selectOption(version);
  }
  
  async selectPlatform(platform: string) {
    await this.platformSelectModal.selectOption(platform);
  }
  
  async submitRepackaging() {
    await this.repackageButton.click();
  }
  
  async loadMore() {
    if (await this.loadMoreButton.isVisible()) {
      await this.loadMoreButton.click();
      await this.waitForSearchResults();
    }
  }

  async getPluginInfo(index: number) {
    const card = this.pluginCards.nth(index);
    return {
      title: await card.locator('.plugin-title').textContent(),
      author: await card.locator('.plugin-author').textContent(),
      description: await card.locator('.plugin-description').textContent(),
      version: await card.locator('.plugin-version').textContent(),
    };
  }
}

// File Upload Page
export class FileUploadPage extends BasePage {
  readonly fileInput = this.page.locator('input[type="file"]');
  readonly dropZone = this.page.getByTestId('drop-zone');
  readonly platformSelect = this.page.getByLabel('Platform (optional)');
  readonly suffixInput = this.page.getByLabel('Suffix');
  readonly uploadButton = this.page.getByRole('button', { name: 'Upload and Repackage' });
  readonly fileInfo = this.page.getByTestId('file-info');
  
  async uploadFile(filePath: string | { name: string; mimeType: string; buffer: Buffer }) {
    await this.fileInput.setInputFiles(filePath);
  }
  
  async dragAndDropFile(filePath: string) {
    // Create a data transfer
    const dataTransfer = await this.page.evaluateHandle(() => new DataTransfer());
    
    // Dispatch drag events
    await this.dropZone.dispatchEvent('dragenter', { dataTransfer });
    await this.dropZone.dispatchEvent('dragover', { dataTransfer });
    
    // Set files and drop
    await this.fileInput.setInputFiles(filePath);
    await this.dropZone.dispatchEvent('drop', { dataTransfer });
  }
  
  async selectPlatform(platform: string) {
    await this.platformSelect.selectOption(platform);
  }
  
  async setSuffix(suffix: string) {
    await this.suffixInput.clear();
    await this.suffixInput.fill(suffix);
  }
  
  async submitUpload() {
    await this.uploadButton.click();
  }
  
  async getFileInfoText(): Promise<string> {
    return await this.fileInfo.textContent() || '';
  }

  async clearFile() {
    // Clear the file input
    await this.fileInput.evaluate((input: HTMLInputElement) => {
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }
}

// Completed Files Page
export class CompletedFilesPage extends BasePage {
  readonly completedFilesList = this.page.getByTestId('completed-files-list');
  readonly fileItems = this.page.getByTestId('completed-file-item');
  readonly emptyMessage = this.page.getByText('No completed files yet');
  readonly refreshButton = this.page.getByRole('button', { name: 'Refresh' });
  
  async getCompletedFilesCount(): Promise<number> {
    if (await this.emptyMessage.isVisible()) {
      return 0;
    }
    return await this.fileItems.count();
  }
  
  async downloadFileByIndex(index: number): Promise<Download> {
    const downloadButton = this.fileItems.nth(index).getByRole('button', { name: /Download/ });
    const downloadPromise = this.page.waitForEvent('download');
    await downloadButton.click();
    return await downloadPromise;
  }
  
  async getFileInfo(index: number) {
    const item = this.fileItems.nth(index);
    return {
      filename: await item.locator('.file-name').textContent(),
      size: await item.locator('.file-size').textContent(),
      date: await item.locator('.file-date').textContent(),
      pluginInfo: await item.locator('.plugin-info').textContent(),
    };
  }
  
  async refresh() {
    await this.refreshButton.click();
    await this.page.waitForTimeout(500); // Wait for refresh
  }

  async copyDownloadLink(index: number) {
    const copyButton = this.fileItems.nth(index).getByRole('button', { name: /Copy Link/ });
    await copyButton.click();
    return await this.page.evaluate(() => navigator.clipboard.readText());
  }
}

// WebSocket Status Component
export class WebSocketStatus extends BasePage {
  readonly statusIndicator = this.page.getByTestId('ws-status-indicator');
  readonly statusText = this.page.getByTestId('ws-status-text');
  readonly reconnectButton = this.page.getByRole('button', { name: 'Reconnect' });
  
  async getConnectionStatus(): Promise<'connected' | 'disconnected' | 'connecting'> {
    const classes = await this.statusIndicator.getAttribute('class') || '';
    if (classes.includes('connected')) return 'connected';
    if (classes.includes('connecting')) return 'connecting';
    return 'disconnected';
  }
  
  async waitForConnection(timeout = 10000) {
    await this.page.waitForFunction(
      () => {
        const indicator = document.querySelector('[data-testid="ws-status-indicator"]');
        return indicator?.classList.contains('connected');
      },
      { timeout }
    );
  }
  
  async reconnect() {
    if (await this.reconnectButton.isVisible()) {
      await this.reconnectButton.click();
      await this.waitForConnection();
    }
  }
}