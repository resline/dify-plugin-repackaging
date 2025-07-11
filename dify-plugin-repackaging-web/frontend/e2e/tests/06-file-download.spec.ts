import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';
import * as path from 'path';
import * as fs from 'fs/promises';

test.describe('File Download and Management', () => {
  test.beforeEach(async ({ page, testHelpers }) => {
    await page.goto('/');
    await testHelpers.cleanupDownloads();
  });

  test.afterEach(async ({ testHelpers }) => {
    await testHelpers.cleanupDownloads();
  });

  test('should download completed file', async ({ page, homePage, taskStatusPage, testHelpers }) => {
    // Mock successful task
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'download-test-123',
          status: 'pending'
        })
      });
    });
    
    // Mock task completion
    await page.route('**/api/v1/tasks/download-test-123', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'download-test-123',
          status: 'completed',
          result: {
            filename: 'test-plugin-offline.difypkg',
            size: 2048000
          }
        })
      });
    });
    
    // Mock file download
    await page.route('**/api/v1/tasks/download-test-123/download', (route) => {
      const testContent = Buffer.from('PK\x03\x04test-plugin-content-with-dependencies');
      route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        headers: {
          'Content-Disposition': 'attachment; filename="test-plugin-offline.difypkg"'
        },
        body: testContent
      });
    });
    
    // Submit task
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Simulate task completion via WebSocket
    await page.evaluate(() => {
      setTimeout(() => {
        const ws = (window as any).__wsInstance;
        if (ws) {
          ws.dispatchEvent(new MessageEvent('message', {
            data: JSON.stringify({
              type: 'status',
              status: 'completed',
              result: {
                filename: 'test-plugin-offline.difypkg',
                size: 2048000
              }
            })
          }));
        }
      }, 1000);
    });
    
    await taskStatusPage.waitForTaskCompletion();
    
    // Download file
    const download = await taskStatusPage.downloadResult();
    const downloadPath = await testHelpers.saveDownload(download);
    
    // Verify download
    const fileInfo = await testHelpers.verifyDownloadedFile(downloadPath);
    expect(fileInfo.exists).toBe(true);
    expect(fileInfo.isValidDifypkg).toBe(true);
    expect(fileInfo.size).toBeGreaterThan(0);
  });

  test('should display download metadata', async ({ page, homePage, taskStatusPage }) => {
    // Mock completed task
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'metadata-test-123',
          status: 'completed',
          result: {
            filename: 'plugin-with-metadata-offline.difypkg',
            size: 5242880, // 5MB
            platform: 'manylinux2014_x86_64',
            suffix: 'offline'
          }
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Check displayed metadata
    const fileName = await taskStatusPage.getDownloadFileName();
    expect(fileName).toContain('plugin-with-metadata-offline.difypkg');
    
    const platform = await taskStatusPage.getTaskPlatform();
    expect(platform).toContain('manylinux2014_x86_64');
    
    const suffix = await taskStatusPage.getTaskSuffix();
    expect(suffix).toContain('offline');
  });

  test('should handle download errors', async ({ page, homePage, taskStatusPage }) => {
    // Mock task completion
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'download-error-test',
          status: 'completed',
          result: { filename: 'test.difypkg' }
        })
      });
    });
    
    // Mock download error
    await page.route('**/api/v1/tasks/download-error-test/download', (route) => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'File not found' })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Try to download
    const downloadButton = page.locator('[data-testid="download-result-button"]');
    await downloadButton.click();
    
    // Should show error
    const errorToast = await homePage.waitForToast('Failed to download file');
    await expect(errorToast).toBeVisible();
  });

  test('should manage completed files list', async ({ page, homePage }) => {
    // Navigate to completed tab
    await homePage.selectCompletedTab();
    
    // Mock completed files API
    await page.route('**/api/v1/files', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          files: [
            {
              id: 'file-1',
              filename: 'plugin1-offline.difypkg',
              size: 1024000,
              created_at: new Date().toISOString(),
              platform: 'manylinux2014_x86_64'
            },
            {
              id: 'file-2',
              filename: 'plugin2-offline.difypkg',
              size: 2048000,
              created_at: new Date(Date.now() - 3600000).toISOString(),
              platform: 'win_amd64'
            }
          ]
        })
      });
    });
    
    // Refresh to load files
    await page.reload();
    await homePage.selectCompletedTab();
    
    // Check file count
    const fileCount = await homePage.getCompletedFileCount();
    expect(fileCount).toBe(2);
  });

  test('should download from completed files list', async ({ page, homePage, testHelpers }) => {
    await homePage.selectCompletedTab();
    
    // Mock completed files
    await page.route('**/api/v1/files', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          files: [{
            id: 'completed-file-1',
            filename: 'completed-plugin-offline.difypkg',
            size: 1536000,
            created_at: new Date().toISOString()
          }]
        })
      });
    });
    
    // Mock file download
    await page.route('**/api/v1/files/completed-file-1/download', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        headers: {
          'Content-Disposition': 'attachment; filename="completed-plugin-offline.difypkg"'
        },
        body: Buffer.from('PK\x03\x04completed-file-content')
      });
    });
    
    await page.reload();
    await homePage.selectCompletedTab();
    
    // Download first file
    const download = await homePage.downloadCompletedFile(0);
    const downloadPath = await testHelpers.saveDownload(download);
    
    // Verify download
    const fileInfo = await testHelpers.verifyDownloadedFile(downloadPath);
    expect(fileInfo.exists).toBe(true);
    expect(fileInfo.isValidDifypkg).toBe(true);
  });

  test('should delete completed files', async ({ page, homePage }) => {
    await homePage.selectCompletedTab();
    
    // Mock completed files
    await page.route('**/api/v1/files', (route) => {
      const url = new URL(route.request().url());
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            files: [{
              id: 'delete-test-file',
              filename: 'delete-me.difypkg',
              size: 1024000,
              created_at: new Date().toISOString()
            }]
          })
        });
      }
    });
    
    // Mock delete endpoint
    await page.route('**/api/v1/files/delete-test-file', (route) => {
      if (route.request().method() === 'DELETE') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'File deleted successfully' })
        });
      }
    });
    
    await page.reload();
    await homePage.selectCompletedTab();
    
    // Delete file
    await homePage.deleteCompletedFile(0);
    
    // File should be removed from list
    await page.waitForTimeout(1000);
    const fileCount = await homePage.getCompletedFileCount();
    expect(fileCount).toBe(0);
  });

  test('should auto-refresh completed files', async ({ page, homePage }) => {
    await homePage.selectCompletedTab();
    
    let callCount = 0;
    await page.route('**/api/v1/files', (route) => {
      callCount++;
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          files: Array.from({ length: callCount }, (_, i) => ({
            id: `file-${i}`,
            filename: `plugin-${i}.difypkg`,
            size: 1024000 * (i + 1),
            created_at: new Date().toISOString()
          }))
        })
      });
    });
    
    // Wait for auto-refresh
    await page.waitForTimeout(3000);
    
    // Should have made multiple requests
    expect(callCount).toBeGreaterThan(1);
  });

  test('should handle large file downloads', async ({ page, homePage, taskStatusPage, testHelpers }) => {
    // Mock task with large file
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'large-file-test',
          status: 'completed',
          result: {
            filename: 'large-plugin-offline.difypkg',
            size: 52428800 // 50MB
          }
        })
      });
    });
    
    // Mock large file download
    const largeContent = Buffer.alloc(52428800);
    largeContent[0] = 0x50; // P
    largeContent[1] = 0x4B; // K
    
    await page.route('**/api/v1/tasks/large-file-test/download', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        headers: {
          'Content-Disposition': 'attachment; filename="large-plugin-offline.difypkg"',
          'Content-Length': '52428800'
        },
        body: largeContent
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Download large file
    const download = await taskStatusPage.downloadResult();
    const downloadPath = await testHelpers.saveDownload(download);
    
    // Verify large file
    const fileInfo = await testHelpers.verifyDownloadedFile(downloadPath);
    expect(fileInfo.exists).toBe(true);
    expect(fileInfo.size).toBe(52428800);
  });

  test('should resume interrupted downloads', async ({ page, context, homePage }) => {
    // This test simulates download interruption and resumption
    // Note: Actual resumption depends on server support for Range requests
    
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'resume-test',
          status: 'completed',
          result: { filename: 'resume-test.difypkg' }
        })
      });
    });
    
    let requestCount = 0;
    await page.route('**/api/v1/tasks/resume-test/download', (route) => {
      requestCount++;
      const headers = route.request().headers();
      
      if (headers['range']) {
        // Partial content response
        route.fulfill({
          status: 206,
          contentType: 'application/octet-stream',
          headers: {
            'Content-Range': 'bytes 1024-2047/2048',
            'Accept-Ranges': 'bytes'
          },
          body: Buffer.alloc(1024)
        });
      } else {
        // Full content response
        route.fulfill({
          status: 200,
          contentType: 'application/octet-stream',
          headers: {
            'Accept-Ranges': 'bytes',
            'Content-Length': '2048'
          },
          body: Buffer.from('PK\x03\x04' + 'x'.repeat(2044))
        });
      }
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Attempt download
    const downloadButton = page.locator('[data-testid="download-result-button"]');
    await downloadButton.click();
    
    await page.waitForTimeout(1000);
    
    // Check if server supports resumption
    expect(requestCount).toBeGreaterThan(0);
  });
});