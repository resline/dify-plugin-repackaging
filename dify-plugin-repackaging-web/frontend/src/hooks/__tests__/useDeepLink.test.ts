import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useDeepLink } from '../useDeepLink'

describe('useDeepLink', () => {
  const originalLocation = window.location

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset window.location
    delete (window as any).location
    window.location = { ...originalLocation }
  })

  afterEach(() => {
    window.location = originalLocation
  })

  it('parses marketplace URL correctly', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://marketplace.dify.ai/plugins/langgenius/agent'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      url: 'https://marketplace.dify.ai/plugins/langgenius/agent',
      author: 'langgenius',
      name: 'agent',
      version: null
    })
  })

  it('parses marketplace URL with version', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      url: 'https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9',
      author: 'langgenius',
      name: 'agent',
      version: '0.0.9'
    })
  })

  it('parses direct .difypkg URL', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://example.com/plugin.difypkg'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'url',
      url: 'https://example.com/plugin.difypkg'
    })
  })

  it('parses GitHub release URL', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://github.com/user/repo/releases/download/v1.0.0/plugin.difypkg'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'url',
      url: 'https://github.com/user/repo/releases/download/v1.0.0/plugin.difypkg'
    })
  })

  it('returns null when no URL parameter', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: ''
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toBeNull()
  })

  it('returns null for invalid URL', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=not-a-url'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toBeNull()
  })

  it('handles URL with additional parameters', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?other=param&url=https://marketplace.dify.ai/plugins/test/plugin&another=value'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      url: 'https://marketplace.dify.ai/plugins/test/plugin',
      author: 'test',
      name: 'plugin',
      version: null
    })
  })

  it('decodes URL-encoded parameters', () => {
    const encodedUrl = encodeURIComponent('https://marketplace.dify.ai/plugins/lang-genius/my-plugin')
    
    Object.defineProperty(window, 'location', {
      value: {
        search: `?url=${encodedUrl}`
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      url: 'https://marketplace.dify.ai/plugins/lang-genius/my-plugin',
      author: 'lang-genius',
      name: 'my-plugin',
      version: null
    })
  })

  it('handles marketplace URL with trailing slash', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://marketplace.dify.ai/plugins/author/name/'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      url: 'https://marketplace.dify.ai/plugins/author/name/',
      author: 'author',
      name: 'name',
      version: null
    })
  })

  it('returns direct type for non-.difypkg URLs that are not marketplace', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://example.com/some/path'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'url',
      url: 'https://example.com/some/path'
    })
  })

  it('handles empty URL parameter', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url='
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toBeNull()
  })

  it('is stable across re-renders', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?url=https://marketplace.dify.ai/plugins/test/plugin'
      },
      writable: true
    })

    const { result, rerender } = renderHook(() => useDeepLink())
    const firstResult = result.current

    rerender()

    expect(result.current).toBe(firstResult)
  })

  it('handles legacy individual parameters format', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?author=langgenius&name=agent&version=0.0.9',
        pathname: '/'
      },
      writable: true
    })

    // Mock history.replaceState
    const originalReplaceState = window.history.replaceState
    window.history.replaceState = vi.fn()

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      author: 'langgenius',
      name: 'agent',
      version: '0.0.9'
    })

    // Verify URL was cleared
    expect(window.history.replaceState).toHaveBeenCalledWith({}, document.title, '/')

    // Restore
    window.history.replaceState = originalReplaceState
  })

  it('handles legacy parameters without version', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?author=test&name=plugin',
        pathname: '/'
      },
      writable: true
    })

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual({
      type: 'marketplace',
      author: 'test',
      name: 'plugin',
      version: 'latest'
    })
  })
})