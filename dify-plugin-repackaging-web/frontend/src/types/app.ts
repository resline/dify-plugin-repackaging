export interface Task {
  task_id: string;
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'failed';
  message?: string;
  error?: string;
  progress: number;
  download_url?: string;
  output_filename?: string;
  created_at?: string;
  completed_at?: string;
  plugin_metadata?: PluginMetadata;
  marketplace_metadata?: PluginMetadata;
  plugin_info?: PluginMetadata;
}

export interface TaskStartResponse {
  task_id: string;
}

export interface RepackageFormData {
  url: string;
  platform: string;
  suffix: string;
}

export interface MarketplaceSelection {
  author: string;
  name: string;
  version?: string;
  platform?: string;
  suffix?: string;
  description?: string;
}

export interface FileUploadSelection {
  file: File;
  platform: string;
  suffix: string;
}

export interface CompletedTask {
  task_id: string;
  status: 'completed';
  created_at: string;
  completed_at: string;
  output_filename: string;
  download_url: string;
  plugin_metadata?: PluginMetadata;
  marketplace_metadata?: PluginMetadata;
  plugin_info?: PluginMetadata;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

export interface PluginMetadata {
  name: string;
  author: string;
  version: string;
  description?: string;
}

export type TabId = 'url' | 'marketplace' | 'file' | 'completed';
