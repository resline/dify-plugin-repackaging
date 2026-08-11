import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

class ControlledWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: ControlledWebSocket[] = [];

  readyState = ControlledWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;

  constructor(public url: string) {
    ControlledWebSocket.instances.push(this);
  }

  send = vi.fn();

  close = vi.fn(() => {
    this.readyState = ControlledWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1000 }));
  });

  fail(code = 1006) {
    this.readyState = ControlledWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code }));
  }
}

describe('ReconnectingWebSocket retry lifecycle', () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    ControlledWebSocket.instances = [];
    Object.defineProperty(global, 'WebSocket', {
      configurable: true,
      writable: true,
      value: ControlledWebSocket,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(global, 'WebSocket', {
      configurable: true,
      writable: true,
      value: originalWebSocket,
    });
  });

  it('schedules another retry when a reconnect attempt also fails', async () => {
    const { ReconnectingWebSocket } = await import('../websocket');
    const socket = new ReconnectingWebSocket({
      taskId: 'task-123',
      reconnectInterval: 100,
      maxReconnectAttempts: 3,
    });

    ControlledWebSocket.instances[0].fail();
    await vi.advanceTimersByTimeAsync(100);
    expect(ControlledWebSocket.instances).toHaveLength(2);

    ControlledWebSocket.instances[1].fail();
    await vi.advanceTimersByTimeAsync(150);
    expect(ControlledWebSocket.instances).toHaveLength(3);

    socket.close();
  });

  it('manual reconnect creates only one replacement socket', async () => {
    const { ReconnectingWebSocket } = await import('../websocket');
    const socket = new ReconnectingWebSocket({ taskId: 'task-123' });

    socket.reconnect();
    await vi.runOnlyPendingTimersAsync();

    expect(ControlledWebSocket.instances).toHaveLength(2);
    socket.close();
  });
});
