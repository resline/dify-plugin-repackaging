/**
 * Enhanced WebSocket service with auto-reconnect and heartbeat functionality
 */

export interface WebSocketOptions {
  taskId: string;
  onOpen?: () => void;
  onMessage?: (data: any) => void;
  onError?: (error: Event) => void;
  onClose?: (event?: CloseEvent) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export class ReconnectingWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private options: WebSocketOptions;
  private reconnectAttempts = 0;
  private isReconnecting = false;
  private heartbeatTimer: NodeJS.Timer | null = null;
  private reconnectTimer: NodeJS.Timer | null = null;
  private lastPongTime: number = Date.now();
  private isManualClose = false;

  constructor(options: WebSocketOptions) {
    this.taskId = options.taskId;
    this.options = {
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      ...options,
    };
    
    this.connect();
  }

  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/tasks/${this.taskId}`;
  }

  private connect(): void {
    try {
      this.ws = new WebSocket(this.getWebSocketUrl());
      this.setupEventHandlers();
    } catch (error) {
      if (process.env.NODE_ENV !== 'test') {
        console.error('Failed to create WebSocket:', error);
      }
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log(`WebSocket connected for task ${this.taskId}`);
      this.reconnectAttempts = 0;
      this.isReconnecting = false;
      this.startHeartbeat();
      
      if (this.options.onOpen) {
        this.options.onOpen();
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        switch (data.type) {
          case 'ping':
            // Respond to server ping with pong
            this.sendPong();
            break;
          case 'heartbeat':
            // Server heartbeat, update last pong time
            this.lastPongTime = Date.now();
            break;
          case 'pong':
            // Server acknowledged our ping
            this.lastPongTime = Date.now();
            break;
          default:
            // Regular message
            if (this.options.onMessage) {
              this.options.onMessage(data);
            }
        }
      } catch (error) {
        if (process.env.NODE_ENV !== 'test') {
          console.error('Error parsing WebSocket message:', error);
        }
      }
    };

    this.ws.onerror = (error) => {
      if (process.env.NODE_ENV !== 'test') {
        console.error(`WebSocket error for task ${this.taskId}:`, error);
      }
      
      if (this.options.onError) {
        this.options.onError(error);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`WebSocket closed for task ${this.taskId}. Code: ${event.code}, Reason: ${event.reason}`);
      this.stopHeartbeat();
      
      // Check for specific close codes
      if (event.code === 1008 && event.reason === 'Task not found') {
        if (process.env.NODE_ENV !== 'test') {
          console.error(`Task ${this.taskId} not found. WebSocket connection rejected.`);
        }
        // Don't attempt to reconnect for non-existent tasks
        this.isManualClose = true;
      }
      
      if (this.options.onClose) {
        this.options.onClose(event);
      }
      
      // Only attempt reconnect if not manually closed and auto-reconnect is enabled
      if (!this.isManualClose && this.options.autoReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    // Send periodic pings to keep connection alive
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Check if we've received a response recently
        const timeSinceLastPong = Date.now() - this.lastPongTime;
        if (timeSinceLastPong > this.options.heartbeatInterval! * 2) {
          if (process.env.NODE_ENV !== 'test') {
            console.warn(`No pong received for ${timeSinceLastPong}ms, reconnecting...`);
          }
          this.reconnect();
          return;
        }
        
        // Send ping
        this.send({ type: 'ping', timestamp: Date.now() });
      }
    }, this.options.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private sendPong(): void {
    this.send({ type: 'pong', timestamp: Date.now() });
  }

  private scheduleReconnect(): void {
    if (this.isReconnecting || this.isManualClose) return;
    
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts!) {
      if (process.env.NODE_ENV !== 'test') {
        console.error(`Max reconnection attempts (${this.options.maxReconnectAttempts}) reached for task ${this.taskId}`);
      }
      return;
    }
    
    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    const delay = Math.min(
      this.options.reconnectInterval! * Math.pow(1.5, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms...`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  public reconnect(): void {
    this.close(false);
    this.connect();
  }

  public send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        const message = typeof data === 'string' ? data : JSON.stringify(data);
        this.ws.send(message);
      } catch (error) {
        if (process.env.NODE_ENV !== 'test') {
          console.error('Error sending WebSocket message:', error);
        }
      }
    } else {
      if (process.env.NODE_ENV !== 'test') {
        console.warn('WebSocket is not open, cannot send message');
      }
    }
  }

  public close(manual = true): void {
    this.isManualClose = manual;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public getReadyState(): number {
    return this.ws ? this.ws.readyState : WebSocket.CLOSED;
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Factory function for creating WebSocket connections
export function createReconnectingWebSocket(taskId: string, options?: Partial<WebSocketOptions>): ReconnectingWebSocket {
  return new ReconnectingWebSocket({
    taskId,
    ...options,
  });
}

// Export WebSocket states for convenience
export const WebSocketState = {
  CONNECTING: WebSocket.CONNECTING,
  OPEN: WebSocket.OPEN,
  CLOSING: WebSocket.CLOSING,
  CLOSED: WebSocket.CLOSED,
} as const;