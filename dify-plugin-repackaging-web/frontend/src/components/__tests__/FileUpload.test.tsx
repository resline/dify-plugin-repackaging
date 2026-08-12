import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../test/utils/test-utils'
import userEvent from '@testing-library/user-event'
import FileUpload from '../FileUpload'
import { createMockFile } from '../../test/utils/test-utils'

describe('FileUpload', () => {
  const mockOnFileSelect = vi.fn()

  const defaultProps = {
    onFileSelect: mockOnFileSelect,
    isLoading: false
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the file upload area correctly', () => {
    render(<FileUpload {...defaultProps} />)
    
    expect(screen.getByText((content, element) => {
      return element?.tagName === 'P' && content.includes('Drop your .difypkg file here')
    })).toBeInTheDocument()
    expect(screen.getByText(/Maximum upload size: 100MB/i)).toBeInTheDocument()
  })

  it('handles file selection via click', async () => {
    const user = userEvent.setup()
    render(<FileUpload {...defaultProps} />)
    
    const file = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    await user.upload(input, file)
    
    await waitFor(() => {
      expect(mockOnFileSelect).toHaveBeenCalledWith({
        file: expect.any(File)
      })
    })
  })

  it('validates file extension', async () => {
    render(<FileUpload {...defaultProps} />)
    
    const invalidFile = createMockFile('plugin.zip', 1024000, 'application/zip')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    fireEvent.change(input, { target: { files: [invalidFile] } })
    
    await waitFor(() => {
      expect(screen.getByText('File must have .difypkg extension')).toBeInTheDocument()
    })
    expect(mockOnFileSelect).toHaveBeenCalledWith(null)
  })

  it('validates file size', async () => {
    const user = userEvent.setup()
    render(<FileUpload {...defaultProps} />)
    
    // Create a file larger than 100MB (100 * 1024 * 1024 bytes)
    const largeFile = createMockFile('plugin.difypkg', 150 * 1024 * 1024, 'application/octet-stream')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    await user.upload(input, largeFile)
    
    await waitFor(() => {
      expect(screen.getByText('File size must be less than 100MB')).toBeInTheDocument()
    })
    expect(mockOnFileSelect).toHaveBeenCalledWith(null)
  })

  it('handles drag and drop', async () => {
    render(<FileUpload {...defaultProps} />)
    
    const dropZone = document.getElementById('drop-zone')!
    const file = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')
    
    // Simulate drag enter
    fireEvent.dragEnter(dropZone, {
      dataTransfer: {
        files: [file],
        items: [file],
        types: ['Files']
      }
    })
    
    expect(dropZone).toHaveClass('border-blue-500')
    
    // Simulate drop
    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
        types: ['Files']
      }
    })
    
    await waitFor(() => {
      expect(mockOnFileSelect).toHaveBeenCalledWith({
        file: expect.any(File)
      })
    })
  })

  it('prevents default drag behavior', () => {
    render(<FileUpload {...defaultProps} />)
    
    const dropZone = document.getElementById('drop-zone')!
    
    const dragOverEvent = new Event('dragover', { bubbles: true })
    Object.defineProperty(dragOverEvent, 'preventDefault', {
      value: vi.fn(),
      writable: true
    })
    
    fireEvent(dropZone, dragOverEvent)
    
    expect(dragOverEvent.preventDefault).toHaveBeenCalled()
  })

  it('displays selected file information', async () => {
    const user = userEvent.setup()
    render(<FileUpload {...defaultProps} />)
    
    const file = createMockFile('my-plugin.difypkg', 2048000, 'application/octet-stream')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    await user.upload(input, file)
    
    expect(await screen.findByText('my-plugin.difypkg')).toBeInTheDocument()
    expect(screen.getByText('1.95 MB')).toBeInTheDocument()
  })

  it('allows file removal', async () => {
    const user = userEvent.setup()
    render(<FileUpload {...defaultProps} />)
    
    const file = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    await user.upload(input, file)
    
    const removeButton = await screen.findByLabelText('Remove file')
    await user.click(removeButton)
    
    expect(mockOnFileSelect).toHaveBeenLastCalledWith(null)
    expect(screen.queryByText('plugin.difypkg')).not.toBeInTheDocument()
  })

  it('disables interaction when loading', () => {
    render(<FileUpload {...defaultProps} isLoading={true} />)
    
    const dropZone = document.getElementById('drop-zone')!
    expect(dropZone).toHaveClass('opacity-50')
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).toBeDisabled()
  })

  it('clears error when new file is selected', async () => {
    render(<FileUpload {...defaultProps} />)
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    
    // Upload invalid file
    const invalidFile = createMockFile('plugin.zip', 1024000, 'application/zip')
    fireEvent.change(input, { target: { files: [invalidFile] } })
    
    await waitFor(() => {
      expect(screen.getByText('File must have .difypkg extension')).toBeInTheDocument()
    })
    
    // Upload valid file
    const validFile = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')
    fireEvent.change(input, { target: { files: [validFile] } })
    
    expect(screen.queryByText('File must have .difypkg extension')).not.toBeInTheDocument()
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<FileUpload {...defaultProps} />)
      
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(input).toHaveAttribute('accept', '.difypkg')
    })

    it('announces file selection to screen readers', async () => {
      const user = userEvent.setup()
      render(<FileUpload {...defaultProps} />)
      
      const file = createMockFile('plugin.difypkg', 1024000, 'application/octet-stream')
      const input = document.querySelector('input[type="file"]') as HTMLInputElement
      
      await user.upload(input, file)
      
      // File information should be visible and readable by screen readers
      expect(await screen.findByText('plugin.difypkg')).toBeInTheDocument()
    })
  })
})
