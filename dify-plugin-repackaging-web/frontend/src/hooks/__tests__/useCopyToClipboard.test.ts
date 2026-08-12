import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useCopyToClipboard } from '../useCopyToClipboard'

const toast = vi.hoisted(() => ({
  copy: vi.fn(),
  error: vi.fn(),
}))

vi.mock('../../components/Toast', () => ({
  useToast: () => ({ ...toast, success: vi.fn(), warning: vi.fn() }),
}))

describe('useCopyToClipboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(navigator.clipboard.writeText).mockResolvedValue(undefined)
  })

  it('starts idle and copies text with a success notification', async () => {
    const { result } = renderHook(() => useCopyToClipboard())
    expect(result.current.isCopying).toBe(false)

    await act(() => result.current.copy('test text', 'Done'))

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text')
    expect(toast.copy).toHaveBeenCalledWith('Done')
    expect(result.current.isCopying).toBe(false)
  })

  it('reports in-flight state and ignores a concurrent copy', async () => {
    let resolveCopy!: () => void
    vi.mocked(navigator.clipboard.writeText).mockImplementation(
      () => new Promise<void>((resolve) => { resolveCopy = resolve })
    )
    const { result } = renderHook(() => useCopyToClipboard())

    let firstCopy!: Promise<void>
    act(() => {
      firstCopy = result.current.copy('first')
    })
    expect(result.current.isCopying).toBe(true)

    await act(() => result.current.copy('second'))
    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveCopy()
      await firstCopy
    })
    expect(result.current.isCopying).toBe(false)
  })

  it('shows an error and returns to idle when the Clipboard API fails', async () => {
    vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error('Clipboard error'))
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { result } = renderHook(() => useCopyToClipboard())

    await act(() => result.current.copy('test'))

    expect(consoleError).toHaveBeenCalledWith('Failed to copy:', expect.any(Error))
    expect(toast.error).toHaveBeenCalledWith('Failed to copy to clipboard')
    expect(result.current.isCopying).toBe(false)
  })

  it('uses the textarea fallback in an insecure context', async () => {
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false })
    const execCommand = vi.fn(() => true)
    Object.defineProperty(document, 'execCommand', { configurable: true, value: execCommand })
    const { result } = renderHook(() => useCopyToClipboard())

    await act(() => result.current.copy('fallback text'))

    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(toast.copy).toHaveBeenCalledWith('Copied to clipboard!')
    expect(document.querySelector('textarea')).not.toBeInTheDocument()
  })

  it('keeps the copy callback stable across rerenders', () => {
    const { result, rerender } = renderHook(() => useCopyToClipboard())
    const first = result.current.copy
    rerender()
    expect(result.current.copy).toBe(first)
  })
})
