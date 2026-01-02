import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { encryptFile, generateKey, keyToBase64Url } from '../utils/crypto';
import { uploadFile, getErrorMessage } from '../utils/api';
import { MAX_FILE_SIZE, TTL_OPTIONS } from '../utils/constants';

export function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [ttl, setTtl] = useState(86400);
  const [maxDownloads, setMaxDownloads] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setIsUploading(true);

    try {
      // Validate file size
      if (file.size > MAX_FILE_SIZE) {
        throw new Error('File too large (max 50MB)');
      }

      // Read and encrypt file
      const fileData = new Uint8Array(await file.arrayBuffer());
      const key = generateKey();
      const encryptedData = encryptFile(fileData, key);

      // Upload encrypted file (with automatic retry)
      const response = await uploadFile(encryptedData, file.name, ttl, maxDownloads);

      // Generate share URL with encryption key in fragment
      const keyFragment = keyToBase64Url(key);
      const shareUrl = `${window.location.origin}/download?id=${response.id}#${keyFragment}`;

      navigate('/share', { state: { shareUrl, expiresAt: response.expires_at } });

    } catch (err) {
      // Use improved error message extraction
      setError(getErrorMessage(err));
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
      <h1>DeadDrop</h1>
      <p>Zero-knowledge file sharing with client-side encryption</p>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <label>Select File (max 50MB):</label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={isUploading}
            required
            style={{ display: 'block', marginTop: '5px' }}
          />
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label>Expiration:</label>
          <select value={ttl} onChange={(e) => setTtl(Number(e.target.value))} disabled={isUploading}>
            {TTL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <label>Max Downloads (1-5):</label>
          <input
            type="number"
            min="1"
            max="5"
            value={maxDownloads}
            onChange={(e) => setMaxDownloads(Number(e.target.value))}
            disabled={isUploading}
            style={{ display: 'block', marginTop: '5px' }}
          />
        </div>
        
        {error && <div style={{ color: 'red', marginBottom: '15px' }}>{error}</div>}
        
        <button type="submit" disabled={!file || isUploading}>
          {isUploading ? 'Encrypting & Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
}
