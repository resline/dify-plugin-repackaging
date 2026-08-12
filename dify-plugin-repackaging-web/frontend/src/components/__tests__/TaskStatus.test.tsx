import { act } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { render, screen, waitFor } from '../../test/utils/test-utils'
import { server } from '../../test/mocks/server'
import { MockWebSocket } from '../../test/mocks/websocket'
import TaskStatus from '../TaskStatus'
import type { Task } from '../../types/app'

describe('TaskStatus', () => {
  const taskId = 'test-task-123'
  const onComplete = vi.fn()
  const onError = vi.fn()
  const onNewTask = vi.fn()
  const onStatusChange = vi.fn()

  const props = { taskId, onComplete, onError, onNewTask, onStatusChange }

  const task = (overrides: Partial<Task> = {}): Task => ({
    task_id: taskId,
    status: 'pending',
    progress: 0,
    created_at: '2024-01-01T10:00:00Z',
    ...overrides,
  })

  const respondWith = (response: Task) => {
    server.use(
      http.get(`/api/v1/tasks/${taskId}`, () => HttpResponse.json(response))
    )
  }

  const renderTask = async (initialTask = task()) => {
    respondWith(initialTask)
    const view = render(<TaskStatus {...props} />)
    await waitFor(() => expect(onStatusChange).toHaveBeenCalledWith(initialTask))
    return view
  }

  const openSocket = () => {
    const transport = MockWebSocket.instances[0]
    act(() => transport.serverOpen())
    return transport
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads the initial task and records its initial state', async () => {
    respondWith(task())
    render(<TaskStatus {...props} />)
    expect(screen.getByRole('status', { name: /loading task status/i })).toBeInTheDocument()

    expect(await screen.findByText(/waiting to start/i)).toBeInTheDocument()
    expect(screen.getByText(/task test-task-123 started/i)).toBeInTheDocument()
    expect(screen.getByText(/task id: test-task-123/i)).toBeInTheDocument()
  })

  it('applies complete WebSocket snapshots and progress updates', async () => {
    await renderTask(task({ status: 'processing' }))
    const transport = openSocket()
    const update = task({
      status: 'processing',
      progress: 50,
      message: 'Installing dependencies...',
    })

    act(() => transport.serverMessage({ type: 'status', ...update }))

    expect(await screen.findByText('Installing dependencies...')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: /task progress/i })).toHaveAttribute('aria-valuenow', '50')
    expect(onStatusChange).toHaveBeenLastCalledWith(expect.objectContaining(update))
  })

  it('reports a failed task and preserves the failure message', async () => {
    await renderTask(task({ status: 'processing' }))
    const transport = openSocket()

    act(() => transport.serverMessage({
      type: 'status',
      ...task({
        status: 'failed',
        message: 'Failed to download package',
        error: 'Network error',
      }),
    }))

    expect(await screen.findByText(/repackaging failed/i)).toBeInTheDocument()
    expect(screen.getByText('Failed to download package')).toBeInTheDocument()
    expect(onError).toHaveBeenCalledWith('Network error')
  })

  it('reports completion once and exposes download actions', async () => {
    await renderTask(task({ status: 'processing' }))
    const transport = openSocket()
    const completed = task({
      status: 'completed',
      progress: 100,
      message: 'Repackaging completed!',
      output_filename: 'plugin-offline.difypkg',
      download_url: `/api/v1/tasks/${taskId}/download`,
      completed_at: '2024-01-01T10:05:00Z',
    })

    act(() => transport.serverMessage({ type: 'status', ...completed }))
    act(() => transport.serverMessage({ type: 'status', ...completed }))

    await waitFor(() => expect(onComplete).toHaveBeenCalledOnce())
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining(completed))
    expect(screen.getByRole('button', { name: 'Download Plugin' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download plugin-offline\.difypkg/i })).toBeInTheDocument()
    expect(screen.getByText(/completed:/i)).toBeInTheDocument()
  })

  it('offers a REST refresh when an active connection drops', async () => {
    await renderTask(task({ status: 'processing' }))
    const transport = openSocket()

    act(() => transport.serverClose(1006, 'Connection lost'))

    expect(await screen.findByRole('button', { name: /refresh/i })).toBeInTheDocument()
    expect(screen.getByText(/connection lost/i)).toBeInTheDocument()
  })

  it('closes its socket during unmount', async () => {
    const view = await renderTask(task({ status: 'processing' }))
    const transport = MockWebSocket.instances[0]

    view.unmount()

    expect(transport.close).toHaveBeenCalledOnce()
  })

  it('renders plugin metadata and invokes the new-task action', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    await renderTask(task({
      status: 'completed',
      progress: 100,
      plugin_metadata: {
        name: 'agent',
        author: 'langgenius',
        version: '0.0.9',
        description: 'Agent plugin',
      },
    }))

    expect(screen.getByText('Plugin Information')).toBeInTheDocument()
    expect(screen.getByText('langgenius')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /new task/i }))
    expect(onNewTask).toHaveBeenCalledOnce()
  })

  it('renders an accessible progress status and log viewer', async () => {
    await renderTask(task({
      status: 'processing',
      progress: 25,
      message: 'Downloading package',
    }))

    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuemin', '0')
    expect(screen.getByText('Downloading package')).toBeInTheDocument()
  })
})
