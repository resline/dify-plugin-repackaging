export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warning' | 'error' | 'success' | 'processing';
  message: string;
  details?: string;
}

export interface LogViewerProps {
  logs: LogEntry[];
  height?: number;
  darkMode?: boolean;
  autoScroll?: boolean;
  showTimestamps?: boolean;
  showCopyButton?: boolean;
  className?: string;
}