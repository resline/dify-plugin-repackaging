import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll, vi, beforeEach } from 'vitest'
import { server } from './mocks/server'

// Mock console methods to suppress expected errors in tests
const originalConsoleError = console.error
const originalConsoleWarn = console.warn

console.error = (...args: any[]) => {
  const errorString = args.join(' ')
  const ignoredPatterns = [
    'Error creating task:',
    'Error loading completed tasks:',
    'Error fetching task status:',
    'Error creating marketplace task:',
    'Error creating file upload task:',
    'WebSocket connection error',
    'Failed to create WebSocket:',
    'Failed to fetch',
    'Network request failed',
    'Request failed with status',
    'AxiosError',
  ]
  
  if (!ignoredPatterns.some(pattern => errorString.includes(pattern))) {
    originalConsoleError(...args)
  }
}

console.warn = (...args: any[]) => {
  const warnString = args.join(' ')
  const ignoredPatterns = [
    'Slow request',
    'Using fallback',
    'Failed slow request',
    'Request failed, retrying',
  ]
  
  if (!ignoredPatterns.some(pattern => warnString.includes(pattern))) {
    originalConsoleWarn(...args)
  }
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve('')),
  },
})

// Mock WebSocket
class MockWebSocket {
  url: string
  readyState: number = 0 // CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  constructor(url: string) {
    this.url = url
    // Simulate async connection with proper cleanup handling
    const timeoutId = setTimeout(() => {
      if (this.readyState === MockWebSocket.CONNECTING) {
        this.readyState = MockWebSocket.OPEN
        if (this.onopen) {
          this.onopen(new Event('open'))
        }
      }
    }, 10)
    
    // Store timeout for cleanup
    (this as any)._connectionTimeout = timeoutId
  }

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
  }

  close(code?: number, reason?: string) {
    // Clear connection timeout if still pending
    if ((this as any)._connectionTimeout) {
      clearTimeout((this as any)._connectionTimeout)
    }
    
    if (this.readyState === MockWebSocket.CLOSED || this.readyState === MockWebSocket.CLOSING) {
      return
    }
    
    this.readyState = MockWebSocket.CLOSING
    // Simulate async close
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED
      if (this.onclose) {
        this.onclose(new CloseEvent('close', { code, reason }))
      }
    }, 0)
  }
}

// Create a proper vi.fn() mock that returns instances
const WebSocketMock = vi.fn().mockImplementation((url: string) => {
  const instance = new MockWebSocket(url)
  return instance
})

// Add static properties to the mock
Object.assign(WebSocketMock, {
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
})

// Store the original WebSocket if exists
const OriginalWebSocket = global.WebSocket

// Set the global WebSocket BEFORE MSW setup using defineProperty
Object.defineProperty(global, 'WebSocket', {
  writable: true,
  configurable: true,
  value: WebSocketMock
})

// Setup MSW after WebSocket mock
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' })
  // Ensure our WebSocket mock is preserved after MSW setup
  Object.defineProperty(global, 'WebSocket', {
    writable: true,
    configurable: true,
    value: WebSocketMock
  })
})

afterEach(() => {
  cleanup()
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})

// Also reset the mock before each test to ensure clean state
beforeEach(() => {
  WebSocketMock.mockClear()
})

// Add process.env.NODE_ENV for test detection
if (!process.env.NODE_ENV) {
  process.env.NODE_ENV = 'test'
}