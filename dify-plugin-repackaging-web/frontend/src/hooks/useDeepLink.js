import { useEffect, useState } from 'react';

/**
 * Custom hook to handle deep links from marketplace
 * Extracts plugin information from URL parameters
 */
export const useDeepLink = () => {
  const [deepLinkData, setDeepLinkData] = useState(null);

  useEffect(() => {
    // Parse URL parameters
    const params = new URLSearchParams(window.location.search);
    
    // Check for URL parameter first
    const url = params.get('url');
    
    if (url) {
      // Validate URL
      try {
        new URL(url);
      } catch {
        // Invalid URL
        return;
      }

      // Check if it's a marketplace URL
      const marketplaceMatch = url.match(/^https:\/\/marketplace\.dify\.ai\/plugins\/([^\/]+)\/([^\/]+)\/?(?:([^\/]+)\/?)?$/);
      
      if (marketplaceMatch) {
        const [, author, name, version] = marketplaceMatch;
        setDeepLinkData({
          type: 'marketplace',
          url,
          author,
          name,
          version: version || null
        });
      } else {
        // Direct URL (GitHub releases, .difypkg files, etc.)
        setDeepLinkData({
          type: 'url',
          url
        });
      }
      
      // Clear URL parameters after processing
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      // Check for individual marketplace plugin parameters (legacy support)
      const author = params.get('author');
      const name = params.get('name');
      const version = params.get('version');
      
      if (author && name) {
        setDeepLinkData({
          type: 'marketplace',
          author,
          name,
          version: version || 'latest'
        });
        
        // Clear URL parameters after processing
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }, []);

  return deepLinkData;
};

export default useDeepLink;