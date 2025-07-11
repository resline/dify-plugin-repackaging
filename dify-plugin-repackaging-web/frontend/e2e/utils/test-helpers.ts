import { Page, Download } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as crypto from 'crypto';

export class TestHelpers {
  /**
   * Create a test .difypkg file
   */
  static async createTestDifypkgFile(fileName: string = 'test-plugin.difypkg'): Promise<string> {
    const testDataDir = path.join(process.cwd(), 'e2e', 'test-data');
    await fs.mkdir(testDataDir, { recursive: true });
    
    const filePath = path.join(testDataDir, fileName);
    
    // Create a minimal zip file structure for .difypkg
    // In a real scenario, this would be a proper zip file
    const content = Buffer.from('PK\x03\x04test-plugin-content');
    await fs.writeFile(filePath, content);
    
    return filePath;
  }

  /**
   * Clean up test data directory
   */
  static async cleanupTestData() {
    const testDataDir = path.join(process.cwd(), 'e2e', 'test-data');
    try {
      await fs.rm(testDataDir, { recursive: true, force: true });
    } catch (error) {
      // Directory might not exist
    }
  }

  /**
   * Generate a unique identifier for test runs
   */
  static generateTestId(): string {
    return `test-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
  }

  /**
   * Wait for download and save to test directory
   */
  static async saveDownload(download: Download, customName?: string): Promise<string> {
    const downloadsDir = path.join(process.cwd(), 'e2e', 'downloads');
    await fs.mkdir(downloadsDir, { recursive: true });
    
    const fileName = customName || download.suggestedFilename();
    const filePath = path.join(downloadsDir, fileName);
    
    await download.saveAs(filePath);
    return filePath;
  }

  /**
   * Verify downloaded file
   */
  static async verifyDownloadedFile(filePath: string): Promise<{
    exists: boolean;
    size: number;
    isValidDifypkg: boolean;
  }> {
    try {
      const stats = await fs.stat(filePath);
      const content = await fs.readFile(filePath);
      
      // Check if it's a valid zip file (starts with PK)
      const isValidDifypkg = content[0] === 0x50 && content[1] === 0x4B;
      
      return {
        exists: true,
        size: stats.size,
        isValidDifypkg
      };
    } catch (error) {
      return {
        exists: false,
        size: 0,
        isValidDifypkg: false
      };
    }
  }

  /**
   * Clean up downloads directory
   */
  static async cleanupDownloads() {
    const downloadsDir = path.join(process.cwd(), 'e2e', 'downloads');
    try {
      await fs.rm(downloadsDir, { recursive: true, force: true });
    } catch (error) {
      // Directory might not exist
    }
  }

  /**
   * Mock API responses
   */
  static async mockApiResponse(page: Page, endpoint: string, response: any) {
    await page.route(`**/api/v1${endpoint}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response)
      });
    });
  }

  /**
   * Mock API error
   */
  static async mockApiError(page: Page, endpoint: string, status: number = 500, message: string = 'Server error') {
    await page.route(`**/api/v1${endpoint}`, (route) => {
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: message })
      });
    });
  }

  /**
   * Wait for network idle
   */
  static async waitForNetworkIdle(page: Page, timeout: number = 5000) {
    await page.waitForLoadState('networkidle', { timeout });
  }

  /**
   * Take screenshot with timestamp
   */
  static async takeScreenshot(page: Page, name: string) {
    const screenshotsDir = path.join(process.cwd(), 'e2e', 'screenshots');
    await fs.mkdir(screenshotsDir, { recursive: true });
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `${name}-${timestamp}.png`;
    const filePath = path.join(screenshotsDir, fileName);
    
    await page.screenshot({ path: filePath, fullPage: true });
    return filePath;
  }

  /**
   * Get localStorage data
   */
  static async getLocalStorage(page: Page, key?: string) {
    return await page.evaluate((storageKey) => {
      if (storageKey) {
        return localStorage.getItem(storageKey);
      }
      return Object.fromEntries(
        Object.entries(localStorage).map(([k, v]) => [k, v])
      );
    }, key);
  }

  /**
   * Set localStorage data
   */
  static async setLocalStorage(page: Page, key: string, value: string) {
    await page.evaluate(([k, v]) => {
      localStorage.setItem(k, v);
    }, [key, value]);
  }

  /**
   * Clear localStorage
   */
  static async clearLocalStorage(page: Page) {
    await page.evaluate(() => {
      localStorage.clear();
    });
  }

  /**
   * Simulate slow network
   */
  static async simulateSlowNetwork(page: Page) {
    await page.context().route('**/*', (route) => {
      setTimeout(() => route.continue(), 2000);
    });
  }

  /**
   * Simulate offline mode
   */
  static async simulateOffline(page: Page) {
    await page.context().setOffline(true);
  }

  /**
   * Restore online mode
   */
  static async simulateOnline(page: Page) {
    await page.context().setOffline(false);
  }

  /**
   * Get console logs
   */
  static setupConsoleListener(page: Page): { logs: any[], errors: any[] } {
    const logs: any[] = [];
    const errors: any[] = [];
    
    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();
      const location = msg.location();
      
      const logEntry = { type, text, location, timestamp: Date.now() };
      
      if (type === 'error') {
        errors.push(logEntry);
      } else {
        logs.push(logEntry);
      }
    });
    
    return { logs, errors };
  }

  /**
   * Wait for specific console message
   */
  static async waitForConsoleMessage(page: Page, expectedMessage: string, timeout: number = 5000): Promise<boolean> {
    return new Promise((resolve) => {
      let timeoutId: NodeJS.Timeout;
      
      const handler = (msg: any) => {
        if (msg.text().includes(expectedMessage)) {
          clearTimeout(timeoutId);
          page.off('console', handler);
          resolve(true);
        }
      };
      
      page.on('console', handler);
      
      timeoutId = setTimeout(() => {
        page.off('console', handler);
        resolve(false);
      }, timeout);
    });
  }

  /**
   * Check for JavaScript errors
   */
  static async checkForJsErrors(page: Page): Promise<string[]> {
    const errors: string[] = [];
    
    page.on('pageerror', (error) => {
      errors.push(error.message);
    });
    
    // Also check console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    return errors;
  }
}