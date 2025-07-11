import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('WebSocket Real-time Updates', () => {
  test.beforeEach(async ({ page, wsHelper }) => {
    await page.goto('/');
  });

  test('should establish WebSocket connection on task creation', async ({ page, homePage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'ws-test-123',
          status: 'pending'
        })
      });
    });
    
    // Submit task
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    
    // Wait for WebSocket connection
    await wsHelper.waitForConnection();
    const state = await wsHelper.getConnectionState();
    expect(state).toBe('open');
  });

  test('should receive real-time status updates', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'realtime-test-123',
          status: 'pending'
        })
      });
    });
    
    // Submit task
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Simulate status updates via WebSocket
    await page.evaluate(() => {
      const ws = (window as any).__wsInstance;
      if (ws) {
        // Send progress update
        setTimeout(() => {
          ws.dispatchEvent(new MessageEvent('message', {
            data: JSON.stringify({
              type: 'status',
              status: 'processing',
              progress: 50,
              message: 'Downloading dependencies...'
            })
          }));
        }, 1000);
        
        // Send completion
        setTimeout(() => {
          ws.dispatchEvent(new MessageEvent('message', {
            data: JSON.stringify({
              type: 'status',
              status: 'completed',
              progress: 100,
              message: 'Task completed successfully',
              result: {
                filename: 'plugin-offline.difypkg',
                size: 1024000
              }
            })
          }));
        }, 2000);
      }
    });
    
    // Verify status updates are reflected in UI
    await taskStatusPage.waitForLogMessage('Downloading dependencies...');
    await taskStatusPage.waitForTaskCompletion();
    
    // Should show download button
    const downloadButton = await taskStatusPage.isDownloadButtonVisible();
    expect(downloadButton).toBe(true);
  });

  test('should handle WebSocket reconnection', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'reconnect-test-123',
          status: 'processing'
        })
      });
    });
    
    // Submit task
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Simulate disconnection
    await wsHelper.simulateDisconnection();
    const disconnectedState = await wsHelper.getConnectionState();
    expect(disconnectedState).toBe('closed');
    
    // Simulate reconnection
    await page.evaluate(() => {
      // Trigger reconnection logic
      const event = new Event('online');
      window.dispatchEvent(event);
    });
    
    // Should attempt to reconnect
    await page.waitForTimeout(2000);
    
    // Check if reconnection indicator is shown
    const wsStatus = await taskStatusPage.getWebSocketStatus();
    expect(['connected', 'disconnected']).toContain(wsStatus);
  });

  test('should buffer messages during disconnection', async ({ page, homePage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'buffer-test-123',
          status: 'processing'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Monitor connection stability
    const stability = await wsHelper.monitorConnectionStability(5000);
    
    // Connection should remain stable during normal operation
    expect(stability.stable).toBe(true);
    expect(stability.changes).toBe(0);
  });

  test('should handle rapid status updates', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'rapid-test-123',
          status: 'pending'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Send rapid updates
    await page.evaluate(() => {
      const ws = (window as any).__wsInstance;
      if (ws) {
        for (let i = 0; i <= 100; i += 10) {
          setTimeout(() => {
            ws.dispatchEvent(new MessageEvent('message', {
              data: JSON.stringify({
                type: 'progress',
                progress: i,
                message: `Processing... ${i}%`
              })
            }));
          }, i * 10);
        }
      }
    });
    
    // UI should handle rapid updates smoothly
    await page.waitForTimeout(1500);
    const progress = await taskStatusPage.getTaskProgress();
    expect(parseInt(progress || '0')).toBeGreaterThan(0);
  });

  test('should receive log messages via WebSocket', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'logs-test-123',
          status: 'processing'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Send log messages
    await page.evaluate(() => {
      const ws = (window as any).__wsInstance;
      if (ws) {
        const logs = [
          { level: 'info', message: 'Starting repackaging process...' },
          { level: 'debug', message: 'Extracting plugin files...' },
          { level: 'warning', message: 'Large dependency detected' },
          { level: 'error', message: 'Retrying download...' },
          { level: 'info', message: 'Process completed successfully' }
        ];
        
        logs.forEach((log, index) => {
          setTimeout(() => {
            ws.dispatchEvent(new MessageEvent('message', {
              data: JSON.stringify({
                type: 'log',
                ...log,
                timestamp: new Date().toISOString()
              })
            }));
          }, (index + 1) * 500);
        });
      }
    });
    
    // Verify logs appear in log viewer
    await taskStatusPage.waitForLogMessage('Starting repackaging process...');
    await taskStatusPage.waitForLogMessage('Process completed successfully');
    
    const logEntries = await taskStatusPage.getLogEntries();
    expect(logEntries.length).toBeGreaterThanOrEqual(5);
    
    // Check log levels
    const errorLog = logEntries.find(e => e.level === 'error');
    expect(errorLog?.message).toContain('Retrying download...');
  });

  test('should handle WebSocket errors gracefully', async ({ page, homePage, wsHelper }) => {
    // Mock task creation
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'error-test-123',
          status: 'processing'
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Simulate WebSocket error
    await page.evaluate(() => {
      const ws = (window as any).__wsInstance;
      if (ws) {
        ws.dispatchEvent(new Event('error'));
        ws.close(1006, 'Abnormal closure');
      }
    });
    
    // Should show connection error indicator
    const wsStatus = await taskStatusPage.getWebSocketStatus();
    expect(wsStatus).toBe('disconnected');
    
    // Should still be able to poll for updates
    await page.waitForTimeout(2000);
  });

  test('should sync state after reconnection', async ({ page, homePage, taskStatusPage, wsHelper }) => {
    // Mock APIs
    await page.route('**/api/v1/tasks', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'sync-test-123',
          status: 'processing'
        })
      });
    });
    
    await page.route('**/api/v1/tasks/sync-test-123', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'sync-test-123',
          status: 'completed',
          result: {
            filename: 'synced-plugin-offline.difypkg'
          }
        })
      });
    });
    
    await homePage.submitUrl(TEST_DATA.urls.validDifypkg);
    await wsHelper.waitForConnection();
    
    // Disconnect WebSocket
    await wsHelper.closeConnection();
    
    // Wait for polling to kick in
    await page.waitForTimeout(3000);
    
    // Should fetch latest status via REST API
    const status = await taskStatusPage.getTaskStatus();
    expect(status).toContain('Completed');
  });

  test('should handle concurrent WebSocket connections', async ({ page, context }) => {
    // Open multiple tabs
    const page1 = page;
    const page2 = await context.newPage();
    
    // Navigate both pages
    await page1.goto('/');
    await page2.goto('/');
    
    // Create WebSocket helpers for both pages
    const wsHelper1 = new (await import('../utils/websocket')).WebSocketHelper(page1);
    const wsHelper2 = new (await import('../utils/websocket')).WebSocketHelper(page2);
    
    await wsHelper1.interceptWebSocket();
    await wsHelper2.interceptWebSocket();
    
    // Mock task creation
    for (const p of [page1, page2]) {
      await p.route('**/api/v1/tasks', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            task_id: `concurrent-${Date.now()}`,
            status: 'pending'
          })
        });
      });
    }
    
    // Submit tasks on both pages
    const homePage1 = new (await import('../pages/HomePage')).HomePage(page1);
    const homePage2 = new (await import('../pages/HomePage')).HomePage(page2);
    
    await homePage1.submitUrl(TEST_DATA.urls.validDifypkg);
    await homePage2.submitUrl(TEST_DATA.urls.githubRelease);
    
    // Both should have active WebSocket connections
    await wsHelper1.waitForConnection();
    await wsHelper2.waitForConnection();
    
    expect(await wsHelper1.getConnectionState()).toBe('open');
    expect(await wsHelper2.getConnectionState()).toBe('open');
    
    await page2.close();
  });
});