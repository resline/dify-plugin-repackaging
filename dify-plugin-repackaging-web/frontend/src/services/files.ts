import api from './api';
import type { FileInfo, FileListResponse } from '../types/file';
import axios from 'axios';

const API_BASE_URL = '/api/v1';

// Error handler specifically for file operations
const handleFileError = (error: unknown, operation: string): never => {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 404) {
      throw new Error(`File or endpoint not found (${operation})`);
    } else if (error.response?.status === 403) {
      throw new Error(`Access denied to file (${operation})`);
    } else if (error.response?.status >= 500) {
      throw new Error(`Server error during ${operation}. Please try again later.`);
    }
  }
  throw error;
};

export const fileService = {
  /**
   * Get list of completed files
   * @param limit - Number of files to return (default: 20)
   * @param offset - Offset for pagination (default: 0)
   */
  listFiles: async (limit: number = 20, offset: number = 0): Promise<FileListResponse> => {
    try {
      const response = await api.get('/files', {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      return handleFileError(error, 'list files');
    }
  },

  /**
   * Get download URL for a specific file
   * @param fileId - ID of the file to download
   */
  getDownloadUrl: (fileId: string): string => {
    return `${API_BASE_URL}/files/${fileId}/download`;
  },

  /**
   * Delete a specific file
   * @param fileId - ID of the file to delete
   */
  deleteFile: async (fileId: string): Promise<void> => {
    try {
      await api.delete(`/files/${fileId}`);
    } catch (error) {
      return handleFileError(error, 'delete file');
    }
  }
};