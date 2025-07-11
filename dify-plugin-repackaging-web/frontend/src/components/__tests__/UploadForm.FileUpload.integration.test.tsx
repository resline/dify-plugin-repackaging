import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../../test/utils/test-utils'
import userEvent from '@testing-library/user-event'
import UploadForm from '../UploadForm'
import { createMockFile } from '../../test/utils/test-utils'

describe('UploadForm File Upload Integration', () => {
  const mockOnSubmit = vi.fn()
  const mockOnSubmitMarketplace = vi.fn()
  const mockOnSubmitFile = vi.fn()
  const mockOnTabChange = vi.fn()

  const defaultProps = {
    onSubmit: mockOnSubmit,
    onSubmitMarketplace: mockOnSubmitMarketplace,
    onSubmitFile: mockOnSubmitFile,
    isLoading: false,
    currentTab: 'file',
    onTabChange: mockOnTabChange
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows "Start Repackaging" button after file selection', async () => {
    const user = userEvent.setup()
    render(<UploadForm {...defaultProps} />)
    
    // Initially, the button should not be visible
    expect(screen.queryByText('Start Repackaging')).not.toBeInTheDocument()
    
    // Find and click the file input
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeInTheDocument()
    
    // Create and upload a valid .difypkg file
    const file = createMockFile('test-plugin.difypkg', 1024000, 'application/octet-stream')
    await user.upload(fileInput, file)
    
    // Wait for the file to be processed
    await waitFor(() => {
      expect(screen.getByText('test-plugin.difypkg')).toBeInTheDocument()
    })
    
    // The "Start Repackaging" button should now be visible
    const startButton = await screen.findByRole('button', { name: /start repackaging/i })
    expect(startButton).toBeInTheDocument()
    expect(startButton).not.toBeDisabled()
  })

  it('calls onSubmitFile when "Start Repackaging" is clicked', async () => {
    const user = userEvent.setup()
    render(<UploadForm {...defaultProps} />)
    
    // Upload a file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = createMockFile('test-plugin.difypkg', 1024000, 'application/octet-stream')
    await user.upload(fileInput, file)
    
    // Wait for button to appear and click it
    const startButton = await screen.findByRole('button', { name: /start repackaging/i })
    await user.click(startButton)
    
    // Verify the callback was called with correct data
    expect(mockOnSubmitFile).toHaveBeenCalledWith({
      file: expect.any(File),
      platform: '',
      suffix: 'offline'
    })
  })

  it('button disappears when loading', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<UploadForm {...defaultProps} />)
    
    // Upload a file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = createMockFile('test-plugin.difypkg', 1024000, 'application/octet-stream')
    await user.upload(fileInput, file)
    
    // Button should be visible
    expect(await screen.findByRole('button', { name: /start repackaging/i })).toBeInTheDocument()
    
    // Rerender with isLoading=true
    rerender(<UploadForm {...defaultProps} isLoading={true} />)
    
    // Button should show loading state
    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('maintains file selection state across re-renders', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<UploadForm {...defaultProps} />)
    
    // Upload a file
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = createMockFile('test-plugin.difypkg', 1024000, 'application/octet-stream')
    await user.upload(fileInput, file)
    
    // Verify file is selected
    expect(await screen.findByText('test-plugin.difypkg')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start repackaging/i })).toBeInTheDocument()
    
    // Trigger a re-render (e.g., parent component state change)
    rerender(<UploadForm {...defaultProps} />)
    
    // File should still be selected and button should still be visible
    expect(screen.getByText('test-plugin.difypkg')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start repackaging/i })).toBeInTheDocument()
  })
})