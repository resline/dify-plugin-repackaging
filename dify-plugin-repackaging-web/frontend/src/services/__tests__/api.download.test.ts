import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';
import { taskService } from '../api';

describe('authenticated task download', () => {
  const taskId = 'test-task-123';
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

  beforeEach(() => {
    localStorage.setItem('auth_token', 'test-secret');
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:test-download'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    localStorage.clear();
    click.mockClear();
  });

  it('sends the auth token and saves the response as a .difypkg file', async () => {
    let receivedToken: string | null = null;

    server.use(
      http.get(`/api/v1/tasks/${taskId}/download`, ({ request }) => {
        receivedToken = request.headers.get('x-auth-token');
        return new HttpResponse(new Blob(['plugin bytes']), {
          headers: {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'attachment; filename="example-offline.difypkg"',
          },
        });
      })
    );

    const filename = await taskService.downloadTaskFile(taskId, 'fallback.difypkg');

    expect(receivedToken).toBe('test-secret');
    expect(filename).toBe('example-offline.difypkg');
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
  });
});
