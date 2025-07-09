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
    
    // Check for marketplace plugin parameters
    const pluginUrl = params.get('plugin');
    const author = params.get('author');
    const name = params.get('name');
    const version = params.get('version');
    
    if (pluginUrl) {
      // Handle full plugin URL parameter
      setDeepLinkData({
        type: 'url',
        url: pluginUrl
      });
    } else if (author && name) {
      // Handle individual plugin parameters
      setDeepLinkData({
        type: 'marketplace',
        author,
        name,
        version: version || 'latest'
      });
    }
    
    // Clear URL parameters after processing to avoid confusion
    if (deepLinkData) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  return deepLinkData;
};

export default useDeepLink;