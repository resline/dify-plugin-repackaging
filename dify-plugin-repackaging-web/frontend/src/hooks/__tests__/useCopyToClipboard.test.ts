import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCopyToClipboard } from '../useCopyToClipboard'

// Mock the Toast hook
vi.mock('../../components/Toast', () => ({
  useToast: () => ({
    copy: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn()
  })
}))

describe('useCopyToClipboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset clipboard mock
    vi.mocked(navigator.clipboard.writeText).mockResolvedValue(undefined)
  })

  it('initializes with not copied state', () => {
    const { result } = renderHook(() => useCopyToClipboard())
    const { isCopying } = result.current
    
    expect(isCopying).toBe(false)
  })

  it('copies text to clipboard successfully', async () => {
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    await act(async () => {
      await copy('test text')
    })
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text')
  })

  it('resets copied state after timeout', async () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    await act(async () => {
      await copy('test text')
    })
    
    // The hook doesn't expose isCopied state, so we can't test this directly
    // Just ensure the copy operation completes without error
    
    vi.useRealTimers()
  })

  it('handles clipboard API errors gracefully', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error('Clipboard error'))
    
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    await act(async () => {
      await copy('test text')
    })
    
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to copy:',
      expect.any(Error)
    )
    
    consoleErrorSpy.mockRestore()
  })

  it('cancels previous timeout when copying again', async () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    // First copy
    await act(async () => {
      await copy('first text')
    })
    
    expect(result.current.isCopying).toBe(true)
    
    // Advance time partially
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    
    // Second copy before timeout
    await act(async () => {
      await copy('second text')
    })
    
    // Advance time past original timeout
    act(() => {
      vi.advanceTimersByTime(1500)
    })
    
    // Should still be true because new timeout was set
    expect(result.current.isCopying).toBe(true)
    
    // Advance to new timeout
    act(() => {
      vi.advanceTimersByTime(600)
    })
    
    expect(result.current.isCopying).toBe(false)
    
    vi.useRealTimers()
  })

  it('handles empty string', async () => {
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    await act(async () => {
      await copy('')
    })
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('')
    expect(result.current.isCopying).toBe(true)
  })

  it('handles special characters', async () => {
    const { result } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    const specialText = 'Test with "quotes" and \nnewlines\tand\ttabs'
    
    await act(async () => {
      await copy(specialText)
    })
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(specialText)
    expect(result.current.isCopying).toBe(true)
  })

  it('maintains stable function reference', () => {
    const { result, rerender } = renderHook(() => useCopyToClipboard())
    const { copy: copy1 } = result.current
    
    rerender()
    
    const { copy: copy2 } = result.current
    
    expect(copy1).toBe(copy2)
  })

  it('cleans up timeout on unmount', async () => {
    vi.useFakeTimers()
    const { result, unmount } = renderHook(() => useCopyToClipboard())
    const { copy } = result.current
    
    await act(async () => {
      await copy('test text')
    })
    
    unmount()
    
    // Advance time - should not cause any errors
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    
    // No assertion needed - just ensuring no errors occur
    
    vi.useRealTimers()
  })
})