import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createReconnectingWebSocket,
  ReconnectingWebSocket,
  WebSocketState,
} from '../websocket'
import {
  MockWebSocket,
  WebSocketConstructorMock,
} from '../../test/mocks/websocket'

describe('WebSocket service', () => {
  let socket: ReconnectingWebSocket | undefined
  const callbacks = {
    onOpen: vi.fn(),
    onMessage: vi.fn(),
    onError: vi.fn(),
    onClose: vi.fn(),
  }

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    socket?.close()
    vi.useRealTimers()
  })

  const connect = (options: ConstructorParameters<typeof ReconnectingWebSocket>[0] = { taskId: 'test-123' }) => {
    socket = new ReconnectingWebSocket({ ...callbacks, ...options })
    return MockWebSocket.instances[MockWebSocket.instances.length - 1]
  }

  it('connects to the task URL and exposes connection state', () => {
    const transport = connect({ taskId: 'test-123' })

    expect(WebSocketConstructorMock).toHaveBeenCalledWith(
      expect.stringMatching(/^ws:\/\/.*\/ws\/tasks\/test-123$/)
    )
    expect(socket!.getReadyState()).toBe(WebSocket.CONNECTING)
    expect(socket!.isConnected()).toBe(false)

    transport.serverOpen()
    expect(callbacks.onOpen).toHaveBeenCalledOnce()
    expect(socket!.getReadyState()).toBe(WebSocket.OPEN)
    expect(socket!.isConnected()).toBe(true)
  })

  it('parses application messages and forwards socket errors', () => {
    const transport = connect()
    transport.serverOpen()
    transport.serverMessage({ type: 'log', message: 'Test message' })
    transport.serverError()

    expect(callbacks.onMessage).toHaveBeenCalledWith({ type: 'log', message: 'Test message' })
    expect(callbacks.onError).toHaveBeenCalledWith(expect.any(Event))
  })

  it('answers server ping without forwarding it', () => {
    const transport = connect()
    transport.serverOpen()

    transport.serverMessage({ type: 'ping' })

    expect(transport.send).toHaveBeenCalledWith(expect.stringContaining('"type":"pong"'))
    expect(callbacks.onMessage).not.toHaveBeenCalled()
  })

  it('sends heartbeat pings periodically', async () => {
    const transport = connect({ taskId: 'test-123', heartbeatInterval: 1_000 })
    transport.serverOpen()

    await vi.advanceTimersByTimeAsync(1_000)

    expect(transport.send).toHaveBeenCalledWith(expect.stringContaining('"type":"ping"'))
  })

  it('reconnects after an unexpected close using exponential backoff', async () => {
    const first = connect({
      taskId: 'test-123',
      reconnectInterval: 1_000,
      maxReconnectAttempts: 3,
    })

    first.serverClose(1006)
    expect(callbacks.onClose).toHaveBeenCalledOnce()
    await vi.advanceTimersByTimeAsync(999)
    expect(MockWebSocket.instances).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(MockWebSocket.instances).toHaveLength(2)

    MockWebSocket.instances[1].serverClose(1006)
    await vi.advanceTimersByTimeAsync(1_499)
    expect(MockWebSocket.instances).toHaveLength(2)
    await vi.advanceTimersByTimeAsync(1)
    expect(MockWebSocket.instances).toHaveLength(3)
  })

  it('stops after the configured number of consecutive reconnect attempts', async () => {
    connect({ taskId: 'test-123', reconnectInterval: 100, maxReconnectAttempts: 2 })

    MockWebSocket.instances[0].serverClose(1006)
    await vi.advanceTimersByTimeAsync(100)
    MockWebSocket.instances[1].serverClose(1006)
    await vi.advanceTimersByTimeAsync(150)
    MockWebSocket.instances[2].serverClose(1006)
    await vi.runOnlyPendingTimersAsync()

    expect(MockWebSocket.instances).toHaveLength(3)
  })

  it('does not reconnect after a manual close or a missing-task response', async () => {
    connect({ taskId: 'test-123', reconnectInterval: 100 })
    socket!.close()
    await vi.runOnlyPendingTimersAsync()
    expect(MockWebSocket.instances).toHaveLength(1)

    socket = undefined
    const missingTask = connect({ taskId: 'missing', reconnectInterval: 100 })
    missingTask.serverClose(1008, 'Task not found')
    await vi.runOnlyPendingTimersAsync()
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('ends reconnects and requests login when the WebSocket session expires', async () => {
    const unauthorized = vi.fn()
    window.addEventListener('auth:unauthorized', unauthorized)
    const transport = connect({ taskId: 'expired', reconnectInterval: 100 })

    transport.serverClose(1008, 'Authentication required')
    await vi.runOnlyPendingTimersAsync()

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(unauthorized).toHaveBeenCalledOnce()
    expect((unauthorized.mock.calls[0][0] as CustomEvent).detail).toMatch(/session expired/i)
    window.removeEventListener('auth:unauthorized', unauthorized)
  })

  it('manual reconnect creates exactly one replacement transport', () => {
    connect()
    socket!.reconnect()
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('reconnects when heartbeat acknowledgements stop', async () => {
    const transport = connect({ taskId: 'test-123', heartbeatInterval: 1_000 })
    transport.serverOpen()

    await vi.advanceTimersByTimeAsync(2_000)

    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('sends serialized data only while connected', () => {
    const transport = connect()
    socket!.send({ type: 'ignored' })
    expect(transport.send).not.toHaveBeenCalled()

    transport.serverOpen()
    socket!.send({ type: 'custom', value: 1 })
    expect(transport.send).toHaveBeenCalledWith('{"type":"custom","value":1}')
  })

  it('factory creates a reconnecting socket with merged options', () => {
    socket = createReconnectingWebSocket('factory-task', {
      onOpen: callbacks.onOpen,
      heartbeatInterval: 5_000,
    })
    MockWebSocket.instances[0].serverOpen()

    expect(socket).toBeInstanceOf(ReconnectingWebSocket)
    expect(callbacks.onOpen).toHaveBeenCalledOnce()
  })

  it('exports browser-compatible state constants', () => {
    expect(WebSocketState).toEqual({ CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 })
  })
})
