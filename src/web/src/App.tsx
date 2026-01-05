/**
 * App Component
 * 
 * Root component with routing and crypto module initialization.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useCrypto } from './hooks/useCrypto';
import { Upload } from './pages/Upload';
import { Download } from './pages/Download';
import { Share } from './pages/Share';
import ErrorBoundary from './components/ErrorBoundary';
import { EncryptionMesh } from './components/EncryptionMesh';

export default function App() {
  const { isReady, error } = useCrypto();

  if (error) {
    return (
      <>
        <EncryptionMesh />
        <div className="page-container">
          <div className="glass-card text-center">
            <div className="error-icon-container">
              <ErrorIcon />
            </div>
            <h2 className="mt-6" style={{ color: 'var(--error)' }}>
              Initialization Error
            </h2>
            <p className="text-secondary mt-2">
              Failed to load cryptography module
            </p>
            <div className="status-message status-error mt-4">
              <XIcon />
              <span>{error}</span>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="btn btn-primary btn-block mt-6"
            >
              <RefreshIcon />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </>
    );
  }

  if (!isReady) {
    return (
      <>
        <EncryptionMesh />
        <div className="loading-container">
          <div className="loading-icon-wrapper">
            <LockIcon />
          </div>
          <div className="loading-spinner" />
          <h3 className="text-primary">DeadDrop</h3>
          <p className="loading-text">Initializing cryptography module...</p>
        </div>
      </>
    );
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/download" element={<Download />} />
          <Route path="/share" element={<Share />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

// Icons
function LockIcon() {
  return (
    <svg 
      width="48" 
      height="48" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="var(--accent-primary)" 
      strokeWidth="1.5"
      style={{ 
        filter: 'drop-shadow(0 0 30px rgba(0, 212, 255, 0.6))',
        animation: 'pulse 2s infinite'
      }}
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
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
      style={{ filter: 'drop-shadow(0 0 20px rgba(239, 68, 68, 0.5))' }}
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

function RefreshIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  );
}
