import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { decryptFile, base64UrlToKey } from '../utils/crypto';
import { downloadFile } from '../utils/api';

type Status = 'idle' | 'downloading' | 'decrypting' | 'success' | 'error';

export function Download() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<Status>('idle');
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
        setStatus('downloading');
        const encryptedData = await downloadFile(fileId);
        
        setStatus('decrypting');
        const key = base64UrlToKey(keyFragment);
        const decryptedData = decryptFile(encryptedData, key);
        
        const blob = new Blob([new Uint8Array(decryptedData)]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'decrypted_file';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        setStatus('success');
        
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Download failed');
      }
    };
    
    performDownload();
  }, [searchParams]);
  
  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px', textAlign: 'center' }}>
      <h1>DeadDrop - Download</h1>
      
      {status === 'downloading' && <p>Downloading encrypted file...</p>}
      {status === 'decrypting' && <p>Decrypting file...</p>}
      {status === 'success' && (
        <div style={{ color: 'green' }}>
          <p>✓ File decrypted successfully!</p>
          <p>Check your downloads folder.</p>
        </div>
      )}
      {status === 'error' && (
        <div style={{ color: 'red' }}>
          <p>✗ {error}</p>
          <p>The file may have expired, been deleted, or the link is invalid.</p>
        </div>
      )}
    </div>
  );
}
