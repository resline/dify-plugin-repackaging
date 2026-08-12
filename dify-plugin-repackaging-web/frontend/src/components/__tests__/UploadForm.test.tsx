import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '../../test/utils/test-utils'
import userEvent from '@testing-library/user-event'
import UploadForm from '../UploadForm'
import { createMockFile } from '../../test/utils/test-utils'

describe('UploadForm', () => {
  const onSubmit = vi.fn()
  const onSubmitMarketplace = vi.fn()
  const onSubmitFile = vi.fn()
  const onFormStateChange = vi.fn()

  const defaultProps = {
    onSubmit,
    onSubmitMarketplace,
    onSubmitFile,
    onFormStateChange,
    isLoading: false,
    currentTab: 'url',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the URL form with accessible controls', () => {
    render(<UploadForm {...defaultProps} />)

    expect(screen.getByLabelText(/plugin url/i)).toHaveAttribute('type', 'url')
    expect(screen.getByText('Target Platform')).toBeInTheDocument()
    expect(screen.getByLabelText(/output suffix/i)).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: /start repackaging/i })).toHaveAttribute('type', 'submit')
  })

  it('validates required URL, protocol and supported URL shape', async () => {
    const user = userEvent.setup()
    render(<UploadForm {...defaultProps} />)
    const urlInput = screen.getByLabelText(/plugin url/i)
    const submitButton = screen.getByRole('button', { name: /start repackaging/i })

    await user.click(submitButton)
    expect(await screen.findByText('URL is required')).toBeInTheDocument()

    await user.type(urlInput, 'not-a-url')
    await user.click(submitButton)
    expect(await screen.findByText('URL must start with http:// or https://')).toBeInTheDocument()

    await user.clear(urlInput)
    await user.type(urlInput, 'https://example.com/invalid')
    await user.click(submitButton)
    expect(await screen.findByText(/URL must point to a \.difypkg file/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it.each([
    'https://marketplace.dify.ai/plugins/langgenius/agent',
    'https://example.com/plugin.difypkg',
  ])('submits a supported URL: %s', async (url) => {
    const user = userEvent.setup()
    render(<UploadForm {...defaultProps} />)

    await user.type(screen.getByLabelText(/plugin url/i), url)
    await user.click(screen.getByRole('button', { name: /start repackaging/i }))

    expect(onSubmit).toHaveBeenCalledWith({ url, platform: '', suffix: 'offline' })
  })

  it('persists edited URL, platform and suffix and submits them', async () => {
    const user = userEvent.setup()
    render(<UploadForm {...defaultProps} initialUrl="https://example.com/plugin.difypkg" />)

    await user.click(screen.getByRole('button', { name: /auto-detect/i }))
    await user.click(screen.getByRole('button', { name: /linux x86_64 \(2014\)/i }))
    const suffix = screen.getByLabelText(/output suffix/i)
    await user.clear(suffix)
    await user.type(suffix, 'custom')
    await user.click(screen.getByRole('button', { name: /start repackaging/i }))

    expect(onFormStateChange).toHaveBeenCalledWith({ platform: 'manylinux2014_x86_64' })
    expect(onFormStateChange).toHaveBeenCalledWith({ suffix: 'custom' })
    expect(onSubmit).toHaveBeenCalledWith({
      url: 'https://example.com/plugin.difypkg',
      platform: 'manylinux2014_x86_64',
      suffix: 'custom',
    })
  })

  it('disables the URL form while a task is starting', () => {
    render(<UploadForm {...defaultProps} isLoading />)

    expect(screen.getByLabelText(/plugin url/i)).toBeDisabled()
    expect(screen.getByLabelText(/output suffix/i)).toBeDisabled()
    expect(screen.getByRole('button', { name: /processing/i })).toBeDisabled()
  })

  it('renders the marketplace browser on its tab', () => {
    render(<UploadForm {...defaultProps} currentTab="marketplace" />)
    expect(screen.queryByLabelText(/plugin url/i)).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /search marketplace plugins/i })).toBeInTheDocument()
  })

  it('selects and submits a local package', async () => {
    const user = userEvent.setup()
    const { container } = render(<UploadForm {...defaultProps} currentTab="file" />)
    const input = container.querySelector<HTMLInputElement>('input[type="file"]')
    const file = createMockFile('plugin.difypkg', 1024, 'application/octet-stream')

    expect(input).not.toBeNull()
    await user.upload(input!, file)
    expect(await screen.findByText('plugin.difypkg')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /start repackaging/i }))

    await waitFor(() => {
      expect(onSubmitFile).toHaveBeenCalledWith({ file, platform: '', suffix: 'offline' })
    })
  })
})
