export interface FileInfo {
  file_id: string;
  filename: string;
  size: number;
  created_at: string;
  plugin_info?: {
    name: string;
    author: string;
    version: string;
    description?: string;
  };
  download_url: string;
}

export interface FileListResponse {
  files: FileInfo[];
  total: number;
  limit: number;
  offset: number;
  has_more?: boolean;
}

export interface DeleteFileResponse {
  message: string;
  file_id: string;
}
