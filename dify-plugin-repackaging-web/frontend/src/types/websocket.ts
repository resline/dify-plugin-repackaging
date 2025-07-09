/**
 * WebSocket message types and interfaces
 */

export interface WebSocketMessage {
  type: string;
  timestamp?: number;
  [key: string]: any;
}

export interface PingMessage extends WebSocketMessage {
  type: 'ping';
  timestamp: number;
}

export interface PongMessage extends WebSocketMessage {
  type: 'pong';
  timestamp: number;
}

export interface HeartbeatMessage extends WebSocketMessage {
  type: 'heartbeat';
  timestamp: number;
}

export interface TaskUpdateMessage extends WebSocketMessage {
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'failed';
  message?: string;
  error?: string;
  progress?: number;
  download_url?: string;
  output_filename?: string;
  plugin_metadata?: any;
  marketplace_metadata?: any;
  plugin_info?: any;
  created_at?: string;
  completed_at?: string;
}

export interface MarketplaceSelectionMessage extends WebSocketMessage {
  type: 'marketplace_selection';
  plugin: any;
  timestamp: string;
}

export type WebSocketConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';

export interface WebSocketStats {
  messagesSent: number;
  messagesReceived: number;
  reconnectAttempts: number;
  lastConnectedAt?: Date;
  lastDisconnectedAt?: Date;
  lastError?: string;
}