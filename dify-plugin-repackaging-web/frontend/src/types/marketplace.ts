/**
 * Marketplace type definitions
 * These types match the backend Pydantic models exactly
 */

export interface PluginVersion {
  version: string;
  created_at: string; // ISO datetime string
  changelog?: string;
  download_count?: number;
}

export interface PluginAuthor {
  name: string;
  display_name?: string;
  avatar_url?: string;
}

export interface Plugin {
  name: string;
  author: string;
  display_name: string;
  description: string;
  category: string;
  tags: string[];
  latest_version: string;
  icon_url?: string;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
  download_count?: number;
  rating?: number;
  verified: boolean;
}

export interface PluginDetails extends Plugin {
  readme?: string;
  license?: string;
  homepage_url?: string;
  repository_url?: string;
  available_versions: PluginVersion[];
  dependencies?: Record<string, string>;
  screenshots?: string[];
}

export interface PluginSearchResult {
  plugins: Plugin[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export interface MarketplaceCategory {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  plugin_count?: number;
}

export interface MarketplaceStats {
  total_plugins: number;
  total_downloads: number;
  categories: MarketplaceCategory[];
}

export interface PluginDownloadInfo {
  download_url: string;
  plugin: {
    author: string;
    name: string;
    version: string;
  };
  size?: number;
  checksum?: string;
}

export interface MarketplacePluginMetadata {
  source: 'marketplace';
  author: string;
  name: string;
  version: string;
  display_name?: string;
  category?: string;
  icon_url?: string;
}

// WebSocket message types
export interface MarketplaceSelectionMessage {
  type: 'marketplace_selection';
  plugin: MarketplacePluginMetadata;
  timestamp: string;
}

export interface TaskProgressMessage {
  task_id: string;
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  updated_at: string;
  error?: string;
  output_filename?: string;
  marketplace_metadata?: MarketplacePluginMetadata;
}

export type WebSocketMessage = 
  | { type: 'heartbeat' }
  | MarketplaceSelectionMessage
  | TaskProgressMessage;