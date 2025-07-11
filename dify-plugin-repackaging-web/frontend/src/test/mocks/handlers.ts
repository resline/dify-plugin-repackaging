import { http, HttpResponse, delay, ws } from 'msw'

const API_BASE_URL = '/api/v1'

// Mock data
const mockTasks = new Map()
const mockPlugins = [
  {
    id: '1',
    author: 'langgenius',
    name: 'agent',
    version: '0.0.9',
    description: 'Agent plugin for Dify',
    downloads: 1000,
    latest_version: '0.0.9',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z'
  },
  {
    id: '2',
    author: 'antv',
    name: 'visualization',
    version: '0.1.7',
    description: 'Data visualization plugin',
    downloads: 500,
    latest_version: '0.1.7',
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-20T00:00:00Z'
  }
]

const mockFiles = [
  {
    id: '1',
    filename: 'agent-0.0.9-offline.difypkg',
    size: 1024000,
    created_at: '2024-01-01T00:00:00Z',
    download_url: '/api/v1/files/1/download'
  },
  {
    id: '2',
    filename: 'visualization-0.1.7-offline.difypkg',
    size: 2048000,
    created_at: '2024-01-02T00:00:00Z',
    download_url: '/api/v1/files/2/download'
  }
]

export const httpHandlers = [
  // Task endpoints
  http.post(`${API_BASE_URL}/tasks`, async ({ request }) => {
    const body = await request.json() as any
    const taskId = Math.random().toString(36).substring(7)
    const task = {
      id: taskId,
      status: 'pending',
      url: body.url,
      platform: body.platform,
      suffix: body.suffix,
      created_at: new Date().toISOString(),
      logs: []
    }
    mockTasks.set(taskId, task)
    
    // Simulate task progression (matching WebSocket timeline)
    setTimeout(() => {
      const task = mockTasks.get(taskId)
      if (task) {
        task.status = 'processing'
        task.progress = 0
        task.phase = 'starting'
        task.logs.push({
          level: 'info',
          message: 'Starting repackaging process...',
          timestamp: new Date().toISOString()
        })
      }
    }, 100)
    
    // Match WebSocket timeline for consistency
    setTimeout(() => {
      const task = mockTasks.get(taskId)
      if (task) {
        task.status = 'completed'
        task.progress = 100
        task.phase = 'completed'
        task.result = {
          filename: 'plugin-offline.difypkg',
          size: 1024000,
          download_url: `/api/v1/tasks/${taskId}/download`
        }
        task.logs.push({
          level: 'info',
          message: 'Repackaging completed successfully',
          timestamp: new Date().toISOString()
        })
      }
    }, 4000) // Total time matches WebSocket progress simulation
    
    return HttpResponse.json({ task_id: taskId })
  }),

  http.post(`${API_BASE_URL}/tasks/marketplace`, async ({ request }) => {
    const body = await request.json() as any
    const taskId = Math.random().toString(36).substring(7)
    const task = {
      id: taskId,
      status: 'pending',
      author: body.author,
      name: body.name,
      version: body.version,
      platform: body.platform,
      suffix: body.suffix,
      created_at: new Date().toISOString(),
      logs: []
    }
    mockTasks.set(taskId, task)
    
    return HttpResponse.json({ task_id: taskId })
  }),

  http.post(`${API_BASE_URL}/tasks/upload`, async ({ request }) => {
    try {
      const formData = await request.formData()
      const file = formData.get('file') as File
      const taskId = Math.random().toString(36).substring(7)
      
      const task = {
        id: taskId,
        status: 'pending',
        filename: file ? file.name : 'unknown.difypkg',
        platform: formData.get('platform') as string || '',
        suffix: formData.get('suffix') as string || 'offline',
        created_at: new Date().toISOString(),
        logs: []
      }
      mockTasks.set(taskId, task)
      
      return HttpResponse.json({ task_id: taskId })
    } catch (error) {
      // Handle cases where formData parsing fails
      const taskId = Math.random().toString(36).substring(7)
      const task = {
        id: taskId,
        status: 'pending',
        filename: 'test.difypkg',
        platform: '',
        suffix: 'offline',
        created_at: new Date().toISOString(),
        logs: []
      }
      mockTasks.set(taskId, task)
      
      return HttpResponse.json({ task_id: taskId })
    }
  }),

  http.get(`${API_BASE_URL}/tasks/:taskId`, ({ params }) => {
    const task = mockTasks.get(params.taskId as string)
    if (!task) {
      return HttpResponse.json({ error: 'Task not found' }, { status: 404 })
    }
    return HttpResponse.json(task)
  }),

  http.get(`${API_BASE_URL}/tasks`, ({ request }) => {
    const url = new URL(request.url)
    const limit = parseInt(url.searchParams.get('limit') || '10')
    const tasks = Array.from(mockTasks.values())
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, limit)
    
    return HttpResponse.json({ tasks, total: tasks.length })
  }),

  http.get(`${API_BASE_URL}/tasks/completed`, ({ request }) => {
    const url = new URL(request.url)
    const limit = parseInt(url.searchParams.get('limit') || '10')
    const completedTasks = Array.from(mockTasks.values())
      .filter(task => task.status === 'completed' && task.result?.download_url)
      .map(task => ({
        task_id: task.id,
        status: task.status,
        created_at: task.created_at,
        completed_at: task.completed_at || new Date().toISOString(),
        output_filename: task.result?.filename || 'plugin-offline.difypkg',
        download_url: task.result?.download_url || `/api/v1/tasks/${task.id}/download`,
        plugin_metadata: task.plugin_metadata || {
          name: task.name || 'test-plugin',
          author: task.author || 'test-author',
          version: task.version || '1.0.0'
        }
      }))
      .sort((a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime())
      .slice(0, limit)
    
    return HttpResponse.json({ tasks: completedTasks, total: completedTasks.length })
  }),

  // Marketplace endpoints
  http.get(`${API_BASE_URL}/marketplace/plugins`, async ({ request }) => {
    await delay(100)
    const url = new URL(request.url)
    const search = url.searchParams.get('q')?.toLowerCase() || ''
    const category = url.searchParams.get('category') || ''
    const author = url.searchParams.get('author') || ''
    
    let filtered = mockPlugins
    
    if (search) {
      filtered = filtered.filter(plugin => 
        plugin.name.toLowerCase().includes(search) ||
        plugin.author.toLowerCase().includes(search) ||
        plugin.description.toLowerCase().includes(search)
      )
    }
    
    if (category) {
      // Filter by category if needed
    }
    
    if (author) {
      filtered = filtered.filter(plugin => plugin.author === author)
    }
    
    return HttpResponse.json({
      plugins: filtered,
      total: filtered.length,
      page: 1,
      per_page: 12
    })
  }),
  
  http.get(`${API_BASE_URL}/marketplace/categories`, async () => {
    await delay(50)
    return HttpResponse.json({
      categories: ['agent', 'visualization', 'tool', 'model']
    })
  }),
  
  http.get(`${API_BASE_URL}/marketplace/authors`, async () => {
    await delay(50)
    return HttpResponse.json({
      authors: ['langgenius', 'antv', 'community']
    })
  }),

  http.get(`${API_BASE_URL}/marketplace/plugins/:author/:name`, ({ params }) => {
    const plugin = mockPlugins.find(p => 
      p.author === params.author && p.name === params.name
    )
    
    if (!plugin) {
      return HttpResponse.json({ error: 'Plugin not found' }, { status: 404 })
    }
    
    return HttpResponse.json({
      ...plugin,
      versions: ['0.0.1', '0.0.5', '0.0.9'],
      readme: '# Example Plugin\n\nThis is a test plugin for Dify.'
    })
  }),

  // File endpoints
  http.get(`${API_BASE_URL}/files`, async () => {
    await delay(100)
    return HttpResponse.json({
      files: mockFiles,
      total: mockFiles.length
    })
  }),

  http.delete(`${API_BASE_URL}/files/:fileId`, ({ params }) => {
    const fileId = params.fileId as string
    const fileIndex = mockFiles.findIndex(f => f.id === fileId)
    
    if (fileIndex === -1) {
      return HttpResponse.json({ error: 'File not found' }, { status: 404 })
    }
    
    mockFiles.splice(fileIndex, 1)
    return HttpResponse.json({ message: 'File deleted successfully' })
  }),

  http.get(`${API_BASE_URL}/files/:fileId/download`, ({ params }) => {
    const file = mockFiles.find(f => f.id === params.fileId)
    
    if (!file) {
      return HttpResponse.json({ error: 'File not found' }, { status: 404 })
    }
    
    // Return a mock blob
    return new HttpResponse(new Blob(['mock file content']), {
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': `attachment; filename="${file.filename}"`
      }
    })
  }),

  // Health check
  http.get(`${API_BASE_URL}/health`, () => {
    return HttpResponse.json({ status: 'healthy' })
  })
]

// WebSocket handlers
export const wsHandlers = [
  ws.link('/ws/tasks/:taskId').addEventListener('connection', ({ client, params }) => {
    const taskId = params.taskId as string
    const task = mockTasks.get(taskId)
    
    if (!task) {
      client.send(JSON.stringify({
        type: 'error',
        message: 'Task not found'
      }))
      client.close(1008, 'Task not found')
      return
    }

    // Send initial connection success message
    client.send(JSON.stringify({
      type: 'connected',
      taskId: taskId
    }))

    // Simulate task progress messages
    const sendProgress = async () => {
      // Initial status
      await delay(100)
      client.send(JSON.stringify({
        type: 'status',
        status: 'processing',
        message: 'Starting repackaging process...'
      }))

      // Download phase
      await delay(500)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'download',
        progress: 25,
        message: 'Downloading plugin package...'
      }))

      await delay(500)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'download',
        progress: 50,
        message: 'Download completed'
      }))

      // Extract phase
      await delay(300)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'extract',
        progress: 60,
        message: 'Extracting package contents...'
      }))

      // Dependencies phase
      await delay(800)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'dependencies',
        progress: 75,
        message: 'Downloading Python dependencies...'
      }))

      await delay(1000)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'dependencies',
        progress: 90,
        message: 'Dependencies downloaded successfully'
      }))

      // Repackaging phase
      await delay(500)
      client.send(JSON.stringify({
        type: 'progress',
        phase: 'repackage',
        progress: 95,
        message: 'Creating offline package...'
      }))

      // Completion
      await delay(300)
      client.send(JSON.stringify({
        type: 'complete',
        status: 'completed',
        progress: 100,
        message: 'Repackaging completed successfully',
        result: {
          filename: task.filename || 'plugin-offline.difypkg',
          size: 1024000,
          download_url: `/api/v1/tasks/${taskId}/download`
        }
      }))

      // Close connection after completion
      setTimeout(() => {
        client.close(1000, 'Task completed')
      }, 100)
    }

    // Start sending progress messages
    sendProgress().catch(error => {
      client.send(JSON.stringify({
        type: 'error',
        message: 'An error occurred during repackaging',
        error: error.message
      }))
      client.close(1011, 'Internal error')
    })

    // Handle client messages
    client.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data.toString())
        
        if (data.type === 'ping') {
          client.send(JSON.stringify({ type: 'pong' }))
        }
      } catch (error) {
        // Ignore invalid messages
      }
    })
  }),

  // Error scenario WebSocket handler for testing error cases
  ws.link('/ws/tasks/error-task').addEventListener('connection', ({ client }) => {
    // Send initial connection success
    client.send(JSON.stringify({
      type: 'connected',
      taskId: 'error-task'
    }))

    // Simulate an error after a short delay
    setTimeout(() => {
      client.send(JSON.stringify({
        type: 'error',
        message: 'Failed to download plugin: Network error',
        error: 'NETWORK_ERROR'
      }))
      client.close(1011, 'Task failed')
    }, 500)
  }),

  // Timeout scenario WebSocket handler
  ws.link('/ws/tasks/timeout-task').addEventListener('connection', ({ client }) => {
    // Send initial connection but then no more messages (simulating timeout)
    client.send(JSON.stringify({
      type: 'connected',
      taskId: 'timeout-task'
    }))
    
    // Just keep the connection open without sending any progress
  })
]

// Combine HTTP and WebSocket handlers
export const handlers = [...httpHandlers, ...wsHandlers]