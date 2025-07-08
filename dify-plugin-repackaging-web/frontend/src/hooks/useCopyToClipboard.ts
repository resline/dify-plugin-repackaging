import { useState, useCallback } from 'react';
import { useToast } from '../components/Toast';

interface UseCopyToClipboardReturn {
  copy: (text: string, successMessage?: string) => Promise<void>;
  isCopying: boolean;
}

export const useCopyToClipboard = (): UseCopyToClipboardReturn => {
  const [isCopying, setIsCopying] = useState(false);
  const { copy: showCopyToast, error } = useToast();

  const copy = useCallback(async (text: string, successMessage?: string) => {
    if (isCopying) return;

    setIsCopying(true);
    
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        showCopyToast(successMessage || 'Copied to clipboard!');
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
          document.execCommand('copy');
          showCopyToast(successMessage || 'Copied to clipboard!');
        } catch (err) {
          error('Failed to copy to clipboard');
          throw err;
        } finally {
          document.body.removeChild(textArea);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      error('Failed to copy to clipboard');
    } finally {
      setIsCopying(false);
    }
  }, [isCopying, showCopyToast, error]);

  return { copy, isCopying };
};