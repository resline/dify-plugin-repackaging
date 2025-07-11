const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// Mock data
const tasks = [];
const files = [];
const plugins = [
  {
    id: '1',
    author: 'langgenius',
    name: 'agent',
    version: '0.0.9',
    description: 'Agent plugin for Dify'
  },
  {
    id: '2', 
    author: 'antv',
    name: 'visualization',
    version: '0.1.7',
    description: 'Data visualization plugin'
  }
];

// Health check
app.get('/api/v1/health', (req, res) => {
  res.json({ status: 'healthy' });
});

// Tasks endpoints
app.get('/api/v1/tasks', (req, res) => {
  res.json({ tasks: tasks.slice(0, req.query.limit || 10) });
});

app.get('/api/v1/tasks/completed', (req, res) => {
  res.json({ tasks: [] });
});

app.post('/api/v1/tasks', (req, res) => {
  const taskId = Math.random().toString(36).substring(7);
  tasks.push({ id: taskId, ...req.body, status: 'pending' });
  res.json({ task_id: taskId });
});

// Files endpoints
app.get('/api/v1/files', (req, res) => {
  res.json({ files: files });
});

// Marketplace endpoints
app.get('/api/v1/marketplace/plugins', (req, res) => {
  res.json({ plugins: plugins, total: plugins.length });
});

// WebSocket mock (just acknowledge connection)
app.ws('/ws/tasks/:taskId', (ws, req) => {
  ws.on('message', msg => {
    ws.send(JSON.stringify({ type: 'pong' }));
  });
  
  // Send initial message
  ws.send(JSON.stringify({ 
    type: 'log', 
    level: 'info', 
    message: 'Task started',
    timestamp: new Date().toISOString()
  }));
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`Mock server running on port ${PORT}`);
});