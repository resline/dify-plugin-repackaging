// WebSocket Test Helper for Playwright E2E Tests

export interface WebSocketMessage {
  type: string;
  status?: string;
  progress?: number;
  message?: string;
  error?: string;
  timestamp?: string;
  [key: string]: any;
}

export class WebSocketTestHelper {
  private ws: WebSocket | null = null;
  private messages: WebSocketMessage[] = [];
  private connected = false;
  private onMessageCallbacks: ((msg: WebSocketMessage) => void)[] = [];
  
  async connect(taskId: string, baseUrl: string): Promise<WebSocketTestHelper> {
    // Convert http to ws protocol
    const wsUrl = baseUrl
      .replace('http://', 'ws://')
      .replace('https://', 'wss://')
      .replace(/\/$/, '') + `/ws/tasks/${taskId}`;
    
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          this.connected = true;
          console.log(`WebSocket connected to ${wsUrl}`);
          resolve(this);
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(new Error(`WebSocket connection failed: ${error}`));
        };
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.messages.push(data);
            
            // Notify callbacks
            this.onMessageCallbacks.forEach(callback => callback(data));
            
            // Log specific message types
            if (data.type === 'status_update') {
              console.log(`Status: ${data.status}, Progress: ${data.progress}%`);
            } else if (data.type === 'log') {
              console.log(`Log: ${data.message}`);
            } else if (data.type === 'error') {
              console.error(`Error: ${data.error}`);
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };
        
        this.ws.onclose = () => {
          this.connected = false;
          console.log('WebSocket disconnected');
        };
        
        // Set a connection timeout
        setTimeout(() => {
          if (!this.connected) {
            this.disconnect();
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);
        
      } catch (error) {
        reject(error);
      }
    });
  }
  
  async waitForMessage(
    predicate: (msg: WebSocketMessage) => boolean, 
    timeout = 30000
  ): Promise<WebSocketMessage> {
    const startTime = Date.now();
    
    // Check existing messages
    const existingMessage = this.messages.find(predicate);
    if (existingMessage) return existingMessage;
    
    // Wait for new messages
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Timeout waiting for WebSocket message after ${timeout}ms`));
      }, timeout);
      
      const checkMessage = (msg: WebSocketMessage) => {
        if (predicate(msg)) {
          clearTimeout(timeoutId);
          resolve(msg);
        }
      };
      
      this.onMessageCallbacks.push(checkMessage);
      
      // Also periodically check existing messages
      const checkInterval = setInterval(() => {
        const message = this.messages.find(predicate);
        if (message) {
          clearTimeout(timeoutId);
          clearInterval(checkInterval);
          resolve(message);
        }
        
        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
        }
      }, 100);
    });
  }
  
  async waitForStatus(status: string, timeout = 60000): Promise<WebSocketMessage> {
    return this.waitForMessage(
      msg => msg.status === status,
      timeout
    );
  }
  
  async waitForProgress(minProgress: number, timeout = 30000): Promise<WebSocketMessage> {
    return this.waitForMessage(
      msg => (msg.progress || 0) >= minProgress,
      timeout
    );
  }
  
  async waitForCompletion(timeout = 120000): Promise<WebSocketMessage> {
    return this.waitForStatus('completed', timeout);
  }
  
  async waitForError(timeout = 30000): Promise<WebSocketMessage> {
    return this.waitForMessage(
      msg => msg.status === 'failed' || msg.type === 'error',
      timeout
    );
  }
  
  getMessages(): WebSocketMessage[] {
    return [...this.messages];
  }
  
  getLastMessage(): WebSocketMessage | undefined {
    return this.messages[this.messages.length - 1];
  }
  
  getMessagesByType(type: string): WebSocketMessage[] {
    return this.messages.filter(msg => msg.type === type);
  }
  
  getProgress(): number {
    const progressMessages = this.messages
      .filter(msg => msg.progress !== undefined)
      .sort((a, b) => (b.progress || 0) - (a.progress || 0));
    
    return progressMessages[0]?.progress || 0;
  }
  
  getStatus(): string | undefined {
    const statusMessages = this.messages.filter(msg => msg.status);
    return statusMessages[statusMessages.length - 1]?.status;
  }
  
  getLogs(): string[] {
    return this.messages
      .filter(msg => msg.type === 'log' && msg.message)
      .map(msg => msg.message!);
  }
  
  clearMessages() {
    this.messages = [];
  }
  
  onMessage(callback: (msg: WebSocketMessage) => void) {
    this.onMessageCallbacks.push(callback);
  }
  
  isConnected(): boolean {
    return this.connected && this.ws?.readyState === WebSocket.OPEN;
  }
  
  async sendMessage(message: any) {
    if (!this.isConnected()) {
      throw new Error('WebSocket is not connected');
    }
    
    this.ws!.send(JSON.stringify(message));
  }
  
  // Send ping to keep connection alive
  async ping() {
    await this.sendMessage({ type: 'ping', timestamp: Date.now() });
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this.onMessageCallbacks = [];
  }
}

// Helper function to monitor WebSocket traffic in Playwright
export async function monitorWebSocketTraffic(page: any, callback: (data: any) => void) {
  page.on('websocket', (ws: any) => {
    console.log(`WebSocket opened: ${ws.url()}`);
    
    ws.on('framesent', (event: any) => {
      console.log(`>> Sent: ${event.payload}`);
    });
    
    ws.on('framereceived', (event: any) => {
      console.log(`<< Received: ${event.payload}`);
      try {
        const data = JSON.parse(event.payload);
        callback(data);
      } catch (e) {
        // Not JSON, ignore
      }
    });
    
    ws.on('close', () => {
      console.log('WebSocket closed');
    });
  });
}

// Mock WebSocket server for testing
export class MockWebSocketServer {
  private messages: any[] = [];
  
  constructor(private page: any) {}
  
  async setup() {
    await this.page.route('**/ws/tasks/*', (route: any) => {
      // Intercept WebSocket connections
      route.fulfill({
        status: 101,
        headers: {
          'Upgrade': 'websocket',
          'Connection': 'Upgrade',
        }
      });
    });
  }
  
  async simulateProgress(taskId: string, progress: number) {
    await this.page.evaluate(({ taskId, progress }) => {
      // Emit custom event that test can listen to
      window.postMessage({
        type: 'ws-mock',
        data: {
          type: 'status_update',
          task_id: taskId,
          status: 'processing',
          progress: progress
        }
      }, '*');
    }, { taskId, progress });
  }
  
  async simulateCompletion(taskId: string, outputFilename: string) {
    await this.page.evaluate(({ taskId, outputFilename }) => {
      window.postMessage({
        type: 'ws-mock',
        data: {
          type: 'status_update',
          task_id: taskId,
          status: 'completed',
          progress: 100,
          output_filename: outputFilename
        }
      }, '*');
    }, { taskId, outputFilename });
  }
  
  async simulateError(taskId: string, error: string) {
    await this.page.evaluate(({ taskId, error }) => {
      window.postMessage({
        type: 'ws-mock',
        data: {
          type: 'error',
          task_id: taskId,
          status: 'failed',
          error: error
        }
      }, '*');
    }, { taskId, error });
  }
}

// Utility to wait for WebSocket events in tests
export class WebSocketEventWaiter {
  private events: any[] = [];
  
  constructor(private page: any) {
    this.setupListener();
  }
  
  private setupListener() {
    this.page.on('websocket', (ws: any) => {
      ws.on('framereceived', (event: any) => {
        try {
          const data = JSON.parse(event.payload);
          this.events.push(data);
        } catch (e) {
          // Ignore non-JSON frames
        }
      });
    });
  }
  
  async waitForEvent(predicate: (event: any) => boolean, timeout = 30000): Promise<any> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const event = this.events.find(predicate);
      if (event) return event;
      
      await this.page.waitForTimeout(100);
    }
    
    throw new Error(`Timeout waiting for WebSocket event after ${timeout}ms`);
  }
  
  getEvents(): any[] {
    return [...this.events];
  }
  
  clear() {
    this.events = [];
  }
}