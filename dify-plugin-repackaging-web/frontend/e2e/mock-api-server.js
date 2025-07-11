const http = require('http');

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Mock responses
  if (req.url === '/api/v1/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'healthy' }));
  } else if (req.url === '/api/v1/tasks?limit=10' || req.url === '/api/v1/tasks') {
    res.writeHead(200);
    res.end(JSON.stringify({ tasks: [] }));
  } else if (req.url === '/api/v1/tasks/completed') {
    res.writeHead(200);
    res.end(JSON.stringify({ tasks: [] }));
  } else if (req.url === '/api/v1/files') {
    res.writeHead(200);
    res.end(JSON.stringify({ files: [] }));
  } else if (req.url.startsWith('/api/v1/marketplace/plugins')) {
    res.writeHead(200);
    res.end(JSON.stringify({ plugins: [], total: 0 }));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

const PORT = 8000;
server.listen(PORT, () => {
  console.log(`Mock API server running on http://localhost:${PORT}`);
});