import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, CheckCircle } from 'lucide-react';

const FileUpload = ({ onFileSelect, isLoading }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState('');

  const validateFile = (file) => {
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

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }
    
    setError('');
    setSelectedFile(file);
    onFileSelect({ file });
  };

  const removeFile = () => {
    setSelectedFile(null);
    setError('');
    onFileSelect(null);
  };

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          className={`relative border-2 border-dashed rounded-lg p-6 ${
            dragActive ? 'border-indigo-600 bg-indigo-50' : 'border-gray-300'
          } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            className="sr-only"
            onChange={handleChange}
            accept=".difypkg"
            disabled={isLoading}
          />
          <label
            htmlFor="file-upload"
            className="relative cursor-pointer"
          >
            <div className="flex flex-col items-center">
              <Upload className={`h-12 w-12 ${dragActive ? 'text-indigo-600' : 'text-gray-400'}`} />
              <p className="mt-2 text-sm text-gray-600">
                <span className="font-semibold">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500 mt-1">
                .difypkg files only (max 100MB)
              </p>
            </div>
          </label>
        </div>
      ) : (
        <div className="border border-gray-300 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="h-8 w-8 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={removeFile}
              disabled={isLoading}
              className="p-1 hover:bg-gray-100 rounded-full disabled:opacity-50"
            >
              <X className="h-4 w-4 text-gray-500" />
            </button>
          </div>
          <div className="mt-2 flex items-center text-xs text-green-600">
            <CheckCircle className="h-3 w-3 mr-1" />
            Ready to upload
          </div>
        </div>
      )}
      
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};

export default FileUpload;