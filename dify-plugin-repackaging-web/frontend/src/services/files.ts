import api from './api';
import type { DeleteFileResponse, FileListResponse } from '../types/file';
import { withErrorHandling } from './utils/errorHandler';

const API_BASE_URL = '/api/v1';

export const fileService = {
  /**
   * Get list of completed files
   * @param limit - Number of files to return (default: 20)
   * @param offset - Offset for pagination (default: 0)
   */
  listFiles: withErrorHandling(
    async (limit: number = 20, offset: number = 0): Promise<FileListResponse> => {
      const response = await api.get('/files', {
        params: { limit, offset }
      });
      return response.data;
    },
    {
      context: 'listFiles',
      defaultValue: { files: [], total: 0, limit: 20, offset: 0 },
      rethrow: true
    }
  ),

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
  deleteFile: withErrorHandling(
    async (fileId: string): Promise<DeleteFileResponse> => {
      const response = await api.delete<DeleteFileResponse>(`/files/${fileId}`);
      return response.data;
    },
    {
      context: 'deleteFile',
      rethrow: true // Re-throw as this is a user action
    }
  )
};
