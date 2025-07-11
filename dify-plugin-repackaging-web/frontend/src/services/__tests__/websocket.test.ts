import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ReconnectingWebSocket, createReconnectingWebSocket, WebSocketState } from '../websocket'
import { waitFor } from '@testing-library/react'

describe('WebSocket Service', () => {
  let ws: ReconnectingWebSocket
  const mockCallbacks = {
    onOpen: vi.fn(),
    onMessage: vi.fn(),
    onError: vi.fn(),
    onClose: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    if (ws) {
      ws.close()
    }
    vi.useRealTimers()
  })

  describe('ReconnectingWebSocket', () => {
    it('connects to the correct URL', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('/ws/tasks/test-123')
      )
    })

    it('calls onOpen when connected', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      expect(mockCallbacks.onOpen).toHaveBeenCalled()
    })

    it('calls onMessage when receiving messages', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value
      const testMessage = { type: 'log', message: 'Test message' }

      mockWs.onmessage(new MessageEvent('message', {
        data: JSON.stringify(testMessage)
      }))

      expect(mockCallbacks.onMessage).toHaveBeenCalledWith(testMessage)
    })

    it('handles ping/pong messages internally', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value
      const sendSpy = vi.spyOn(mockWs, 'send')

      // Receive ping from server
      mockWs.onmessage(new MessageEvent('message', {
        data: JSON.stringify({ type: 'ping' })
      }))

      // Should send pong response
      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"type":"pong"')
      )

      // Should not call user's onMessage for ping
      expect(mockCallbacks.onMessage).not.toHaveBeenCalled()
    })

    it('sends heartbeat messages periodically', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        heartbeatInterval: 1000,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value
      const sendSpy = vi.spyOn(mockWs, 'send')

      // Advance time to trigger heartbeat
      await vi.advanceTimersByTimeAsync(1100)

      expect(sendSpy).toHaveBeenCalledWith(
        expect.stringContaining('"type":"ping"')
      )
    })

    it('attempts to reconnect on disconnection', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        autoReconnect: true,
        reconnectInterval: 1000,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value

      // Simulate disconnection
      mockWs.onclose(new CloseEvent('close', { code: 1006 }))

      expect(mockCallbacks.onClose).toHaveBeenCalled()

      // Clear previous WebSocket calls
      vi.clearAllMocks()

      // Advance time to trigger reconnect
      await vi.advanceTimersByTimeAsync(1100)

      // Should create new WebSocket connection
      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('/ws/tasks/test-123')
      )
    })

    it('does not reconnect when manually closed', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        autoReconnect: true,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      // Manually close
      ws.close()

      vi.clearAllMocks()

      // Advance time
      await vi.advanceTimersByTimeAsync(5000)

      // Should not create new connection
      expect(global.WebSocket).not.toHaveBeenCalled()
    })

    it('respects maximum reconnect attempts', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        autoReconnect: true,
        reconnectInterval: 100,
        maxReconnectAttempts: 3,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value

      // Simulate multiple disconnections
      for (let i = 0; i < 4; i++) {
        mockWs.onclose(new CloseEvent('close', { code: 1006 }))
        await vi.advanceTimersByTimeAsync(200)
      }

      // Should only attempt 3 reconnections
      expect(global.WebSocket).toHaveBeenCalledTimes(4) // 1 initial + 3 reconnects
    })

    it('does not reconnect for "Task not found" error', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        autoReconnect: true,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value

      // Simulate "Task not found" close event
      mockWs.onclose(new CloseEvent('close', { code: 1008, reason: 'Task not found' }))

      vi.clearAllMocks()

      // Advance time
      await vi.advanceTimersByTimeAsync(5000)

      // Should not attempt reconnection
      expect(global.WebSocket).not.toHaveBeenCalled()
    })

    it('exponentially backs off reconnect attempts', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        autoReconnect: true,
        reconnectInterval: 1000,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value

      // First disconnection
      mockWs.onclose(new CloseEvent('close', { code: 1006 }))
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('1000ms')
      )

      await vi.advanceTimersByTimeAsync(1100)

      // Second disconnection
      const mockWs2 = (global.WebSocket as any).mock.results[1].value
      mockWs2.onclose(new CloseEvent('close', { code: 1006 }))
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('1500ms')
      )

      consoleSpy.mockRestore()
    })

    it('sends messages when connected', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value
      const sendSpy = vi.spyOn(mockWs, 'send')

      const testData = { type: 'custom', data: 'test' }
      ws.send(testData)

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify(testData))
    })

    it('does not send messages when disconnected', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      const mockWs = (global.WebSocket as any).mock.results[0].value
      mockWs.readyState = WebSocket.CLOSED

      ws.send({ type: 'test' })

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'WebSocket is not open, cannot send message'
      )

      consoleWarnSpy.mockRestore()
    })

    it('reports connection state correctly', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        ...mockCallbacks
      })

      expect(ws.isConnected()).toBe(false)
      expect(ws.getReadyState()).toBe(WebSocket.CONNECTING)

      await vi.runOnlyPendingTimersAsync()

      expect(ws.isConnected()).toBe(true)
      expect(ws.getReadyState()).toBe(WebSocket.OPEN)

      ws.close()

      expect(ws.isConnected()).toBe(false)
      expect(ws.getReadyState()).toBe(WebSocket.CLOSED)
    })

    it('reconnects when no pong received', async () => {
      ws = new ReconnectingWebSocket({
        taskId: 'test-123',
        heartbeatInterval: 1000,
        ...mockCallbacks
      })

      await vi.runOnlyPendingTimersAsync()

      // Advance time past heartbeat interval * 2 without pong
      await vi.advanceTimersByTimeAsync(2100)

      // Should trigger reconnection
      expect(global.WebSocket).toHaveBeenCalledTimes(2)
    })
  })

  describe('createReconnectingWebSocket', () => {
    it('creates WebSocket with merged options', async () => {
      ws = createReconnectingWebSocket('test-123', {
        onOpen: mockCallbacks.onOpen,
        heartbeatInterval: 5000
      })

      await vi.runOnlyPendingTimersAsync()

      expect(mockCallbacks.onOpen).toHaveBeenCalled()
      expect(ws).toBeInstanceOf(ReconnectingWebSocket)
    })
  })

  describe('WebSocketState', () => {
    it('exports correct WebSocket state constants', () => {
      expect(WebSocketState.CONNECTING).toBe(0)
      expect(WebSocketState.OPEN).toBe(1)
      expect(WebSocketState.CLOSING).toBe(2)
      expect(WebSocketState.CLOSED).toBe(3)
    })
  })
})