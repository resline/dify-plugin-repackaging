import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fileService } from '../files'
import { server } from '../../test/mocks/server'
import { http, HttpResponse } from 'msw'

describe('File Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listFiles', () => {
    it('retrieves list of files', async () => {
      const result = await fileService.listFiles()
      
      expect(result).toHaveProperty('files')
      expect(result).toHaveProperty('total')
      expect(Array.isArray(result.files)).toBe(true)
      expect(result.files.length).toBeGreaterThan(0)
      
      // Check file structure
      const file = result.files[0]
      expect(file).toHaveProperty('id')
      expect(file).toHaveProperty('filename')
      expect(file).toHaveProperty('size')
      expect(file).toHaveProperty('created_at')
      expect(file).toHaveProperty('download_url')
    })

    it('handles empty file list', async () => {
      server.use(
        http.get('/api/v1/files', () => {
          return HttpResponse.json({
            files: [],
            total: 0
          })
        })
      )

      const result = await fileService.listFiles()
      
      expect(result.files).toHaveLength(0)
      expect(result.total).toBe(0)
    })

    it('handles server errors', async () => {
      server.use(
        http.get('/api/v1/files', () => {
          return HttpResponse.json({ error: 'Server error' }, { status: 500 })
        })
      )

      await expect(fileService.listFiles()).rejects.toThrow()
    })
  })

  describe('deleteFile', () => {
    it('deletes a file successfully', async () => {
      const fileId = '1'
      const result = await fileService.deleteFile(fileId)
      
      expect(result).toHaveProperty('message', 'File deleted successfully')
    })

    it('handles non-existent file', async () => {
      const fileId = 'non-existent'
      
      server.use(
        http.delete(`/api/v1/files/${fileId}`, () => {
          return HttpResponse.json({ error: 'File not found' }, { status: 404 })
        })
      )

      await expect(fileService.deleteFile(fileId)).rejects.toThrow()
    })

    it('handles deletion errors', async () => {
      server.use(
        http.delete('/api/v1/files/:fileId', () => {
          return HttpResponse.json({ error: 'Permission denied' }, { status: 403 })
        })
      )

      await expect(fileService.deleteFile('1')).rejects.toThrow()
    })
  })

  describe('downloadFile', () => {
    it('returns correct download URL', () => {
      const fileId = 'test-file-123'
      const url = fileService.downloadFile(fileId)
      
      expect(url).toBe(`/api/v1/files/${fileId}/download`)
    })
  })
})