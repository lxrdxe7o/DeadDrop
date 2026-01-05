/**
 * FileDropzone Component
 * 
 * Drag-and-drop file upload area with visual feedback.
 */

import { useState, useRef, DragEvent, ChangeEvent } from 'react';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  maxSize?: number;
  accept?: string;
}

export function FileDropzone({
  onFileSelect,
  disabled = false,
  maxSize = 50 * 1024 * 1024, // 50MB default
  accept = '*/*',
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFile = (file: File) => {
    setSelectedFile(file);
    onFileSelect(file);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const dropzoneClasses = [
    'dropzone',
    isDragging && 'active',
    selectedFile && 'has-file',
    disabled && 'disabled',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={dropzoneClasses}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        onChange={handleFileInput}
        accept={accept}
        disabled={disabled}
      />
      
      {!selectedFile ? (
        <>
          <UploadIcon className="dropzone-icon" />
          <p className="dropzone-text">
            Drag & drop your file here, or <span className="text-accent">browse</span>
          </p>
          <p className="dropzone-hint">
            Maximum file size: {formatFileSize(maxSize)}
          </p>
        </>
      ) : (
        <>
          <FileIcon className="dropzone-icon" style={{ color: 'var(--success)' }} />
          <div className="dropzone-file">
            <span className="dropzone-file-name">{selectedFile.name}</span>
            <span className="dropzone-file-size">{formatFileSize(selectedFile.size)}</span>
            <button 
              type="button"
              onClick={(e) => { e.stopPropagation(); clearFile(); }}
              className="btn btn-ghost btn-sm"
              style={{ padding: '0.25rem 0.5rem' }}
            >
              ✕
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg 
      className={className}
      width="48" 
      height="48" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function FileIcon({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg 
      className={className}
      style={style}
      width="48" 
      height="48" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}

export default FileDropzone;
