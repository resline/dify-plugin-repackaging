import { Page } from '@playwright/test';

export class WebSocketHelper {
  private page: Page;
  private messages: any[] = [];
  private connectionState: 'connecting' | 'open' | 'closed' = 'connecting';

  constructor(page: Page) {
    this.page = page;
  }

  async interceptWebSocket() {
    // Inject WebSocket interceptor into the page
    await this.page.addInitScript(() => {
      // Store original WebSocket
      const OriginalWebSocket = window.WebSocket;
      
      // Create interceptor
      (window as any).WebSocket = class InterceptedWebSocket extends OriginalWebSocket {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(url, protocols);
          
          // Store WebSocket instance
          (window as any).__wsInstance = this;
          (window as any).__wsMessages = [];
          (window as any).__wsState = 'connecting';
          
          // Intercept events
          this.addEventListener('open', () => {
            (window as any).__wsState = 'open';
            console.log('[WS Test] WebSocket opened:', url);
          });
          
          this.addEventListener('message', (event) => {
            const message = {
              type: 'received',
              data: event.data,
              timestamp: Date.now()
            };
            (window as any).__wsMessages.push(message);
            console.log('[WS Test] Message received:', event.data);
          });
          
          this.addEventListener('close', () => {
            (window as any).__wsState = 'closed';
            console.log('[WS Test] WebSocket closed');
          });
          
          this.addEventListener('error', (error) => {
            console.error('[WS Test] WebSocket error:', error);
          });
          
          // Intercept send
          const originalSend = this.send.bind(this);
          this.send = (data: any) => {
            const message = {
              type: 'sent',
              data: data,
              timestamp: Date.now()
            };
            (window as any).__wsMessages.push(message);
            console.log('[WS Test] Message sent:', data);
            return originalSend(data);
          };
        }
      };
    });
  }

  async waitForConnection(timeout: number = 10000) {
    await this.page.waitForFunction(
      () => (window as any).__wsState === 'open',
      { timeout }
    );
    this.connectionState = 'open';
  }

  async waitForMessage(predicate: (message: any) => boolean, timeout: number = 10000) {
    const message = await this.page.waitForFunction(
      (pred: string) => {
        const messages = (window as any).__wsMessages || [];
        const predicateFn = eval(`(${pred})`);
        return messages.find((msg: any) => msg.type === 'received' && predicateFn(msg));
      },
      predicate.toString(),
      { timeout }
    );
    
    return await message.jsonValue();
  }

  async waitForMessageType(type: string, timeout: number = 10000) {
    return await this.waitForMessage((msg) => {
      try {
        const data = typeof msg.data === 'string' ? JSON.parse(msg.data) : msg.data;
        return data.type === type;
      } catch {
        return false;
      }
    }, timeout);
  }

  async getAllMessages() {
    const messages = await this.page.evaluate(() => {
      return (window as any).__wsMessages || [];
    });
    this.messages = messages;
    return messages;
  }

  async getReceivedMessages() {
    const messages = await this.getAllMessages();
    return messages.filter(msg => msg.type === 'received');
  }

  async getSentMessages() {
    const messages = await this.getAllMessages();
    return messages.filter(msg => msg.type === 'sent');
  }

  async getConnectionState() {
    const state = await this.page.evaluate(() => {
      return (window as any).__wsState || 'unknown';
    });
    this.connectionState = state as any;
    return state;
  }

  async sendMessage(data: any) {
    await this.page.evaluate((message) => {
      const ws = (window as any).__wsInstance;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(typeof message === 'string' ? message : JSON.stringify(message));
      } else {
        throw new Error('WebSocket is not connected');
      }
    }, data);
  }

  async closeConnection() {
    await this.page.evaluate(() => {
      const ws = (window as any).__wsInstance;
      if (ws) {
        ws.close();
      }
    });
    this.connectionState = 'closed';
  }

  async simulateDisconnection() {
    // Simulate network disconnection by closing the WebSocket
    await this.closeConnection();
  }

  async clearMessages() {
    await this.page.evaluate(() => {
      (window as any).__wsMessages = [];
    });
    this.messages = [];
  }

  // Helper to parse message data
  parseMessageData(message: any) {
    if (typeof message.data === 'string') {
      try {
        return JSON.parse(message.data);
      } catch {
        return message.data;
      }
    }
    return message.data;
  }

  // Wait for specific task status
  async waitForTaskStatus(status: string, timeout: number = 30000) {
    return await this.waitForMessage((msg) => {
      const data = this.parseMessageData(msg);
      return data.status === status;
    }, timeout);
  }

  // Wait for task completion
  async waitForTaskComplete(timeout: number = 60000) {
    return await this.waitForTaskStatus('completed', timeout);
  }

  // Monitor connection stability
  async monitorConnectionStability(duration: number = 5000) {
    const startState = await this.getConnectionState();
    const states: string[] = [startState];
    
    const interval = setInterval(async () => {
      const state = await this.getConnectionState();
      states.push(state);
    }, 1000);
    
    await this.page.waitForTimeout(duration);
    clearInterval(interval);
    
    return {
      stable: states.every(s => s === startState),
      states,
      changes: states.filter((s, i) => i === 0 || s !== states[i - 1]).length - 1
    };
  }
}