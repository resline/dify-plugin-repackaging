import { act, render, screen, waitFor } from '../../test/utils/test-utils';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';

const websocketHarness = vi.hoisted(() => ({
  sockets: [] as Array<{
    options: Record<string, (...args: any[]) => void>;
    close: ReturnType<typeof vi.fn>;
    reconnect: ReturnType<typeof vi.fn>;
  }>,
}));

vi.mock('../../services/websocket', () => ({
  createReconnectingWebSocket: vi.fn((_taskId: string, options: Record<string, (...args: any[]) => void>) => {
    const socket = {
      options,
      close: vi.fn(),
      reconnect: vi.fn(),
    };
    websocketHarness.sockets.push(socket);
    return socket;
  }),
  ReconnectingWebSocket: class ReconnectingWebSocket {},
}));

import TaskStatus from '../TaskStatus';

describe('TaskStatus connection lifecycle', () => {
  it('keeps one WebSocket and one initial status request across state-driven renders', async () => {
    let statusRequests = 0;

    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        statusRequests += 1;
        return HttpResponse.json({
          task_id: 'test-task-123',
          status: 'processing',
          progress: 5,
          created_at: new Date().toISOString(),
        });
      })
    );

    render(
      <TaskStatus
        taskId="test-task-123"
        onComplete={vi.fn()}
        onError={vi.fn()}
        onNewTask={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/repackaging plugin/i)).toBeInTheDocument();
      expect(websocketHarness.sockets).toHaveLength(1);
      expect(statusRequests).toBe(1);
    });

    act(() => {
      websocketHarness.sockets[0].options.onOpen();
      websocketHarness.sockets[0].options.onMessage({
        task_id: 'test-task-123',
        status: 'processing',
        progress: 25,
        message: 'Resolving dependencies...',
        type: 'status',
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/resolving dependencies/i)).toBeInTheDocument();
    });

    expect(websocketHarness.sockets).toHaveLength(1);
    expect(statusRequests).toBe(1);
  });
});
