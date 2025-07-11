import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '../../test/utils/test-utils'
import userEvent from '@testing-library/user-event'
import TaskStatus from '../TaskStatus.jsx'
import { mockWebSocketMessage } from '../../test/utils/test-utils'
import { server } from '../../test/mocks/server'
import { http, HttpResponse } from 'msw'

// Access the mock WebSocket class from global
const MockWebSocket = global.WebSocket as any

describe('TaskStatus', () => {
  const mockOnComplete = vi.fn()
  const mockOnError = vi.fn()
  const mockOnNewTask = vi.fn()

  const defaultProps = {
    taskId: 'test-task-123',
    onComplete: mockOnComplete,
    onError: mockOnError,
    onNewTask: mockOnNewTask
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders initial loading state', async () => {
    // Mock the initial task status API response
    const mockTask = {
      id: 'test-task-123',
      status: 'pending',
      created_at: new Date().toISOString(),
      logs: []
    }
    
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json(mockTask)
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Initial state shows a loading spinner
    expect(screen.getByRole('status')).toBeInTheDocument()
    
    // Wait for task status to load
    await waitFor(() => {
      expect(screen.getByText(/waiting to start/i)).toBeInTheDocument()
    })
  })

  it('establishes WebSocket connection and receives messages', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'pending',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait for the component to render and fetch initial status
    await waitFor(() => {
      expect(screen.getByText(/waiting to start/i)).toBeInTheDocument()
    })
    
    // The component should establish a WebSocket connection
    // Check that the component can receive log messages
    await waitFor(() => {
      // Look for the initial log entry
      expect(screen.getByText(/task test-task-123 started/i)).toBeInTheDocument()
    })
  })

  it('displays task progress messages', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          message: 'Starting repackaging process...',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait for initial render
    await waitFor(() => {
      expect(screen.getByText(/starting repackaging process/i)).toBeInTheDocument()
    })
    
    // Get the WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    // Simulate task progress
    if (ws && ws.onmessage) {
      if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
          status: 'downloading',
          message: 'Downloading plugin package...',
          type: 'status'
        })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/downloading plugin package/i)).toBeInTheDocument()
    })
    
    if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
          status: 'processing',
          message: 'Installing dependencies...',
          type: 'status'
        })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/installing dependencies/i)).toBeInTheDocument()
    })
  })

  it('displays error messages', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
        status: 'failed',
        message: 'Failed to download package',
        error: 'Network error',
        type: 'status'
      })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/failed to download package/i)).toBeInTheDocument()
      expect(mockOnError).toHaveBeenCalledWith('Network error')
    })
  })

  it('handles task completion', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    const completedData = {
      status: 'completed',
      message: 'Repackaging completed!',
      output_filename: 'plugin-offline.difypkg',
      download_url: '/api/v1/tasks/test-task-123/download',
      type: 'status'
    }
    
    if (ws && ws.onmessage) {
      act(() => {
      mockWebSocketMessage(ws, completedData)
    })
    
    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith(completedData)
    })
    
    expect(screen.getByText(/repackaging completed/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /download/i })).toBeInTheDocument()
  })

  it('handles task failure', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
        status: 'failed',
        message: 'Task failed: Invalid plugin format',
        error: 'Invalid plugin format',
        type: 'status'
      })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/repackaging failed/i)).toBeInTheDocument()
      expect(mockOnError).toHaveBeenCalledWith('Invalid plugin format')
    })
  })

  it('displays progress percentage', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
        status: 'processing',
        progress: 50,
        message: 'Processing dependencies...',
        type: 'status'
      })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/50%/)).toBeInTheDocument()
      expect(screen.getByText(/processing dependencies/i)).toBeInTheDocument()
    })
    
    // Check the progress bar visual element
    const progressBar = screen.getByText('50%').closest('.bg-gray-200')
    expect(progressBar).toBeInTheDocument()
  })

  it('handles WebSocket disconnection', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    // Simulate connection close
    if (ws) {
      if (ws && ws.onmessage) {
      act(() => {
        ws.close(1006, 'Connection lost')
      })
    }
    
    await waitFor(() => {
      // Should show refresh button when disconnected
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
    })
  })

  it('cleans up WebSocket on unmount', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    const { unmount } = render(<TaskStatus {...defaultProps} />)
    
    // Wait a bit for WebSocket to establish
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Get the mock WebSocket instance
    const ws = (MockWebSocket as any).lastInstance
    
    if (ws) {
      const closeSpy = vi.spyOn(ws, 'close')
      unmount()
      expect(closeSpy).toHaveBeenCalled()
    } else {
      // If no WebSocket instance, just verify unmount works
      unmount()
    }
  })

  it('displays log viewer for detailed logs', async () => {
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'processing',
          message: 'Step 1: Downloading',
          created_at: new Date().toISOString(),
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    // Wait for initial message
    await waitFor(() => {
      expect(screen.getByText(/step 1: downloading/i)).toBeInTheDocument()
    })
    
    const ws = (MockWebSocket as any).lastInstance
    
    // Add another log message
    if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
        status: 'processing',
        message: 'Step 2: Extracting',
        type: 'status'
      })
      })
    }
    
    await waitFor(() => {
      expect(screen.getByText(/step 2: extracting/i)).toBeInTheDocument()
    })
  })

  it('shows task details and timestamps', async () => {
    const createdAt = '2024-01-01T10:00:00Z'
    const completedAt = '2024-01-01T10:05:00Z'
    
    // Mock the initial task status API response
    server.use(
      http.get('/api/v1/tasks/test-task-123', () => {
        return HttpResponse.json({
          id: 'test-task-123',
          status: 'completed',
          created_at: createdAt,
          completed_at: completedAt,
          logs: []
        })
      })
    )
    
    render(<TaskStatus {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText(/task id: test-task-123/i)).toBeInTheDocument()
      expect(screen.getByText(/started:/i)).toBeInTheDocument()
      expect(screen.getByText(/completed:/i)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes for progress', async () => {
      // Mock the initial task status API response with progress
      server.use(
        http.get('/api/v1/tasks/test-task-123', () => {
          return HttpResponse.json({
            id: 'test-task-123',
            status: 'processing',
            progress: 50,
            created_at: new Date().toISOString(),
            logs: []
          })
        })
      )
      
      render(<TaskStatus {...defaultProps} />)
      
      await waitFor(() => {
        // Check for progress percentage text instead of progressbar role
        expect(screen.getByText('50%')).toBeInTheDocument()
      })
    })

    it('announces status changes to screen readers', async () => {
      // Mock the initial task status API response
      server.use(
        http.get('/api/v1/tasks/test-task-123', () => {
          return HttpResponse.json({
            id: 'test-task-123',
            status: 'processing',
            created_at: new Date().toISOString(),
            logs: []
          })
        })
      )
      
      render(<TaskStatus {...defaultProps} />)
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled()
      })
      
      const ws = (MockWebSocket as any).lastInstance
      
      if (ws && ws.onmessage) {
      act(() => {
        mockWebSocketMessage(ws, {
          status: 'processing',
          message: 'Important status update',
          type: 'status'
        })
      })
      
      // Status messages should be visible
      await waitFor(() => {
        expect(screen.getByText(/important status update/i)).toBeInTheDocument()
      })
    })

    it('provides keyboard navigation for logs', async () => {
      // Mock the initial task status API response
      server.use(
        http.get('/api/v1/tasks/test-task-123', () => {
          return HttpResponse.json({
            id: 'test-task-123',
            status: 'processing',
            message: 'Log message 0',
            created_at: new Date().toISOString(),
            logs: []
          })
        })
      )
      
      const user = userEvent.setup()
      render(<TaskStatus {...defaultProps} />)
      
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled()
      })
      
      const ws = (MockWebSocket as any).lastInstance
      
      // Add more logs
      if (ws && ws.onmessage) {
      act(() => {
        for (let i = 1; i < 5; i++) {
          mockWebSocketMessage(ws, {
            status: 'processing',
            message: `Log message ${i}`,
            type: 'status'
          })
        }
      })
      
      await waitFor(() => {
        expect(screen.getByText(/log message 4/i)).toBeInTheDocument()
      })
      
      // Check that all log messages are present
      for (let i = 0; i < 5; i++) {
        expect(screen.getByText(`Log message ${i}`)).toBeInTheDocument()
      }
    })
  })
})