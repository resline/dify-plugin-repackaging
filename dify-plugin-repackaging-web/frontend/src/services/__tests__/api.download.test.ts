import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AxiosAdapter } from 'axios';
import api, { taskService } from '../api';

describe('authenticated task download', () => {
  const taskId = 'test-task-123';
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  const originalAdapter = api.defaults.adapter;

  beforeEach(() => {
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
    api.defaults.adapter = originalAdapter;
    localStorage.clear();
    click.mockClear();
  });

  it('sends the auth token and saves the response as a .difypkg file', async () => {
    let sentWithCredentials = false;
    let sentLegacyToken = false;
    const adapter: AxiosAdapter = vi.fn(async (config) => {
      sentWithCredentials = config.withCredentials === true;
      sentLegacyToken = config.headers.has('X-Auth-Token');
      return {
        data: new Blob(['plugin bytes']),
        status: 200,
        statusText: 'OK',
        headers: {
          'content-type': 'application/octet-stream',
          'content-disposition': 'attachment; filename="example-offline.difypkg"',
        },
        config,
      };
    });
    api.defaults.adapter = adapter;

    const filename = await taskService.downloadTaskFile(taskId, 'fallback.difypkg');

    expect(sentWithCredentials).toBe(true);
    expect(sentLegacyToken).toBe(false);
    expect(adapter).toHaveBeenCalledOnce();
    expect(filename).toBe('example-offline.difypkg');
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
  });
});
