/**
 * Upload Page
 * 
 * File upload interface with encryption.
 */

import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { encryptFile, generateKey, keyToBase64Url } from '../utils/crypto';
import { uploadFile, getErrorMessage } from '../utils/api';
import { MAX_FILE_SIZE, TTL_OPTIONS } from '../utils/constants';
import { Layout } from '../components/Layout';
import { Button } from '../components/Button';
import { FileDropzone } from '../components/FileDropzone';
import { ProgressBar } from '../components/ProgressBar';

type UploadPhase = 'idle' | 'encrypting' | 'uploading' | 'complete';

export function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [ttl, setTtl] = useState(86400);
  const [maxDownloads, setMaxDownloads] = useState(1);
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setProgress(0);

    try {
      // Validate file size
      if (file.size > MAX_FILE_SIZE) {
        throw new Error('File too large (max 50MB)');
      }

      // Phase 1: Encrypting
      setPhase('encrypting');
      setProgress(20);
      
      const fileData = new Uint8Array(await file.arrayBuffer());
      setProgress(40);
      
      const key = generateKey();
      const encryptedData = encryptFile(fileData, key);
      setProgress(60);

      // Phase 2: Uploading
      setPhase('uploading');
      setProgress(70);
      
      const response = await uploadFile(encryptedData, file.name, ttl, maxDownloads);
      setProgress(90);

      // Generate share URL with encryption key in fragment
      const keyFragment = keyToBase64Url(key);
      const shareUrl = `${window.location.origin}/download?id=${response.id}#${keyFragment}`;

      setPhase('complete');
      setProgress(100);
      
      // Navigate to share page
      setTimeout(() => {
        navigate('/share', { state: { shareUrl, expiresAt: response.expires_at } });
      }, 500);

    } catch (err) {
      setError(getErrorMessage(err));
      setPhase('idle');
      setProgress(0);
      console.error('Upload error:', err);
    }
  };

  const isProcessing = phase !== 'idle';
  
  const getProgressLabel = () => {
    switch (phase) {
      case 'encrypting': return 'Encrypting file...';
      case 'uploading': return 'Uploading encrypted data...';
      case 'complete': return 'Complete!';
      default: return '';
    }
  };

  return (
    <Layout>
      <form onSubmit={handleSubmit}>
        {/* File Dropzone */}
        <div className="form-group">
          <FileDropzone
            onFileSelect={setFile}
            disabled={isProcessing}
            maxSize={MAX_FILE_SIZE}
          />
        </div>

        {/* Options Row */}
        <div className="glass-card-inner">
          <div className="flex gap-4">
            {/* Expiration */}
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="form-label">Expires After</label>
              <select
                className="form-select"
                value={ttl}
                onChange={(e) => setTtl(Number(e.target.value))}
                disabled={isProcessing}
              >
                {TTL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Max Downloads */}
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="form-label">Max Downloads</label>
              <input
                type="number"
                className="form-input"
                min="1"
                max="5"
                value={maxDownloads}
                onChange={(e) => setMaxDownloads(Number(e.target.value))}
                disabled={isProcessing}
              />
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        {isProcessing && (
          <ProgressBar
            progress={progress}
            label={getProgressLabel()}
          />
        )}

        {/* Error Message */}
        {error && (
          <div className="status-message status-error mt-4">
            <ErrorIcon />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <Button
          type="submit"
          variant="primary"
          size="lg"
          block
          loading={isProcessing}
          disabled={!file || isProcessing}
          className="mt-6"
        >
          <UploadIcon />
          <span>Encrypt & Upload</span>
        </Button>
      </form>

      {/* Security Notice */}
      <div className="security-notice">
        <ShieldIcon />
        <p className="security-notice-text">
          <strong>Zero-knowledge encryption:</strong> Your files are encrypted in your browser 
          before upload. The server never sees your unencrypted data or encryption keys.
        </p>
      </div>
    </Layout>
  );
}

// Icons
function UploadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
