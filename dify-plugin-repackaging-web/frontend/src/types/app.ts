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

export interface PluginMetadata {
  name: string;
  author: string;
  version: string;
  description?: string;
}

export type TabId = 'url' | 'marketplace' | 'file';