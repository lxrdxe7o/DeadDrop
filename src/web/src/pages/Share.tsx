import { useLocation, Link } from 'react-router-dom';

export function Share() {
  const location = useLocation();
  const { shareUrl, expiresAt } = location.state || {};
  
  if (!shareUrl) {
    return <div>No share link available</div>;
  }
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(shareUrl);
    alert('Link copied to clipboard!');
  };
  
  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
      <h1>File Uploaded Successfully!</h1>
      
      <div style={{ marginTop: '20px', padding: '15px', background: '#f0f0f0', borderRadius: '5px' }}>
        <p><strong>Share this link:</strong></p>
        <input
          type="text"
          value={shareUrl}
          readOnly
          style={{ width: '100%', padding: '10px', marginTop: '10px' }}
        />
        <button onClick={copyToClipboard} style={{ marginTop: '10px' }}>
          Copy Link
        </button>
      </div>
      
      <div style={{ marginTop: '20px' }}>
        <p><strong>Expires:</strong> {new Date(expiresAt).toLocaleString()}</p>
        <p style={{ fontSize: '0.9em', color: '#666' }}>
          ⚠️ The encryption key is in the URL fragment (after #).  
          The server never sees this key - only the recipient can decrypt the file.
        </p>
      </div>
      
      <Link to="/">Upload Another File</Link>
    </div>
  );
}
