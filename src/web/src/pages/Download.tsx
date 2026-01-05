/**
 * Download Page
 * 
 * Handles file download and decryption.
 */

import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { decryptFile, base64UrlToKey } from '../utils/crypto';
import { downloadFile, getErrorMessage } from '../utils/api';
import { Layout } from '../components/Layout';
import { ProgressBar } from '../components/ProgressBar';

type Status = 'idle' | 'downloading' | 'decrypting' | 'success' | 'error';

export function Download() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<Status>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fileId = searchParams.get('id');
    const keyFragment = window.location.hash.slice(1);

    if (!fileId || !keyFragment) {
      setStatus('error');
      setError('Invalid download link (missing ID or key)');
      return;
    }

    const performDownload = async () => {
      try {
        // Phase 1: Downloading
        setStatus('downloading');
        setProgress(30);
        
        const encryptedData = await downloadFile(fileId);
        setProgress(60);

        // Phase 2: Decrypting
        setStatus('decrypting');
        setProgress(80);
        
        const key = base64UrlToKey(keyFragment);
        const decryptedData = decryptFile(encryptedData, key);
        setProgress(90);

        // Trigger browser download
        const blob = new Blob([new Uint8Array(decryptedData)]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'decrypted_file';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        setProgress(100);
        setStatus('success');

      } catch (err) {
        setStatus('error');
        setError(getErrorMessage(err));
        console.error('Download error:', err);
      }
    };

    performDownload();
  }, [searchParams]);

  const getProgressLabel = () => {
    switch (status) {
      case 'downloading': return 'Downloading encrypted file...';
      case 'decrypting': return 'Decrypting file...';
      case 'success': return 'Complete!';
      default: return '';
    }
  };

  const renderContent = () => {
    if (status === 'success') {
      return (
        <div className="text-center">
          <div className="success-icon-container">
            <SuccessIcon />
          </div>
          <h2 className="mt-6" style={{ color: 'var(--success)' }}>
            File Decrypted!
          </h2>
          <p className="text-secondary mt-2">
            Your file has been decrypted and downloaded.
          </p>
          <p className="text-muted text-sm mt-4">
            Check your downloads folder for the file.
          </p>
          <Link to="/" className="btn btn-primary btn-block mt-8">
            <UploadIcon />
            <span>Upload Another File</span>
          </Link>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="text-center">
          <div className="error-icon-container">
            <ErrorIcon />
          </div>
          <h2 className="mt-6" style={{ color: 'var(--error)' }}>
            Download Failed
          </h2>
          <div className="status-message status-error mt-4">
            <XIcon />
            <span>{error}</span>
          </div>
          <p className="text-muted text-sm mt-4">
            The file may have expired, been deleted, reached its download limit, 
            or the link may be invalid.
          </p>
          <Link to="/" className="btn btn-primary btn-block mt-8">
            <UploadIcon />
            <span>Upload a New File</span>
          </Link>
        </div>
      );
    }

    // Downloading/Decrypting states
    return (
      <div className="text-center">
        <div className="loading-icon-container">
          <LockAnimatedIcon />
        </div>
        <h2 className="mt-6">
          {status === 'downloading' ? 'Downloading...' : 'Decrypting...'}
        </h2>
        <p className="text-secondary mt-2">
          {status === 'downloading' 
            ? 'Fetching encrypted file from server' 
            : 'Decrypting file with your key'}
        </p>
        <ProgressBar
          progress={progress}
          label={getProgressLabel()}
        />
        
        <div className="security-notice mt-6">
          <ShieldIcon />
          <p className="security-notice-text">
            <strong>End-to-end encrypted:</strong> The decryption key in your URL 
            never leaves your browser. The server only sees encrypted data.
          </p>
        </div>
      </div>
    );
  };

  return (
    <Layout 
      title="DeadDrop" 
      subtitle="Secure file download"
      showBranding={status !== 'success' && status !== 'error'}
    >
      {renderContent()}
    </Layout>
  );
}

// Icons
function SuccessIcon() {
  return (
    <svg 
      width="64" 
      height="64" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="var(--success)" 
      strokeWidth="1.5"
      style={{ 
        filter: 'drop-shadow(0 0 20px rgba(16, 185, 129, 0.5))',
      }}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg 
      width="64" 
      height="64" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="var(--error)" 
      strokeWidth="1.5"
      style={{ 
        filter: 'drop-shadow(0 0 20px rgba(239, 68, 68, 0.5))',
      }}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function LockAnimatedIcon() {
  return (
    <svg 
      width="64" 
      height="64" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="var(--accent-primary)" 
      strokeWidth="1.5"
      style={{ 
        filter: 'drop-shadow(0 0 20px rgba(0, 212, 255, 0.5))',
        animation: 'pulse 2s infinite'
      }}
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      <circle cx="12" cy="16" r="1" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg 
      width="24" 
      height="24" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5"
      className="security-notice-icon"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}
