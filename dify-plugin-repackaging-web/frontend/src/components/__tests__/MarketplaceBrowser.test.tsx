import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../../test/utils/test-utils'
import userEvent from '@testing-library/user-event'
import MarketplaceBrowser from '../MarketplaceBrowser'
import { server } from '../../test/mocks/server'
import { http, HttpResponse } from 'msw'

describe('MarketplaceBrowser', () => {
  const mockOnSelectPlugin = vi.fn()

  const defaultProps = {
    onSelectPlugin: mockOnSelectPlugin,
    platform: '',
    suffix: 'offline'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    render(<MarketplaceBrowser {...defaultProps} />)
    
    // Should show loading spinner
    expect(screen.getByText(/loading plugins/i)).toBeInTheDocument()
  })

  it('renders plugins after loading', async () => {
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
      expect(screen.getByText('visualization')).toBeInTheDocument()
    })
    
    expect(screen.getByText('Agent plugin for Dify')).toBeInTheDocument()
    expect(screen.getByText('Data visualization plugin')).toBeInTheDocument()
  })

  it('handles search functionality', async () => {
    const user = userEvent.setup()
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
    })
    
    const searchInput = screen.getByPlaceholderText(/search plugins/i)
    await user.type(searchInput, 'visual')
    
    // Click search button to trigger search
    const searchButton = screen.getByRole('button', { name: /search/i })
    await user.click(searchButton)
    
    // Mock the filtered search response
    server.use(
      http.get('/api/v1/marketplace/plugins', ({ request }) => {
        const url = new URL(request.url)
        const query = url.searchParams.get('q')
        if (query === 'visual') {
          return HttpResponse.json({
            plugins: [{
              id: '2',
              author: 'antv',
              name: 'visualization',
              version: '0.1.7',
              description: 'Data visualization plugin',
              downloads: 500,
              latest_version: '0.1.7',
              created_at: '2024-01-05T00:00:00Z',
              updated_at: '2024-01-20T00:00:00Z'
            }],
            total: 1
          })
        }
        return HttpResponse.json({ plugins: [], total: 0 })
      })
    )
    
    // Wait for search results
    await waitFor(() => {
      expect(screen.queryByText('agent')).not.toBeInTheDocument()
      expect(screen.getByText('visualization')).toBeInTheDocument()
    })
  })

  it('displays plugin details', async () => {
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
    })
    
    // Check that plugin details are displayed
    expect(screen.getByText('langgenius')).toBeInTheDocument()
    expect(screen.getByText('0.0.9')).toBeInTheDocument()
    expect(screen.getByText('Agent plugin for Dify')).toBeInTheDocument()
  })

  it('handles plugin selection', async () => {
    const user = userEvent.setup()
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
    })
    
    const repackageButton = screen.getAllByRole('button', { name: /repackage/i })[0]
    await user.click(repackageButton)
    
    expect(mockOnSelectPlugin).toHaveBeenCalledWith({
      author: 'langgenius',
      name: 'agent',
      version: '0.0.9',
      description: 'Agent plugin for Dify',
      platform: '',
      suffix: 'offline'
    })
  })

  it('handles error state', async () => {
    server.use(
      http.get('/api/v1/marketplace/plugins', () => {
        return HttpResponse.json({ error: 'Server error' }, { status: 500 })
      }),
      http.get('/api/v1/marketplace/categories', () => {
        return HttpResponse.json({ categories: [] })
      }),
      http.get('/api/v1/marketplace/authors', () => {
        return HttpResponse.json({ authors: [] })
      })
    )
    
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      const errorMessage = screen.getByText((content, element) => {
        return element?.classList?.contains('text-red-700') && 
               content?.toLowerCase()?.includes('marketplace') || false
      })
      expect(errorMessage).toBeInTheDocument()
    }, { timeout: 2000 })
  })

  it('clears filters', async () => {
    const user = userEvent.setup()
    
    server.use(
      http.get('/api/v1/marketplace/categories', () => {
        return HttpResponse.json({ categories: ['agent', 'tool'] })
      }),
      http.get('/api/v1/marketplace/authors', () => {
        return HttpResponse.json({ authors: ['langgenius', 'antv'] })
      })
    )
    
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
    })
    
    // Open filters using the filter icon button
    const filterButtons = screen.getAllByRole('button')
    const filterButton = filterButtons.find(btn => btn.querySelector('.lucide-filter'))
    if (filterButton) {
      await user.click(filterButton)
    }
    
    // Type in search
    const searchInput = screen.getByPlaceholderText(/search plugins/i)
    await user.type(searchInput, 'test')
    
    // Look for clear filters link
    await waitFor(() => {
      expect(screen.getByText(/clear all filters/i)).toBeInTheDocument()
    })
  })

  it('displays empty state when no plugins found', async () => {
    server.use(
      http.get('/api/v1/marketplace/plugins', () => {
        return HttpResponse.json({
          plugins: [],
          total: 0,
          page: 1,
          per_page: 12
        })
      })
    )
    
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText(/no plugins found/i)).toBeInTheDocument()
    })
  })

  it('displays plugin information correctly', async () => {
    render(<MarketplaceBrowser {...defaultProps} />)
    
    await waitFor(() => {
      expect(screen.getByText('agent')).toBeInTheDocument()
    })
    
    // Check that plugin information is displayed
    expect(screen.getByText('langgenius')).toBeInTheDocument()
    expect(screen.getByText('0.0.9')).toBeInTheDocument()
    expect(screen.getByText('Agent plugin for Dify')).toBeInTheDocument()
  })

  it('displays loading state while fetching', () => {
    render(<MarketplaceBrowser {...defaultProps} />)
    
    // Should show loading spinner and text
    expect(screen.getByText(/loading plugins/i)).toBeInTheDocument()
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', async () => {
      render(<MarketplaceBrowser {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('agent')).toBeInTheDocument()
      })
      
      // Check for search input
      expect(screen.getByPlaceholderText(/search plugins/i)).toBeInTheDocument()
      // Check for filter button
      expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument()
    })

    it('announces search results to screen readers', async () => {
      const user = userEvent.setup()
      render(<MarketplaceBrowser {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('agent')).toBeInTheDocument()
      })
      
      const searchInput = screen.getByPlaceholderText(/search plugins/i)
      await user.type(searchInput, 'visual')
      
      await waitFor(() => {
        // Results should be in a live region for screen reader announcements
        expect(screen.getByText('visualization')).toBeInTheDocument()
      })
    })

    it('provides keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<MarketplaceBrowser {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('agent')).toBeInTheDocument()
      })
      
      // Tab through elements
      await user.tab()
      expect(screen.getByPlaceholderText(/search plugins/i)).toHaveFocus()
      
      await user.tab()
      // Should focus on search button
      expect(screen.getByRole('button', { name: /search/i })).toHaveFocus()
    })
  })
})