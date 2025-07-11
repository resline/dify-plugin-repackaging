import { Page, expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class TaskStatusPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  // Task status monitoring
  async waitForTaskToStart() {
    const statusElement = this.page.locator('[data-testid="task-status"]');
    await statusElement.waitFor({ state: 'visible' });
    
    // Wait for status to change from initial state
    await expect(statusElement).not.toHaveText('Initializing...', { timeout: 10000 });
  }

  async waitForTaskCompletion(timeout: number = 60000) {
    const statusElement = this.page.locator('[data-testid="task-status"]');
    
    // Wait for success status
    await expect(statusElement).toHaveText(/Completed|Success/i, { timeout });
    
    // Wait for confetti animation if present
    const confetti = this.page.locator('[data-testid="confetti"]');
    if (await confetti.isVisible()) {
      await this.page.waitForTimeout(2000); // Let confetti animation play
    }
  }

  async waitForTaskError(timeout: number = 30000) {
    const statusElement = this.page.locator('[data-testid="task-status"]');
    await expect(statusElement).toHaveText(/Error|Failed/i, { timeout });
  }

  async getTaskStatus() {
    const statusElement = this.page.locator('[data-testid="task-status"]');
    return await statusElement.textContent();
  }

  async getTaskProgress() {
    const progressBar = this.page.locator('[role="progressbar"]');
    if (await progressBar.isVisible()) {
      return await progressBar.getAttribute('aria-valuenow');
    }
    return null;
  }

  // Log viewer
  async isLogViewerVisible() {
    const logViewer = this.page.locator('[data-testid="log-viewer"]');
    return await logViewer.isVisible();
  }

  async getLogEntries() {
    const logEntries = this.page.locator('[data-testid="log-entry"]');
    const entries = [];
    const count = await logEntries.count();
    
    for (let i = 0; i < count; i++) {
      const entry = logEntries.nth(i);
      const level = await entry.getAttribute('data-log-level');
      const message = await entry.textContent();
      entries.push({ level, message });
    }
    
    return entries;
  }

  async waitForLogMessage(expectedMessage: string, timeout: number = 10000) {
    const logEntry = this.page.locator('[data-testid="log-entry"]', { hasText: expectedMessage });
    await logEntry.waitFor({ state: 'visible', timeout });
  }

  async scrollToLatestLog() {
    const scrollButton = this.page.locator('button', { hasText: 'Scroll to bottom' });
    if (await scrollButton.isVisible()) {
      await scrollButton.click();
    }
  }

  // File download
  async isDownloadButtonVisible() {
    const downloadButton = this.page.locator('[data-testid="download-result-button"]');
    return await downloadButton.isVisible();
  }

  async downloadResult() {
    const downloadButton = this.page.locator('[data-testid="download-result-button"]');
    await downloadButton.waitFor({ state: 'visible' });
    
    // Set up download promise before clicking
    const downloadPromise = this.page.waitForEvent('download');
    await downloadButton.click();
    
    const download = await downloadPromise;
    return download;
  }

  async getDownloadFileName() {
    const fileNameElement = this.page.locator('[data-testid="result-filename"]');
    if (await fileNameElement.isVisible()) {
      return await fileNameElement.textContent();
    }
    return null;
  }

  // Error handling
  async getErrorMessage() {
    const errorElement = this.page.locator('[data-testid="error-message"]');
    if (await errorElement.isVisible()) {
      return await errorElement.textContent();
    }
    return null;
  }

  async clickRetryButton() {
    const retryButton = this.page.locator('button', { hasText: 'Retry' });
    await retryButton.click();
  }

  async clickNewTaskButton() {
    const newTaskButton = this.page.locator('button', { hasText: 'New Task' });
    await newTaskButton.click();
  }

  // WebSocket status
  async getWebSocketStatus() {
    const wsIndicator = this.page.locator('[data-testid="websocket-status"]');
    const isConnected = await wsIndicator.getAttribute('data-connected');
    return isConnected === 'true' ? 'connected' : 'disconnected';
  }

  async waitForWebSocketReconnection(timeout: number = 10000) {
    const wsIndicator = this.page.locator('[data-testid="websocket-status"]');
    await expect(wsIndicator).toHaveAttribute('data-connected', 'true', { timeout });
  }

  // Task details
  async getTaskId() {
    const taskIdElement = this.page.locator('[data-testid="task-id"]');
    if (await taskIdElement.isVisible()) {
      return await taskIdElement.textContent();
    }
    return null;
  }

  async getProcessingTime() {
    const timeElement = this.page.locator('[data-testid="processing-time"]');
    if (await timeElement.isVisible()) {
      return await timeElement.textContent();
    }
    return null;
  }

  // Platform and suffix info
  async getTaskPlatform() {
    const platformElement = this.page.locator('[data-testid="task-platform"]');
    if (await platformElement.isVisible()) {
      return await platformElement.textContent();
    }
    return null;
  }

  async getTaskSuffix() {
    const suffixElement = this.page.locator('[data-testid="task-suffix"]');
    if (await suffixElement.isVisible()) {
      return await suffixElement.textContent();
    }
    return null;
  }
}