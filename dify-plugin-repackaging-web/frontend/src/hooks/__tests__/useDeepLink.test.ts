import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useDeepLink } from '../useDeepLink'

const setSearch = (search = '') => {
  window.history.replaceState({}, '', `/${search}`)
}

describe('useDeepLink', () => {
  afterEach(() => {
    window.history.replaceState({}, '', '/')
    vi.restoreAllMocks()
  })

  it.each([
    [
      '?url=https://marketplace.dify.ai/plugins/langgenius/agent',
      {
        type: 'marketplace',
        url: 'https://marketplace.dify.ai/plugins/langgenius/agent',
        author: 'langgenius',
        name: 'agent',
        version: null,
      },
    ],
    [
      '?url=https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9',
      {
        type: 'marketplace',
        url: 'https://marketplace.dify.ai/plugins/langgenius/agent/0.0.9',
        author: 'langgenius',
        name: 'agent',
        version: '0.0.9',
      },
    ],
    [
      '?url=https://example.com/plugin.difypkg',
      { type: 'url', url: 'https://example.com/plugin.difypkg' },
    ],
    [
      '?url=https://github.com/user/repo/releases/download/v1.0.0/plugin.difypkg',
      {
        type: 'url',
        url: 'https://github.com/user/repo/releases/download/v1.0.0/plugin.difypkg',
      },
    ],
    [
      '?other=param&url=https://marketplace.dify.ai/plugins/test/plugin&another=value',
      {
        type: 'marketplace',
        url: 'https://marketplace.dify.ai/plugins/test/plugin',
        author: 'test',
        name: 'plugin',
        version: null,
      },
    ],
    [
      `?url=${encodeURIComponent('https://marketplace.dify.ai/plugins/lang-genius/my-plugin')}`,
      {
        type: 'marketplace',
        url: 'https://marketplace.dify.ai/plugins/lang-genius/my-plugin',
        author: 'lang-genius',
        name: 'my-plugin',
        version: null,
      },
    ],
    [
      '?url=https://marketplace.dify.ai/plugins/author/name/',
      {
        type: 'marketplace',
        url: 'https://marketplace.dify.ai/plugins/author/name/',
        author: 'author',
        name: 'name',
        version: null,
      },
    ],
    [
      '?url=https://example.com/some/path',
      { type: 'url', url: 'https://example.com/some/path' },
    ],
  ])('parses deep link %s', (search, expected) => {
    setSearch(search)

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual(expected)
    expect(window.location.search).toBe('')
  })

  it.each(['', '?url=', '?url=not-a-url'])(
    'returns null for missing or invalid URL: %s',
    (search) => {
      setSearch(search)
      const { result } = renderHook(() => useDeepLink())
      expect(result.current).toBeNull()
    }
  )

  it('is stable across rerenders', () => {
    setSearch('?url=https://marketplace.dify.ai/plugins/test/plugin')
    const { result, rerender } = renderHook(() => useDeepLink())
    const firstResult = result.current

    rerender()

    expect(result.current).toBe(firstResult)
  })

  it.each([
    [
      '?author=langgenius&name=agent&version=0.0.9',
      { type: 'marketplace', author: 'langgenius', name: 'agent', version: '0.0.9' },
    ],
    [
      '?author=test&name=plugin',
      { type: 'marketplace', author: 'test', name: 'plugin', version: 'latest' },
    ],
  ])('supports legacy parameters: %s', (search, expected) => {
    setSearch(search)
    const replaceState = vi.spyOn(window.history, 'replaceState')

    const { result } = renderHook(() => useDeepLink())

    expect(result.current).toEqual(expected)
    expect(replaceState).toHaveBeenCalledWith({}, document.title, '/')
  })
})
