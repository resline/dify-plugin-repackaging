import { describe, it, expect, vi, beforeEach } from 'vitest'
import { marketplaceService } from '../marketplace'
import { server } from '../../test/mocks/server'
import { http, HttpResponse } from 'msw'

describe('Marketplace Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('searchPlugins', () => {
    it('retrieves plugins without search query', async () => {
      const result = await marketplaceService.searchPlugins()
      
      expect(result).toHaveProperty('plugins')
      expect(result).toHaveProperty('total')
      expect(Array.isArray(result.plugins)).toBe(true)
      expect(result.plugins.length).toBeGreaterThan(0)
    })

    it('searches plugins with query', async () => {
      const result = await marketplaceService.searchPlugins({ q: 'visual' })
      
      expect(result.plugins).toHaveLength(1)
      expect(result.plugins[0].name).toBe('visualization')
    })

    it('returns empty results for no matches', async () => {
      const result = await marketplaceService.searchPlugins({ q: 'nonexistent' })
      
      expect(result.plugins).toHaveLength(0)
      expect(result.total).toBe(0)
    })

    it('handles API errors gracefully', async () => {
      server.use(
        http.get('/api/v1/marketplace/plugins', () => {
          return HttpResponse.json({ error: 'Server error' }, { status: 500 })
        })
      )

      await expect(marketplaceService.searchPlugins()).rejects.toThrow()
    })

    it('sends correct query parameters', async () => {
      let capturedUrl = ''
      
      server.use(
        http.get('/api/v1/marketplace/plugins', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json({ plugins: [], total: 0 })
        })
      )

      await marketplaceService.searchPlugins({ q: 'test query' })
      
      expect(new URL(capturedUrl).searchParams.get('q')).toBe('test query')
    })
  })

  describe('getPluginDetails', () => {
    it('retrieves plugin details successfully', async () => {
      const result = await marketplaceService.getPluginDetails('langgenius', 'agent')
      
      expect(result).toHaveProperty('author', 'langgenius')
      expect(result).toHaveProperty('name', 'agent')
      expect(result).toHaveProperty('version')
      expect(result).toHaveProperty('versions')
      expect(result).toHaveProperty('readme')
    })

    it('handles non-existent plugin', async () => {
      await expect(
        marketplaceService.getPluginDetails('unknown', 'plugin')
      ).rejects.toThrow()
    })

    it('constructs correct URL path', async () => {
      let capturedPath: string | null = null
      
      server.use(
        http.get('/api/v1/marketplace/plugins/:author/:name', ({ params }) => {
          capturedPath = `${params.author}/${params.name}`
          return HttpResponse.json({
            author: params.author,
            name: params.name,
            version: '1.0.0',
            versions: ['1.0.0'],
            readme: 'Test'
          })
        })
      )

      await marketplaceService.getPluginDetails('test-author', 'test-plugin')
      
      expect(capturedPath).toBe('test-author/test-plugin')
    })

    it('includes extended plugin information', async () => {
      const result = await marketplaceService.getPluginDetails('langgenius', 'agent')
      
      // Should include base plugin info plus extended details
      expect(result).toHaveProperty('description')
      expect(result).toHaveProperty('downloads')
      expect(result).toHaveProperty('created_at')
      expect(result).toHaveProperty('updated_at')
      expect(result).toHaveProperty('versions')
      expect(result).toHaveProperty('readme')
    })
  })

  describe('Error Handling', () => {
    it('propagates network errors', async () => {
      server.use(
        http.get('/api/v1/marketplace/plugins', () => {
          return HttpResponse.error()
        })
      )

      await expect(marketplaceService.searchPlugins()).rejects.toThrow()
    })

    it('handles malformed responses', async () => {
      server.use(
        http.get('/api/v1/marketplace/plugins', () => {
          return HttpResponse.text('Invalid JSON')
        })
      )

      await expect(marketplaceService.searchPlugins()).rejects.toThrow()
    })
  })

  describe('Cache Behavior', () => {
    it('does not cache search results by default', async () => {
      let callCount = 0
      
      server.use(
        http.get('/api/v1/marketplace/plugins', () => {
          callCount++
          return HttpResponse.json({ plugins: [], total: 0 })
        })
      )

      await marketplaceService.searchPlugins({ q: 'test' })
      await marketplaceService.searchPlugins({ q: 'test' })
      
      expect(callCount).toBe(2)
    })

    it('makes separate requests for different queries', async () => {
      const queries: string[] = []
      
      server.use(
        http.get('/api/v1/marketplace/plugins', ({ request }) => {
          const url = new URL(request.url)
          queries.push(url.searchParams.get('q') || '')
          return HttpResponse.json({ plugins: [], total: 0 })
        })
      )

      await marketplaceService.searchPlugins({ q: 'query1' })
      await marketplaceService.searchPlugins({ q: 'query2' })
      
      expect(queries).toEqual(['query1', 'query2'])
    })
  })
})
