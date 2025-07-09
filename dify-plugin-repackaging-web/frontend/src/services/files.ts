import api from './api';
import type { FileInfo, FileListResponse } from '../types/file';

const API_BASE_URL = '/api/v1';

export const fileService = {
  /**
   * Get list of completed files
   * @param limit - Number of files to return (default: 20)
   * @param offset - Offset for pagination (default: 0)
   */
  listFiles: async (limit: number = 20, offset: number = 0): Promise<FileListResponse> => {
    const response = await api.get('/files', {
      params: { limit, offset }
    });
    return response.data;
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
    await api.delete(`/files/${fileId}`);
  }
};