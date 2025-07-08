import React, { useState, useCallback, useRef } from 'react';
import { Upload, X, FileText, CheckCircle, Loader2, FileX } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (data: { file: File } | null) => void;
  isLoading?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, isLoading = false }) => {
  const [dragActive, setDragActive] = useState(false);
  const [dragCounter, setDragCounter] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!file) return 'No file selected';
    
    // Check file extension
    if (!file.name.endsWith('.difypkg')) {
      return 'File must have .difypkg extension';
    }
    
    // Check file size (100MB limit)
    const maxSize = 100 * 1024 * 1024; // 100MB in bytes
    if (file.size > maxSize) {
      return 'File size must be less than 100MB';
    }
    
    return null;
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter(prev => prev + 1);
    
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setDragActive(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter(prev => {
      const newCounter = prev - 1;
      if (newCounter === 0) {
        setDragActive(false);
      }
      return newCounter;
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setDragCounter(0);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      // Shake animation
      const dropZone = document.getElementById('drop-zone');
      if (dropZone) {
        dropZone.classList.add('animate-shake');
        setTimeout(() => dropZone.classList.remove('animate-shake'), 500);
      }
      return;
    }
    
    setError('');
    setSelectedFile(file);
    onFileSelect({ file });
    
    // Simulate upload progress
    setUploadProgress(0);
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 100);
  };

  const removeFile = () => {
    setSelectedFile(null);
    setError('');
    setUploadProgress(0);
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          id="drop-zone"
          className={`
            relative border-2 border-dashed rounded-lg p-8
            transition-all duration-300 ease-out
            ${dragActive 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-105 shadow-lg' 
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            }
            ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            ${error ? 'animate-shake' : ''}
          `}
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isLoading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="sr-only"
            onChange={handleChange}
            accept=".difypkg"
            disabled={isLoading}
          />
          
          <div className="flex flex-col items-center">
            <div className={`
              p-4 rounded-full transition-all duration-300
              ${dragActive 
                ? 'bg-blue-100 dark:bg-blue-800/30 rotate-12' 
                : 'bg-gray-100 dark:bg-gray-800'
              }
            `}>
              <Upload className={`
                h-8 w-8 transition-all duration-300
                ${dragActive 
                  ? 'text-blue-600 dark:text-blue-400 scale-110' 
                  : 'text-gray-400 dark:text-gray-500'
                }
              `} />
            </div>
            
            <p className="mt-4 text-sm font-medium text-gray-700 dark:text-gray-300">
              {dragActive ? 'Drop your file here' : 'Drop your .difypkg file here, or click to browse'}
            </p>
            
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Maximum file size: 100MB
            </p>

            {/* Visual indicator for drag */}
            {dragActive && (
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute inset-0 bg-blue-500 opacity-10 animate-pulse rounded-lg" />
                <div className="absolute inset-2 border-2 border-blue-500 border-dashed rounded-lg animate-pulse" />
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="relative border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-white dark:bg-gray-800 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-xs">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={removeFile}
              disabled={isLoading}
              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors disabled:opacity-50"
              aria-label="Remove file"
            >
              <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </button>
          </div>
          
          {/* Upload progress */}
          {uploadProgress < 100 ? (
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                <span>Validating file...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-blue-600 dark:bg-blue-400 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="mt-3 flex items-center text-xs text-green-600 dark:text-green-400">
              <CheckCircle className="h-3.5 w-3.5 mr-1.5" />
              Ready to repackage
            </div>
          )}
        </div>
      )}
      
      {error && (
        <div className="mt-3 flex items-start space-x-2 text-sm text-red-600 dark:text-red-400">
          <FileX className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
          20%, 40%, 60%, 80% { transform: translateX(2px); }
        }
        
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
      `}</style>
    </div>
  );
};

export default FileUpload;