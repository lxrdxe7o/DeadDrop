/**
 * Share Page
 * 
 * Displays the shareable link after successful upload.
 */

import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Button } from '../components/Button';

export function Share() {
  const location = useLocation();
  const { shareUrl, expiresAt } = location.state || {};
  const [copied, setCopied] = useState(false);

  if (!shareUrl) {
    return (
      <Layout title="No Link Available">
        <div className="status-message status-error">
          <ErrorIcon />
          <span>No share link available. Please upload a file first.</span>
        </div>
        <Link to="/" className="btn btn-primary btn-block mt-6">
          <UploadIcon />
          <span>Upload a File</span>
        </Link>
      </Layout>
    );
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatExpiry = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = date.getTime() - now.getTime();
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
      return `${days} day${days > 1 ? 's' : ''} from now`;
    }
    return `${hours} hour${hours > 1 ? 's' : ''} from now`;
  };

  return (
    <Layout 
      title="Upload Complete!" 
      subtitle="Your file has been encrypted and uploaded securely"
      showBranding={false}
    >
      {/* Success Header */}
      <div className="text-center mb-8">
        <div className="success-icon-container">
          <SuccessIcon />
        </div>
        <h2 className="mt-4" style={{ color: 'var(--success)' }}>
          Upload Complete!
        </h2>
        <p className="text-secondary mt-2">
          Your file has been encrypted and uploaded securely
        </p>
      </div>

      {/* Share Link */}
      <div className="share-link-container">
        <div className="share-link-label">Share this secure link</div>
        <div className="share-link-input">
          <input
            type="text"
            value={shareUrl}
            readOnly
            onClick={(e) => (e.target as HTMLInputElement).select()}
          />
          <Button
            variant={copied ? 'secondary' : 'primary'}
            onClick={copyToClipboard}
            style={{ flexShrink: 0 }}
          >
            {copied ? (
              <>
                <CheckIcon />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <CopyIcon />
                <span>Copy</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Expiry Info */}
      <div className="flex justify-center mt-4">
        <div className="expiry-badge">
          <ClockIcon />
          <span>Expires: {formatExpiry(expiresAt)} ({new Date(expiresAt).toLocaleString()})</span>
        </div>
      </div>

      {/* Security Notice */}
      <div className="security-notice">
        <KeyIcon />
        <div className="security-notice-text">
          <strong>The encryption key is in the URL fragment</strong> (after the #). 
          The server never sees this key — only the recipient with this exact link can decrypt the file.
        </div>
      </div>

      {/* Actions */}
      <Link to="/" className="btn btn-secondary btn-block mt-6">
        <UploadIcon />
        <span>Upload Another File</span>
      </Link>
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
        animation: 'pulse 2s infinite'
      }}
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="expiry-badge-icon">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function KeyIcon() {
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
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
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

function ErrorIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}
