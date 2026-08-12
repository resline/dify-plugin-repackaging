import { expect, Page, test } from '@playwright/test';

const completedTask = {
  task_id: 'completed-task',
  status: 'completed',
  progress: 100,
  message: 'Repackaging completed!',
  created_at: '2026-08-12T10:00:00Z',
  completed_at: '2026-08-12T10:01:00Z',
  output_filename: 'json2chart-offline.difypkg',
  download_url: '/api/v1/tasks/completed-task/download',
  plugin_metadata: {
    name: 'json2chart',
    author: 'lfenghx',
    version: '1.2.0',
  },
};

async function mockAuthenticatedApi(page: Page, completedTasks: typeof completedTask[] = []) {
  await page.route('**/api/v1/auth/session', async route => {
    await route.fulfill({ json: { authenticated: true } });
  });
  await page.route('**/api/v1/tasks/completed?**', async route => {
    await route.fulfill({ json: { tasks: completedTasks, total: completedTasks.length } });
  });
  await page.route('**/api/v1/tasks?**', async route => {
    await route.fulfill({ json: { tasks: [], total: 0 } });
  });
}

test.describe('Reported regressions', () => {
  test('signs in without a React hook-order crash', async ({ page }) => {
    const consoleErrors: string[] = [];
    let authenticated = false;

    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    await page.route('**/api/v1/auth/session', async route => {
      await route.fulfill({ json: { authenticated } });
    });
    await page.route('**/api/v1/auth/login', async route => {
      authenticated = true;
      await route.fulfill({ json: { authenticated: true } });
    });
    await page.route('**/api/v1/tasks/completed?**', async route => {
      await route.fulfill({ json: { tasks: [], total: 0 } });
    });

    await page.goto('/');
    await page.getByLabel('Password').fill('test-password');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByRole('heading', { name: 'Repackage a Dify Plugin' })).toBeVisible();
    expect(consoleErrors.filter(error => /React error|Rendered more hooks/i.test(error))).toEqual([]);
  });

  test('keeps the first completed file above the application header', async ({ page }) => {
    await mockAuthenticatedApi(page, [completedTask]);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    const sidebar = page.getByTestId('completed-files-sidebar');
    const firstFile = sidebar.getByText('json2chart', { exact: true });
    await expect(firstFile).toBeVisible();

    const isTopmostAtCenter = await firstFile.evaluate(element => {
      const bounds = element.getBoundingClientRect();
      const topmost = document.elementFromPoint(
        bounds.left + bounds.width / 2,
        bounds.top + bounds.height / 2,
      );
      return topmost === element || element.contains(topmost);
    });
    expect(isTopmostAtCenter).toBe(true);

    const [sidebarZIndex, headerZIndex] = await Promise.all([
      sidebar.evaluate(element => Number.parseInt(getComputedStyle(element).zIndex, 10)),
      page.locator('header').evaluate(element => Number.parseInt(getComputedStyle(element).zIndex, 10)),
    ]);
    expect(sidebarZIndex).toBeGreaterThan(headerZIndex);
  });

  test('preserves completed status after minimizing the processing panel', async ({ page }) => {
    await mockAuthenticatedApi(page);
    await page.route('**/api/v1/tasks', async route => {
      await route.fulfill({ json: { task_id: completedTask.task_id } });
    });
    await page.route(`**/api/v1/tasks/${completedTask.task_id}`, async route => {
      await route.fulfill({ json: completedTask });
    });
    await page.routeWebSocket('**/ws/tasks/**', () => {});

    await page.goto('/');
    await page.getByLabel('Plugin URL').fill('https://example.com/json2chart.difypkg');
    await page.getByRole('button', { name: 'Start Repackaging' }).click();

    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('heading', { name: 'Repackaging completed!' })).toBeVisible();
    await dialog.getByRole('button', { name: 'Minimize task result' }).click();

    await expect(dialog.getByRole('heading', { name: 'Completed Task' })).toBeVisible();
    await expect(dialog.getByText('Task completed successfully', { exact: true })).toBeVisible();
  });
});
