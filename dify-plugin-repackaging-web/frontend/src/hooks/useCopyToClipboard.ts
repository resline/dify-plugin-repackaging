import { useState, useCallback, useRef } from 'react';
import { useToast } from '../components/Toast';

interface UseCopyToClipboardReturn {
  copy: (text: string, successMessage?: string) => Promise<void>;
  isCopying: boolean;
}

export const useCopyToClipboard = (): UseCopyToClipboardReturn => {
  const [isCopying, setIsCopying] = useState(false);
  const { copy: showCopyToast, error } = useToast();
  const isCopyingRef = useRef(false);
  const showCopyToastRef = useRef(showCopyToast);
  const showErrorRef = useRef(error);

  showCopyToastRef.current = showCopyToast;
  showErrorRef.current = error;

  const copy = useCallback(async (text: string, successMessage?: string) => {
    if (isCopyingRef.current) return;

    isCopyingRef.current = true;
    setIsCopying(true);
    
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        showCopyToastRef.current(successMessage || 'Copied to clipboard!');
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
          showCopyToastRef.current(successMessage || 'Copied to clipboard!');
        } catch (err) {
          showErrorRef.current('Failed to copy to clipboard');
          throw err;
        } finally {
          document.body.removeChild(textArea);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      showErrorRef.current('Failed to copy to clipboard');
    } finally {
      isCopyingRef.current = false;
      setIsCopying(false);
    }
  }, []);

  return { copy, isCopying };
};
